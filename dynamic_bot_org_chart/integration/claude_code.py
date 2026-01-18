"""Integration with Claude Code sessions (tasks)."""

from typing import Any, Dict, Optional
from dataclasses import dataclass, field
import asyncio
import subprocess
import json
from datetime import datetime

from dynamic_bot_org_chart.core.states import TaskState, TaskContext


@dataclass
class ClaudeCodeSession:
    """Represents a Claude Code session (task)."""

    task_id: str
    project_id: str
    description: str
    test_requirements: str
    codebase_context: Dict[str, Any]
    execution_timeout: Optional[int] = None

    # Runtime state
    context: TaskContext = field(init=False)
    session_id: Optional[str] = None
    process: Optional[asyncio.subprocess.Process] = None

    def __post_init__(self):
        self.context = TaskContext(
            task_id=self.task_id,
            project_id=self.project_id,
            description=self.description,
            state=TaskState.PENDING
        )
        if self.execution_timeout:
            self.context.metadata.timeout = self.execution_timeout

    async def start(self, working_dir: str) -> bool:
        """Start the Claude Code session."""
        try:
            print(f"[Task {self.task_id}] Starting Claude Code session...")
            self.context.transition_to(TaskState.EXECUTING)

            # Build Claude Code command
            # In a real implementation, this would use the Agent SDK
            # For now, we'll simulate with a placeholder command
            command = self._build_command(working_dir)

            # Start the process
            self.process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir
            )

            print(f"[Task {self.task_id}] Claude Code session started")
            return True

        except Exception as e:
            print(f"[Task {self.task_id}] Failed to start: {e}")
            self.context.transition_to(TaskState.FAILED)
            self.context.error = str(e)
            return False

    def _build_command(self, working_dir: str) -> str:
        """Build the Claude Code command."""
        # This is a placeholder - in real implementation, use Agent SDK
        # For demo purposes, we'll create a simple simulation command

        # Create a task file with the description
        task_file = f"{working_dir}/task_{self.task_id}.json"

        task_data = {
            "task_id": self.task_id,
            "description": self.description,
            "test_requirements": self.test_requirements,
            "codebase_context": self.codebase_context
        }

        # Write task file
        with open(task_file, 'w') as f:
            json.dump(task_data, f, indent=2)

        # Placeholder command - in production, use actual Claude Code/Agent SDK
        return f"echo 'Claude Code session for task {self.task_id}' && sleep 2"

    async def wait_for_completion(self) -> Dict[str, Any]:
        """Wait for the Claude Code session to complete."""
        if not self.process:
            raise RuntimeError("Session not started")

        try:
            # Wait for process with timeout
            timeout = self.execution_timeout or 3600  # default 1 hour
            stdout, stderr = await asyncio.wait_for(
                self.process.communicate(),
                timeout=timeout
            )

            # Check return code
            if self.process.returncode == 0:
                self.context.transition_to(TaskState.COMPLETED)
                result = {
                    "status": "completed",
                    "stdout": stdout.decode() if stdout else "",
                    "stderr": stderr.decode() if stderr else "",
                    "artifact": self._extract_artifact(stdout)
                }
                self.context.artifact = result["artifact"]
                return result
            else:
                self.context.transition_to(TaskState.FAILED)
                self.context.error = f"Process exited with code {self.process.returncode}"
                return {
                    "status": "failed",
                    "error": self.context.error,
                    "stderr": stderr.decode() if stderr else ""
                }

        except asyncio.TimeoutError:
            print(f"[Task {self.task_id}] Timed out")
            self.context.transition_to(TaskState.FAILED)
            self.context.error = "Execution timeout"
            if self.process:
                self.process.kill()
            return {
                "status": "failed",
                "error": "Execution timeout"
            }
        except Exception as e:
            print(f"[Task {self.task_id}] Error: {e}")
            self.context.transition_to(TaskState.FAILED)
            self.context.error = str(e)
            return {
                "status": "failed",
                "error": str(e)
            }

    def _extract_artifact(self, stdout: bytes) -> Dict[str, Any]:
        """Extract artifact from stdout."""
        # Placeholder - in real implementation, parse actual output
        return {
            "code_changes": "Simulated code changes",
            "test_results": {
                "passed": True,
                "tests_run": 10,
                "tests_passed": 10,
                "coverage": 95.0
            }
        }

    async def cancel(self):
        """Cancel the Claude Code session."""
        print(f"[Task {self.task_id}] Cancelling...")

        if self.process:
            self.process.kill()
            await self.process.wait()

        self.context.transition_to(TaskState.FAILED)
        self.context.error = "Cancelled by user"


class ClaudeCodeManager:
    """Manager for Claude Code sessions."""

    def __init__(self, working_dir: str = "."):
        self.working_dir = working_dir
        self.sessions: Dict[str, ClaudeCodeSession] = {}

    async def create_task(
        self,
        task_id: str,
        project_id: str,
        description: str,
        test_requirements: str,
        execution_timeout: Optional[int] = None,
        codebase_context: Optional[Dict[str, Any]] = None
    ) -> ClaudeCodeSession:
        """Create a new Claude Code session (task)."""

        session = ClaudeCodeSession(
            task_id=task_id,
            project_id=project_id,
            description=description,
            test_requirements=test_requirements,
            codebase_context=codebase_context or {},
            execution_timeout=execution_timeout
        )

        self.sessions[task_id] = session

        # Start the session
        await session.start(self.working_dir)

        return session

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a Claude Code session."""
        session = self.sessions.get(task_id)
        if not session:
            return False

        await session.cancel()
        return True

    def get_task(self, task_id: str) -> Optional[ClaudeCodeSession]:
        """Get a task by ID."""
        return self.sessions.get(task_id)

    async def wait_for_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Wait for a task to complete."""
        session = self.sessions.get(task_id)
        if not session:
            return None

        return await session.wait_for_completion()

    def get_completed_tasks(self, project_id: str) -> list:
        """Get all completed tasks for a project."""
        return [
            session for session in self.sessions.values()
            if session.project_id == project_id
            and session.context.state == TaskState.COMPLETED
        ]
