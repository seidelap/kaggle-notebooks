# Dynamic Bot Org Chart - Design Document

## Overview

An event-driven, agent-based framework for managing products and projects with hierarchical escalation and circuit breaker patterns. Built entirely on Strands framework, running locally. Uses Strands Swarms for huddles and Strands Graphs for the dependency structure. Projects use Claude Code sessions as tasks for autonomous coding work.

## Core Architecture

### Strands Components

- **Swarm**: Each huddle is a Swarm containing the huddle lead and all higher-ranking members
- **Graph**: Inverted pyramid structure where huddles are nodes with dependencies
- **GraphNode**: Represents a huddle with dependencies, execution status, and results
- **GraphEdge**: Connections between huddles with optional conditions

### Key Concepts

1. **Huddles (Swarms)**: Multi-agent groups with huddle lead and higher-ranking members
2. **Graph Structure**: Products create projects - projects are downstream (children) of products
3. **Tasks**: Claude Code sessions created by Project Huddle - not graph nodes, external sessions
4. **State-Driven Execution**: Execution status maps to project state
5. **Cross-Swarm Communication**: Agents can bring feedback between their huddles
6. **Product/Project Relationship**: Products create projects; completed projects can be converted to new products or kept as part of parent product

## Huddle Types

### Product Huddle

**Purpose**: Manage products, create/cancel projects, evaluate completed projects

**Members**: Product Owner (huddle lead), CEO

**Special Cases**:
- **CEO Product Huddle**: Root huddle with special permission to request human feedback

**Tools Available to Huddle Lead (PO)**:
- `createProject(description, artifactSpecification, executionTimeout, ...)` - Creates a new Project Huddle with artifact specification for how project artifact should be created/synthesized
- `cancelProject(projectId)`
- `cancelProduct(productId)`
- `evaluateCompletedProject(projectId)` - Evaluates a completed project, decides whether to convert to new product or keep as part of parent product for maintenance
- `evaluateProductLevels()` - Evaluates and manages direct children (re-org, creation, cancellation of direct children)
- `escalate(reason, wait=True)` - Escalates to CEO, optionally waits for response
- `resolveBlocker(childNodeId, wait=True)` - Resolves blocker in child project, optionally waits
- `wait()` - Sleeps until any project completes or feedback is provided

**Tools Available to All Members**:
- `provideFeedback(targetHuddle, feedback)` - Can go up/down/across chain, or to sibling/cousin huddles

### Project Huddle

**Purpose**: Manage project, create/coordinate Claude Code sessions (tasks)

**Members**: Project Lead (huddle lead), Product Owner, CEO

**Key Concepts**:
- **Tasks**: Claude Code sessions created by Project Huddle - not graph nodes, external sessions
- **Task Dependencies**: If any task is not immediately ready to start, the agent should not start it. Agent has access to `wait()` if another task is required first.
- **Artifact Creation**: Project Lead is responsible for project artifact creation, which is specified by PO when the project is defined. LLM judge is used to define how artifact is created or synthesized.

**Tools Available to Huddle Lead (Project Lead)**:
- `createTask(description, testRequirements, executionTimeout, codebaseContext, ...)` - Creates Claude Code session (task)
- `cancelTask(taskId)` - Cancels Claude Code session
- `wait()` - Sleeps until any task completes or feedback is provided
- `escalate(reason, wait=True)` - Escalates to Product Owner, optionally waits for response
- `resolveBlocker(childNodeId, wait=True)` - Resolves blocker (if tasks can block)
- `completeProject(artifact, evaluation)` - Completes project with artifact and LLM judge evaluation

**Tools Available to All Members**:
- `provideFeedback(targetHuddle, feedback)` - Can go up/down/across chain

## Graph Structure

### Dependency Flow

```
Product Huddle (root)
    ↓ dependency
Project Huddle (downstream/child)
```

**Key Points**:
- Products create projects - projects are downstream (children) of products
- **Tasks are NOT graph nodes** - they are Claude Code sessions (external)
- Information flows **automatically** from project → product
- **Dependencies are unidirectional** (product → project)
- **Blockers do NOT create graph dependencies** - they're wake-up signals, not dependencies
- When blocker resolved via `resolveBlocker()`, it wakes up the blocked node (similar to feedback mechanism)
- Both parent and child can continue running after blocker resolution

### GraphNode Properties

