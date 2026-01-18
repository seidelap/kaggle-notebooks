"""Graph execution engine."""

from typing import Optional, Set
import asyncio
from datetime import datetime

from dynamic_bot_org_chart.core.graph import Graph, GraphNode
from dynamic_bot_org_chart.core.states import (
    ExecutionStatus,
    NodeResult,
    HuddleState,
)
from dynamic_bot_org_chart.core.events import EventType


class GraphExecutor:
    """Executor for running the graph."""

    def __init__(self, graph: Graph):
        self.graph = graph
        self._running = False
        self._start_time: Optional[datetime] = None

    async def run(self):
        """Run the graph execution."""
        self._running = True
        self._start_time = datetime.now()

        print("=" * 60)
        print("Starting Graph Execution")
        print("=" * 60)

        # Start event processing
        event_task = asyncio.create_task(self.graph.event_bus.process_events())

        try:
            # Execute the graph
            await self._execute_graph()

        finally:
            # Stop event processing
            self.graph.event_bus.stop()
            await event_task

        print("=" * 60)
        print("Graph Execution Completed")
        print("=" * 60)
        print(self.graph.visualize())

    async def _execute_graph(self):
        """Execute the graph nodes."""
        executed_nodes: Set[str] = set()

        while self._running:
            # Check execution timeout
            if self._is_execution_timed_out():
                print("Execution timeout reached")
                break

            # Get ready nodes
            ready_nodes = self._get_ready_nodes(executed_nodes)

            if not ready_nodes:
                # No ready nodes - check if we're done or waiting
                if self._is_graph_complete():
                    print("All nodes completed")
                    break
                else:
                    # Wait a bit for events to process
                    await asyncio.sleep(0.1)
                    continue

            # Execute ready nodes in parallel
            tasks = [self._execute_node(node) for node in ready_nodes]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for node, result in zip(ready_nodes, results):
                if isinstance(result, Exception):
                    print(f"Node {node.node_id} failed with exception: {result}")
                    await self.graph.mark_node_failed(node.node_id, str(result))
                else:
                    executed_nodes.add(node.node_id)

            # Small delay between iterations
            await asyncio.sleep(0.1)

    def _get_ready_nodes(self, executed_nodes: Set[str]) -> list[GraphNode]:
        """Get nodes that are ready to execute."""
        ready = []

        for node in self.graph.nodes.values():
            # Skip already executed nodes
            if node.node_id in executed_nodes:
                continue

            # Skip nodes that are not ready
            if not node.is_ready_to_execute():
                continue

            # Check if node has timed out
            if node.metadata.is_timed_out:
                print(f"Node {node.node_id} timed out")
                asyncio.create_task(
                    self.graph.mark_node_failed(node.node_id, "Node execution timeout")
                )
                continue

            # Check if max executions reached
            if node.metadata.is_max_executions_reached:
                print(f"Node {node.node_id} reached max executions")
                asyncio.create_task(
                    self.graph.mark_node_failed(node.node_id, "Max executions reached")
                )
                continue

            ready.append(node)

        return ready

    async def _execute_node(self, node: GraphNode):
        """Execute a single node."""
        print(f"\n{'=' * 60}")
        print(f"Executing node: {node.node_id}")
        print(f"{'=' * 60}")

        # Update node status
        node.execution_status = ExecutionStatus.EXECUTING
        node.context.transition_to(HuddleState.EXECUTING)

        try:
            # Execute the huddle
            result = await node.executor.execute()

            # Check result
            if node.context.state == HuddleState.COMPLETED:
                # Node completed successfully
                await self.graph.mark_node_completed(
                    node.node_id,
                    NodeResult.COMPLETED,
                    node.context.artifact
                )
                print(f"Node {node.node_id} completed successfully")

            elif node.context.state == HuddleState.FAILED:
                # Node failed
                await self.graph.mark_node_failed(
                    node.node_id,
                    node.context.error or "Unknown error"
                )
                print(f"Node {node.node_id} failed")

            elif node.context.state == HuddleState.BLOCKED:
                # Node is blocked - mark as blocked but don't fail
                node.execution_status = ExecutionStatus.PENDING
                node.mark_blocked(True)
                print(f"Node {node.node_id} is blocked")

            elif node.context.state == HuddleState.WAITING:
                # Node is waiting - leave as pending
                node.execution_status = ExecutionStatus.PENDING
                node.mark_waiting_for_feedback(True)
                print(f"Node {node.node_id} is waiting")

            else:
                # Unknown state
                print(f"Node {node.node_id} in unknown state: {node.context.state}")

        except Exception as e:
            print(f"Node {node.node_id} raised exception: {e}")
            await self.graph.mark_node_failed(node.node_id, str(e))

    def _is_execution_timed_out(self) -> bool:
        """Check if overall execution has timed out."""
        if not self.graph._execution_timeout or not self._start_time:
            return False

        elapsed = (datetime.now() - self._start_time).total_seconds()
        return elapsed > self.graph._execution_timeout

    def _is_graph_complete(self) -> bool:
        """Check if graph execution is complete."""
        for node in self.graph.nodes.values():
            if node.execution_status not in (ExecutionStatus.COMPLETED, ExecutionStatus.FAILED):
                # Check if node is waiting or blocked
                if node.context.state in (HuddleState.WAITING, HuddleState.BLOCKED):
                    continue
                return False
        return True

    def stop(self):
        """Stop execution."""
        self._running = False


class OrgChartRunner:
    """Runner for the dynamic bot org chart."""

    def __init__(self):
        self.graph: Optional[Graph] = None
        self.executor: Optional[GraphExecutor] = None

    async def run(self, initial_product_description: str = "Main product"):
        """Run the org chart."""
        from dynamic_bot_org_chart.core.graph import Graph, GraphNode
        from dynamic_bot_org_chart.core.events import EventBus
        from dynamic_bot_org_chart.huddles.product_huddle import ProductHuddle
        from dynamic_bot_org_chart.core.states import ExecutionStatus

        # Create event bus and graph
        event_bus = EventBus()
        self.graph = Graph(event_bus)

        # Set execution limits
        self.graph.set_execution_timeout(3600)  # 1 hour
        self.graph.set_node_timeout(600)  # 10 minutes per node
        self.graph.set_max_node_executions(10)  # Max 10 executions

        # Create CEO Product Huddle (root)
        ceo_huddle = ProductHuddle(
            huddle_id="ceo-product",
            event_bus=event_bus,
            graph=self.graph,
            is_ceo=True
        )

        # Add to graph
        node = GraphNode(
            node_id="ceo-product",
            executor=ceo_huddle,
            context=ceo_huddle.context
        )
        self.graph.add_node(node)

        # Create executor
        self.executor = GraphExecutor(self.graph)

        # Run the graph
        await self.executor.run()

        return self.graph
