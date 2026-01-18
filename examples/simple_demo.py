"""Simple demo of the Dynamic Bot Org Chart framework."""

import asyncio
from dynamic_bot_org_chart.core.execution import OrgChartRunner


async def main():
    """Run a simple demo."""
    print("=" * 60)
    print("Dynamic Bot Org Chart - Simple Demo")
    print("=" * 60)
    print()

    # Create runner
    runner = OrgChartRunner()

    # Run the org chart with initial product description
    graph = await runner.run(initial_product_description="Main Product")

    print()
    print("=" * 60)
    print("Demo Complete")
    print("=" * 60)
    print()
    print("Final Graph State:")
    print(graph.visualize())


if __name__ == "__main__":
    asyncio.run(main())