Each huddle (Swarm) is a GraphNode with:

- `node_id`: Unique identifier (projectId, productId)
- `executor`: The Swarm instance (huddle)
- `dependencies`: Set of upstream nodes (projects for products)
- `execution_status`: Maps to project/product state (PENDING, EXECUTING, COMPLETED, FAILED)
- `result`: NodeResult after execution (COMPLETED, FAILED, BLOCKED)
- `execution_time`: Time taken to execute

### Execution Behavior

**Default Behavior**: Node executes when dependencies complete

**Scenario: Dependency Completes During Execution**:
1. Product huddle is executing (reasoning, planning)
2. Project completes (while product huddle executing)
3. Completion is queued/buffered
4. Product huddle finishes current execution
5. Product huddle re-executes with new dependency result
6. Product huddle can reason about new state and create new projects

**Incremental Execution**:
- Product huddle receives project completions **incrementally**
- Product huddle can reason about next actions after each completion
- Product huddle can create new projects as dependencies are met
- Example: Project A completes → Product huddle creates Project C (which depends on A)

**Task Execution (Claude Code Sessions)**:
- Tasks are Claude Code sessions created by Project Huddle
- Tasks are NOT graph nodes - they are external sessions
- Project Huddle manages task lifecycle (create, wait, cancel)
- If any task is not immediately ready to start, Project Lead should not start it
- Project Lead can use `wait()` if another task is required first
- Tasks complete independently and return artifacts to Project Huddle

## State Mapping

### GraphNode Execution Status → Project/Product State

| GraphNode Status | Project/Product State | Description |
|-----------------|----------------------|-------------|
| PENDING | WAITING | Non-escalatory, only has dependencies on projects |
| PENDING | BLOCKED | Escalatory, has dependency on parent (but projects can continue) |
| EXECUTING | EXECUTING | Active execution, can have projects executing simultaneously |
| COMPLETED | COMPLETED | Project/product completed successfully |
| FAILED | FAILED | Project/product failed |

### State Details

**WAITING**:
- Non-escalatory state
- Only has dependencies on projects
- Product is waiting for projects to complete
- No escalation needed

**BLOCKED**:
- Escalatory state
- **No graph dependency created** - blocker is a wake-up signal, not a dependency
- **Projects can continue executing** (work continues, but product completion is blocked)
- Requires resolution from parent via `resolveBlocker()`
- When resolved, wakes up (similar to feedback mechanism) and continues execution
- Both parent and child can continue running after resolution

**EXECUTING**:
- Active execution
- Can have projects executing simultaneously
- Can receive dependency completions during execution
- Re-executes when dependencies complete

**COMPLETED**:
- Project/product completed successfully
- All dependencies satisfied
- Evaluation passed (if applicable)

**FAILED**:
- Project/product failed
- Cannot continue
- May trigger escalation

### Task States (Claude Code Session States)

| Task State | Description |
|------------|-------------|
| PENDING | Created but not started |
| EXECUTING | Claude Code session running |
| BLOCKED | Claude Code returned blocked status |
| COMPLETED | Claude Code completed successfully |
| FAILED | Claude Code failed or timed out |

## Escalation Pattern

### One-Level-at-a-Time Escalation

**Pattern**: Escalate one level at a time (no skipping)

**Flow**:
```
Project Lead blocked → escalates(reason, wait=True) → Project Huddle enters BLOCKED state
  ↓ (wake-up signal sent to Product Huddle, no dependency created)
Product Owner receives escalation notification (Product Huddle can continue or wait)
  ├─→ Can resolve? → resolveBlocker(childNodeId="project-123", wait=True)
  │   → Wake-up signal sent to Project Huddle
  │   → Project Huddle wakes up, exits BLOCKED state, continues
  │   → Product Owner can continue reasoning until wait() called
  │   → Both can run concurrently after resolution
  └─→ Cannot resolve? → escalates(reason, wait=True) → Product Huddle enters BLOCKED state
      ↓ (wake-up signal sent to CEO, no dependency created)
CEO receives escalation notification
  ├─→ Can resolve? → resolveBlocker(childNodeId="product-456", wait=True)
  │   → Wake-up signal sent to Product Huddle
  │   → Product Huddle wakes up, exits BLOCKED state, continues
  │   → Product Owner can then resolve blocker in Project Huddle
  │   → Both can run concurrently after resolution
  └─→ Cannot resolve? → requests human feedback
      ↓
... continues one level at a time up to CEO
```

