# Dynamic Bot Org Chart - Built on AWS Strands Agents

An event-driven, agent-based framework for managing products and projects with hierarchical escalation, built entirely on **AWS Strands Agents**.

## Architecture

### Strands Components

- **Strands Graph**: Overall org chart structure with dynamic expansion
- **Strands Swarms**: Each huddle (Product Huddle, Project Huddle) is a multi-agent swarm
- **MCP Tools**: Operations (escalate, resolveBlocker, provideFeedback, wait, createProject, createTask, etc.)
- **Shared State**: Pydantic models for type-safe state management

### Huddle Types

#### Product Huddle (Strands Swarm)
- **Members**: Product Owner (lead), CEO (member)
- **Tools**: createProject, cancelProject, evaluateCompletedProject, resolveBlocker, wait, provideFeedback
- **CEO Special**: requestHumanFeedback (only for CEO Product Huddle)

#### Project Huddle (Strands Swarm)
- **Members**: Project Lead (lead), Product Owner (member), CEO (member)
- **Tools**: createTask, cancelTask, completeProject, escalate, resolveBlocker, wait, provideFeedback

### States

- **WAITING**: Non-escalatory, waiting for dependencies
- **BLOCKED**: Escalatory, waiting for parent resolution
- **EXECUTING**: Active execution
- **COMPLETED**: Successfully completed
- **FAILED**: Failed execution

## Installation

```bash
pip install -r requirements.txt
```

Required packages:
- `strands-agents>=1.0.0` - AWS Strands Agents framework
- `strands-agents-tools>=1.0.0` - Strands tools
- `anthropic>=0.39.0` - Anthropic API for LLM
- `pydantic>=2.0.0` - Data validation

## Quick Start

```python
import asyncio
from dynamic_bot_org_chart import GraphOrchestrator

async def main():
    # Create orchestrator
    orchestrator = GraphOrchestrator()

    # Create CEO Product Huddle (root)
    orchestrator.create_ceo_product_huddle("ceo-product")

    # Execute graph
    result = await orchestrator.execute("Manage the organization")

    # Visualize
    print(orchestrator.visualize())

if __name__ == "__main__":
    asyncio.run(main())
```

## How It Works

### 1. Graph Initialization

The GraphOrchestrator creates the CEO Product Huddle as the root node:

```python
orchestrator = GraphOrchestrator()
ceo_huddle = orchestrator.create_ceo_product_huddle("ceo-product")
```

### 2. Dynamic Graph Expansion

When the Product Owner creates a project using `createProject()`:
1. ProjectInfo is added to shared state
2. Project added to `pending_graph_nodes` queue
3. After current node execution completes, new Project Huddle node is created
4. Graph edge is added: `project -> product` (product depends on project)

### 3. Multi-Agent Swarms

Each huddle is a Strands Swarm with multiple agents:
- **Product Huddle**: Product Owner (lead) + CEO (member)
- **Project Huddle**: Project Lead (lead) + Product Owner + CEO

Agents can hand off to each other within the swarm.

### 4. MCP Tool Execution

Tools are wired up with custom executors that provide context:
- `huddle_id`: Current huddle ID
- `parent_huddle_id`: Parent huddle ID
- `shared_state`: Global OrgChartState

Example tool execution:
```python
result = await execute_create_project(
    description="Build REST API",
    artifact_specification="Working API with tests",
    context={
        "huddle_id": "product-1",
        "parent_huddle_id": "ceo-product",
        "shared_state": shared_state
    }
)
```

### 5. Event-Driven Communication

Using shared state and Pydantic models:
- **Escalations**: EscalationInfo with resolution tracking
- **Feedback**: FeedbackInfo for cross-huddle communication
- **State Changes**: HuddleState enum for type-safe states

## Project Structure

```
dynamic-bot-org-chart/
├── DESIGN.md                     # Detailed design document
├── README.md                     # Original README
├── README_STRANDS.md             # This file (Strands implementation)
├── requirements.txt              # Dependencies
├── dynamic_bot_org_chart/
│   ├── models.py                 # Pydantic models (state management)
│   ├── mcp_tools/                # MCP tool definitions and executors
│   │   ├── product_tools.py      # Product Huddle tools
│   │   ├── project_tools.py      # Project Huddle tools
│   │   ├── shared_tools.py       # Shared tools (all huddles)
│   │   └── ceo_tools.py          # CEO tools
│   ├── huddles/                  # Strands Swarm implementations
│   │   ├── product_huddle.py     # Product Huddle Swarm
│   │   └── project_huddle.py     # Project Huddle Swarm
│   └── graph/                    # Strands Graph orchestration
│       └── orchestrator.py       # GraphOrchestrator
├── examples/
│   └── simple_example.py         # Simple usage example
└── tests/                        # Unit and integration tests
    ├── test_product_huddle.py
    ├── test_project_huddle.py
    └── test_graph_orchestration.py
```

## Key Features

### 1. Dynamic Graph Expansion

Graph starts with CEO Product Huddle and expands dynamically as projects are created.

### 2. Hierarchical Escalation

One-level-at-a-time escalation:
- Project Lead → Product Owner → CEO

### 3. Cross-Huddle Communication

Agents can provide feedback up/down/across the org chart via `provideFeedback()`.

### 4. Type-Safe State Management

All state managed through Pydantic models for validation and type safety.

### 5. CEO Special Permissions

CEO Product Huddle can request human feedback via `requestHumanFeedback()`.

## Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_product_huddle.py

# Run with verbose output
pytest -v tests/
```

## Environment Variables

Required:
- `ANTHROPIC_API_KEY` - Your Anthropic API key for Claude

Optional:
- `STRANDS_LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)

## Development Status

### ✅ Implemented

- Pydantic models for state management
- MCP tools for all huddle operations
- Product Huddle as Strands Swarm
- Project Huddle as Strands Swarm
- Graph orchestration with dynamic expansion
- Unit tests for huddles
- Integration tests for graph

### 🚧 Remaining Work

- **Agent SDK Integration for Tasks**: Claude Code sessions for autonomous coding
- **LLM Judge**: Artifact evaluation with scoring
- **Full E2E Example**: Complete workflow demonstration
- **Documentation**: API reference, tutorials

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

## License

MIT License

## References

- [AWS Strands Agents](https://strandsagents.com/)
- [Strands Python SDK](https://github.com/strands-agents/sdk-python)
- [DESIGN.md](./DESIGN.md) - Detailed design specification
