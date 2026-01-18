"""Simple example of using the Dynamic Bot Org Chart with Strands."""

import asyncio
import os
from dynamic_bot_org_chart.graph.orchestrator import GraphOrchestrator


async def main():
    """Run a simple org chart example."""
    print("=" * 60)
    print("Dynamic Bot Org Chart - Simple Example")
    print("Built on AWS Strands Agents")
    print("=" * 60)

    # Create the graph orchestrator
    orchestrator = GraphOrchestrator()

    # Create the CEO Product Huddle (root node)
    ceo_huddle = orchestrator.create_ceo_product_huddle("ceo-product")

    print("\n" + "=" * 60)
    print("Initial Graph Structure")
    print("=" * 60)
    print(orchestrator.visualize())

    # Execute the graph
    # Note: In production, you would need to set ANTHROPIC_API_KEY
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\n⚠ ANTHROPIC_API_KEY not set. Skipping execution.")
        print("Set ANTHROPIC_API_KEY environment variable to run the agents.")
        return

    print("\n" + "=" * 60)
    print("Executing Graph")
    print("=" * 60)

    initial_prompt = """You are the CEO managing the top-level product.

Your task: Create a project to build a simple REST API with the following requirements:
- Endpoints: GET /users, POST /users
- Include tests
- Artifact: Working REST API code

After creating the project, wait for it to complete, then evaluate it."""

    result = await orchestrator.execute(initial_prompt)

    print("\n" + "=" * 60)
    print("Final Graph Structure")
    print("=" * 60)
    print(orchestrator.visualize())

    print("\n" + "=" * 60)
    print("State Summary")
    print("=" * 60)
    summary = orchestrator.get_state_summary()
    for key, value in summary.items():
        print(f"{key}: {value}")

    print("\n" + "=" * 60)
    print("Execution Complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