**Rationale**:
- Each level gets opportunity to resolve
- Context accumulates as it goes up
- Clear audit trail
- Natural flow: "I tried TL, they couldn't help, now trying PL"

### Escalation and Blocker Resolution Tools

**Escalation** (Huddle Lead only):
```python
escalate(reason, wait=True)  # Escalates to immediate next level
# - Sets state to BLOCKED, enters wait state
# - wait=True: Waits for response (default for Product/Task huddles)
# - wait=False: Continues execution (optional for Product/Task huddles)
# - In Subtask huddles: wait is always True (ignored if set to False)
# - Creates dependency on parent (escalation chain)
```

**Blocker Resolution** (Huddle Lead only):
```python
resolveBlocker(childNodeId, wait=True)  # Resolves blocker in child node
# - Called by parent huddle to resolve blocker in child
# - Sends wake-up signal to child (similar to feedback mechanism)
# - wait=True: Waits after resolution (default)
# - wait=False: Continues execution immediately
# - Allows reasoning to continue until wait() is called again
# - Child node wakes up, exits BLOCKED state and continues
# - Both parent and child can continue running (no dependency relationship)
```

**Feedback** (All members):
```python
provideFeedback(targetHuddle, feedback)  # Provides feedback to target huddle
# - Can go up chain (to parent huddle)
# - Can go down chain (to child huddle)
# - Can go across chain (to sibling/cousin huddles via common ancestor)
# - Recipient is always yourself in the target huddle
# - Wakes up WAITING huddles
# - Makes other huddles active
```

### Escalation Chain

```
Project Lead → Product Owner → CEO
```

**Note**: Project Lead escalates to Product Owner, who can escalate to CEO

## Cross-Swarm Communication

### Pattern: Agent Brings Feedback Between Huddles

**Concept**: An agent (e.g., PO) can take feedback/concerns from one huddle and bring it to another huddle where they're also present.

**Example**:
1. PO is in Project Huddle A
2. Project Huddle A has a concern/feedback
3. PO formulates message in Project Huddle A
4. PO brings message to Product Huddle (where PO is also present)
5. PO acts on message in Product Huddle
6. PO can bring response back to Project Huddle A

