# Dynamic Bot Org Chart

An event-driven, agent-based framework for managing products and projects with hierarchical escalation and circuit breaker patterns. Built on top of the Claude Agent SDK, running locally.

## Overview

This framework implements a dynamic organizational structure where:

- **Products** are managed by Product Huddles (Swarms)
- **Projects** are managed by Project Huddles (Swarms)
- **Tasks** are Claude Code sessions (autonomous coding work)
- **Graph** structure manages dependencies between huddles
- **Events** drive communication and wake-up signals
- **Escalation** follows one-level-at-a-time pattern
- **LLM Judge** evaluates artifacts for completion

## Architecture

### Core Components

- **Graph**: Dependency graph with nodes (huddles) and edges (dependencies)
- **GraphNode**: Represents a huddle with execution status and results
- **GraphEdge**: Connections between huddles
- **Swarm/Huddle**: Multi-agent groups with huddle lead and members
- **EventBus**: Handles events and notifications

### Huddle Types

#### Product Huddle
- **Members**: Product Owner (lead), CEO
- **Tools**: createProject, cancelProject, evaluateCompletedProject, escalate, resolveBlocker, wait, provideFeedback
- **CEO Special**: requestHumanFeedback

#### Project Huddle
- **Members**: Project Lead (lead), Product Owner, CEO
- **Tools**: createTask, cancelTask, completeProject, escalate, resolveBlocker, wait, provideFeedback

### States

- **WAITING**: Non-escalatory, waiting for dependencies
- **BLOCKED**: Escalatory, waiting for parent resolution
- **EXECUTING**: Active execution
- **COMPLETED**: Successfully completed
- **FAILED**: Failed execution

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Or using pip with pyproject.toml
pip install -e .
```

## Usage

### Simple Demo

```python
import asyncio
from dynamic_bot_org_chart.core.execution import OrgChartRunner

async def main():
    runner = OrgChartRunner()
    graph = await runner.run(initial_product_description="Main Product")
    print(graph.visualize())

if __name__ == "__main__":
    asyncio.run(main())
```

### Custom Integration

```python
from dynamic_bot_org_chart.core.graph import Graph, GraphNode
from dynamic_bot_org_chart.core.events import EventBus
from dynamic_bot_org_chart.huddles.product_huddle import ProductHuddle

# Create event bus and graph
event_bus = EventBus()
graph = Graph(event_bus)

# Create CEO Product Huddle
ceo_huddle = ProductHuddle(
    huddle_id="ceo-product",
    event_bus=event_bus,
    graph=graph,
    is_ceo=True
)

# Add to graph
node = GraphNode(
    node_id="ceo-product",
    executor=ceo_huddle,
    context=ceo_huddle.context
)
graph.add_node(node)

# Execute
from dynamic_bot_org_chart.core.execution import GraphExecutor
executor = GraphExecutor(graph)
await executor.run()
```

## Directory Structure

```
dynamic-bot-org-chart/
├── DESIGN.md                     # Detailed design document
├── README.md                     # This file
├── requirements.txt              # Dependencies
├── pyproject.toml                # Project configuration
├── dynamic_bot_org_chart/        # Main package
│   ├── core/                     # Core components
│   │   ├── graph.py              # Graph, GraphNode, GraphEdge
│   │   ├── states.py             # State management
│   │   ├── events.py             # Event system
│   │   └── execution.py          # Graph executor
│   ├── huddles/                  # Huddle implementations
│   │   ├── base.py               # Base huddle
│   │   ├── product_huddle.py     # Product huddle
│   │   └── project_huddle.py     # Project huddle
│   ├── tools/                    # Tools for huddles
│   │   ├── base.py               # Base tool
│   │   ├── product_tools.py      # Product tools
│   │   ├── project_tools.py      # Project tools
│   │   ├── shared_tools.py       # Shared tools
│   │   └── ceo_tools.py          # CEO tools
│   ├── judges/                   # LLM judge
│   │   └── llm_judge.py          # Artifact evaluation
│   ├── integration/              # External integrations
│   │   └── claude_code.py        # Claude Code sessions
│   └── utils/                    # Utilities
│       └── helpers.py            # Helper functions
├── examples/                     # Example scripts
│   └── simple_demo.py            # Simple demo
└── tests/                        # Tests
    ├── test_graph.py             # Graph tests
    ├── test_states.py            # State tests
    ├── test_huddles.py           # Huddle tests
    └── test_tools.py             # Tool tests
```

## Key Features

### 1. Dynamic Graph Expansion
- Graph starts with CEO Product Huddle (root)
- Projects added dynamically via `createProject()` tool calls
- Dependencies established automatically

### 2. Event-Driven Communication
- Wake-up signals for escalation and blocker resolution
- Feedback between huddles
- Dependency completion notifications

### 3. Hierarchical Escalation
- One-level-at-a-time pattern
- Project Lead → Product Owner → CEO
- Clear audit trail

### 4. Circuit Breaker Pattern
- Execution timeouts per huddle
- Node-level timeouts
- Max execution limits for cyclic graphs

### 5. LLM Judge Evaluation
- Artifact evaluation against requirements
- Guidance for artifact creation/synthesis
- Score-based approval (threshold: 0.7)

### 6. CEO Special Permissions
- Request human feedback
- Final decision maker
- No escalation chain above CEO

## Configuration

### Execution Limits

```python
graph.set_execution_timeout(3600)      # 1 hour total
graph.set_node_timeout(300)             # 5 minutes per node
graph.set_max_node_executions(10)      # Max 10 executions per node
```

### LLM Judge Threshold

```python
evaluation = await llm_judge.evaluate(
    artifact=artifact,
    requirements=requirements,
    artifact_specification=artifact_specification,
    context=context,
    threshold=0.7  # Default approval threshold
)
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Style

```bash
# Format code
black dynamic_bot_org_chart/

# Lint code
ruff dynamic_bot_org_chart/

# Type check
mypy dynamic_bot_org_chart/
```

## Implementation Notes

### Current Status

This is a **framework implementation** that provides:
- Complete graph structure and state management
- Event-driven communication system
- Huddle (Swarm) abstractions
- Tools system for all huddle operations
- LLM judge for artifact evaluation
- Claude Code session integration (placeholder)

### Integration with Claude Agent SDK

The current implementation uses **placeholder** for actual Agent SDK integration. To fully integrate:

1. Replace huddle `execute()` methods with Agent SDK calls
2. Use Agent SDK's subagent capabilities for multi-agent execution
3. Implement tool calling through Agent SDK
4. Add session management for state persistence

### Claude Code Sessions

The current implementation provides a **simulation** of Claude Code sessions. To integrate with actual Claude Code:

1. Use the Agent SDK to create sessions
2. Pass task descriptions and test requirements
3. Wait for session completion
4. Extract artifacts (code changes, test results)

## License

MIT License

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Support

For issues and questions, please open an issue on GitHub.