**Mechanics**:
- Message is formulated in source huddle by an agent
- Same agent brings message to destination huddle (where they're also present)
- Agent acts on message in destination huddle
- Wakes up WAITING huddles
- Makes other huddles active

**Use Cases**:
- Escalation feedback
- Cross-task coordination
- Resource sharing
- Priority adjustments

## Circuit Breaker Pattern

### Execution Time Limits

Instead of token budgets, use Strands built-in execution limits:

**Per-Huddle Limits**:
- `set_execution_timeout()`: Maximum total execution time for huddle
- `set_node_timeout()`: Maximum time per node/agent execution
- `set_max_node_executions()`: Maximum node executions (for cyclic graphs)

**Configuration**:
```python
graph.set_execution_timeout(3600)  # 1 hour total
graph.set_node_timeout(300)  # 5 minutes per agent
graph.set_max_node_executions(10)  # Max 10 executions per node
```

### Failure Handling

**Time Limit Reached**:
1. Strands automatically stops execution
2. Current state is captured
3. Result sent up the chain (automatic escalation)
4. Parent huddle receives failure notification

**Manual Escalation**:
- Agent calls `escalate()` when blocked
- Escalation follows one-level-at-a-time pattern
- Each level attempts resolution before escalating

## Acceptance Criteria and Completion

### Task Completion (Claude Code Session)

**Acceptance Criteria**:
- ✅ All tests pass
- ✅ Code is the artifact

**Completion Flow**:
1. Project Huddle creates task (Claude Code session)
2. Claude Code session runs autonomously:
   - Writes tests first (TDD)
   - Implements code
   - Runs tests
   - All tests must pass
3. Claude Code session completes
4. Project Huddle receives artifact (code changes, test results)

**Completion Validation**:
- Claude Code session returns:
  - Code artifact (file changes, git diff)
  - Test results (pass/fail, coverage)
  - Completion status

**Failure Handling**:
- If tests fail, Claude Code session continues until all pass
- If session times out or fails, Project Huddle receives failure status
- Project Huddle can create new task or escalate

### Project Completion

**Acceptance Criteria**:
- ✅ Artifact is produced (as specified by PO in artifactSpecification)
- ✅ LLM judge validates artifact meets requirements
- ✅ All tasks complete (all Claude Code sessions complete)

**Completion Flow**:
1. Project Huddle creates tasks (Claude Code sessions)
2. All tasks complete (tests pass, code artifacts produced)
3. Project Lead creates project artifact:
   - Uses artifactSpecification provided by PO
   - May combine task outputs or create new artifact
   - Uses LLM judge to guide creation/synthesis
4. LLM judge evaluates artifact
5. If judge approves → Project completes

**Artifact Creation**:
- Project Lead is responsible for project artifact creation
- Artifact specification is provided by PO when project is created
- LLM judge is used to define how artifact is created or synthesized
- Artifact can combine task outputs or be created independently

**Completion Validation**:
- `completeProject(artifact, evaluation)` tool:
  - Validates artifact is provided
  - Runs LLM judge evaluation
  - Judge checks artifact against project requirements and artifactSpecification
  - Judge provides score and reasoning
  - If score meets threshold → Project completes
  - If score below threshold → Project continues or escalates

**LLM Judge Evaluation**:
```python
evaluation = llm_judge.evaluate(
    artifact=result.artifact,
    requirements=project.requirements,
    artifactSpecification=project.artifactSpecification,
    context={
        'task_results': completed_tasks,
        'project_description': project.description
    }
)

# Returns:
# {
#   'score': 0.0-1.0,
#   'reasoning': 'Explanation of evaluation',
#   'approved': True/False,
#   'feedback': 'Suggestions for improvement'
# }
```

**Artifact Types**:
- **Executable Script**: Python, shell, etc. - must be runnable
- **Text Document**: Analysis, report, documentation
- **Data File**: Processed data, dataset
- **Model/Configuration**: Trained model, config file
- **Codebase Changes**: Combined changes from multiple tasks
- **Other**: Any deliverable specified in artifactSpecification

### Product Evaluation

**After Project Completion**:
- Product Owner evaluates completed project via `evaluateCompletedProject(projectId)`
- PO decides:
  - **Convert to new product**: Project becomes standalone product for maintenance
  - **Keep as part of parent product**: Project results integrated into parent product
- Decision is based on project scope, maintenance needs, and product strategy

## Graph Construction

### Dynamic Graph Expansion

**Initial State**:
- Graph starts with just the **CEO Product Huddle** (root)
- No explicit graph building needed

**Expansion via Tool Calls**:
- When Product Huddle calls `createProject()`, a new Project Huddle node is created and added to graph
- Dependencies are automatically established (product → project)
- **Tasks are NOT graph nodes** - they are Claude Code sessions (external)

**Graph Structure** (built dynamically):
```
CEO Product Huddle (root, initial node)
  ↑ (dependency: Project Huddle 1 → CEO Product Huddle, when createProject() called)
Project Huddle 1 (entry node, no dependencies)
  - Creates Claude Code sessions (tasks) - external, not graph nodes
```

**Dependency Flow**:
- Project Huddle 1 (upstream/parent) → CEO Product Huddle (downstream/child)
- Information flows automatically from project → product
- Tasks are managed by Project Huddle but are not part of the graph

**Execution Limits** (configured per huddle):
- `executionTimeout`: Maximum total execution time for huddle
- `nodeTimeout`: Maximum time per agent execution
- `maxNodeExecutions`: Maximum node executions (for cyclic graphs)

### Graph Execution

**Entry Points**:
- Projects are entry nodes (no dependencies)
- Products depend on projects

**Execution Flow**:
1. Graph starts with CEO Product Huddle
2. Product Huddle creates projects via tool calls
3. Project Huddles create Claude Code sessions (tasks) - external, not graph nodes
4. Projects execute independently (entry nodes)
5. When project completes, dependent product executes
6. CEO Product Huddle is the root (final sink)

**Task Execution (External)**:
- Tasks are Claude Code sessions created by Project Huddle
- Tasks are NOT graph nodes - they are external sessions
- Project Huddle manages task lifecycle (create, wait, cancel)
- Tasks complete independently and return artifacts to Project Huddle

## CEO Product Huddle

### Special Permissions

**Human Feedback Request**:
- CEO can request human feedback in their Product Huddle
- Special tool: `requestHumanFeedback(request, context)`
- System pauses until human responds
- Human response triggers continuation

**Otherwise Same**:
- Same structure as other Product Huddles
- Same tools and capabilities
- Same escalation patterns

## Implementation Notes

### Local Execution

- Everything runs on local machine
- No AWS/Lambda infrastructure needed
- Strands handles all orchestration
- Session management for state persistence

### State Persistence

- Strands session management handles state
- Agent state persists across executions
- Graph state maintained by Strands
- Can pause and resume execution

### Cyclic Graph Support

- Strands supports cyclic graphs
- Escalation creates cycles (up and down)
- Feedback creates cycles (back to originator)
- `set_max_node_executions()` prevents infinite loops

## Example Flow

### Complete Project Execution

```
1. Product Huddle creates Project
   ↓
2. Project Huddle starts executing
   ↓
3. Project Huddle creates Task A (Claude Code session)
   ↓
4. Project Huddle creates Task B (Claude Code session) - parallel
   ↓
5. Claude Code sessions run autonomously
   - Task A: writes tests, implements code, runs tests
   - Task B: writes tests, implements code, runs tests
   ↓
6. Task A completes → Project Huddle receives result
   ↓
7. Project Huddle reasons: "A done, can create C"
   ↓
8. Project Huddle creates Task C (Claude Code session)
   ↓
9. Task B completes → Project Huddle receives result
   ↓
10. Task C completes → Project Huddle receives result
   ↓
11. Project Huddle evaluates: All tasks complete
   ↓
12. Project Lead creates project artifact (uses artifactSpecification from PO, LLM judge guides creation/synthesis)
   ↓
13. LLM judge evaluates artifact
   ↓
14. If approved → Project Huddle completes → Product Huddle receives result
   ↓
15. Product Huddle evaluates completed project
   - Can convert to new product
   - Or keep as part of parent product
```

### Escalation and Resolution Flow

```
1. Project Lead in Project Huddle is blocked
   ↓
2. Project Lead: escalate("Need requirements", wait=True)
   ↓
3. Project Huddle enters BLOCKED state, wake-up signal sent to Product Huddle
   ↓ (no dependency created, just notification)
4. Product Huddle receives escalation notification (can continue or wait)
   ↓
5. Product Owner can resolve?
   ├─→ Yes: resolveBlocker(childNodeId="project-123", wait=True)
   │   → Wake-up signal sent to Project Huddle
   │   → Project Huddle wakes up, exits BLOCKED state, continues
   │   → Product Owner can continue reasoning until wait() called
   │   → Both can run concurrently after resolution
   └─→ No: escalate(reason, wait=True)
       ↓
6. Product Huddle enters BLOCKED state, wake-up signal sent to CEO
   ↓ (no dependency created, just notification)
7. CEO receives escalation notification
   ↓
8. CEO can resolve?
   ├─→ Yes: resolveBlocker(childNodeId="product-456", wait=True)
   │   → Wake-up signal sent to Product Huddle
   │   → Product Huddle wakes up, exits BLOCKED state, continues
   │   → Product Owner can then resolve blocker in Project Huddle
   │   → Both can run concurrently after resolution
   └─→ No: requests human feedback
       ↓
9. ... continues up to CEO if needed
```

## Summary

- **Huddles**: Swarms with huddle lead and higher-ranking members
- **Graph**: Products create projects, dynamically expanded via tool calls (starts with CEO Product Huddle)
- **Products**: Manage products, create/evaluate projects
- **Projects**: Manage projects, create/coordinate Claude Code sessions (tasks)
- **Tasks**: Claude Code sessions - external, not graph nodes
- **State**: Maps GraphNode status to project/product state (WAITING, BLOCKED, EXECUTING, COMPLETED, FAILED)
- **Escalation**: One-level-at-a-time, huddle lead only, creates cycles
- **Feedback**: All members can provide feedback up/down/across chain
- **Tools**: Most tools only available to huddle lead, except provideFeedback (all members)
- **Wait**: Product and Project huddles can wait() until any project/task completes or feedback provided
- **Task Dependencies**: If any task is not immediately ready to start, agent should not start it. Agent uses wait() if another task is required first.
- **Artifact Creation**: Project Lead creates project artifact as specified by PO, using LLM judge for creation/synthesis
- **Product Evaluation**: PO decides after project completion whether to convert to new product or keep as part of parent product
- **Local**: Everything runs on local machine with Strands
