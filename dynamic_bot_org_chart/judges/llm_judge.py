"""LLM judge for evaluating project artifacts."""

from typing import Any, Dict, Optional
from dataclasses import dataclass
import anthropic
import os


@dataclass
class JudgeEvaluation:
    """Result of LLM judge evaluation."""

    score: float  # 0.0 to 1.0
    reasoning: str
    approved: bool
    feedback: str
    threshold: float = 0.7  # Default approval threshold

    @classmethod
    def from_llm_response(cls, response: str, threshold: float = 0.7) -> "JudgeEvaluation":
        """Parse LLM response into JudgeEvaluation."""
        # Simple parsing - in production, use structured output
        lines = response.strip().split("\n")

        score = 0.0
        reasoning = ""
        feedback = ""

        for line in lines:
            if line.startswith("Score:"):
                try:
                    score = float(line.split(":")[1].strip())
                except:
                    score = 0.0
            elif line.startswith("Reasoning:"):
                reasoning = line.split(":", 1)[1].strip()
            elif line.startswith("Feedback:"):
                feedback = line.split(":", 1)[1].strip()

        # If no structured output, use the whole response as reasoning
        if not reasoning:
            reasoning = response

        approved = score >= threshold

        return cls(
            score=score,
            reasoning=reasoning,
            approved=approved,
            feedback=feedback,
            threshold=threshold
        )


class LLMJudge:
    """LLM judge for evaluating artifacts."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-5-20250929"):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self.client = anthropic.Anthropic(api_key=self.api_key)

    async def evaluate(
        self,
        artifact: Any,
        requirements: str,
        artifact_specification: str,
        context: Dict[str, Any],
        threshold: float = 0.7
    ) -> JudgeEvaluation:
        """Evaluate an artifact against requirements."""

        # Build prompt for judge
        prompt = self._build_evaluation_prompt(
            artifact=artifact,
            requirements=requirements,
            artifact_specification=artifact_specification,
            context=context
        )

        # Call Claude API
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            response_text = message.content[0].text

            # Parse response
            evaluation = JudgeEvaluation.from_llm_response(response_text, threshold=threshold)

            return evaluation

        except Exception as e:
            # If evaluation fails, return failed evaluation
            return JudgeEvaluation(
                score=0.0,
                reasoning=f"Evaluation failed: {str(e)}",
                approved=False,
                feedback=f"Could not evaluate artifact due to error: {str(e)}",
                threshold=threshold
            )

    def _build_evaluation_prompt(
        self,
        artifact: Any,
        requirements: str,
        artifact_specification: str,
        context: Dict[str, Any]
    ) -> str:
        """Build evaluation prompt for the judge."""

        prompt = f"""You are an expert evaluator for project artifacts. Your job is to evaluate whether an artifact meets the specified requirements and specifications.

**Requirements:**
{requirements}

**Artifact Specification:**
{artifact_specification}

**Artifact:**
{self._format_artifact(artifact)}

**Context:**
{self._format_context(context)}

Please evaluate the artifact and provide your assessment in the following format:

Score: <0.0-1.0>
Reasoning: <detailed explanation of your evaluation>
Feedback: <specific suggestions for improvement, or "Excellent work" if approved>

Guidelines:
- Score 0.0-0.3: Poor - artifact fails to meet basic requirements
- Score 0.4-0.6: Fair - artifact partially meets requirements but has significant gaps
- Score 0.7-0.8: Good - artifact meets requirements with minor issues
- Score 0.9-1.0: Excellent - artifact fully meets or exceeds requirements

Be thorough and specific in your evaluation."""

        return prompt

    def _format_artifact(self, artifact: Any) -> str:
        """Format artifact for display in prompt."""
        if isinstance(artifact, str):
            return artifact
        elif isinstance(artifact, dict):
            return "\n".join(f"{k}: {v}" for k, v in artifact.items())
        elif hasattr(artifact, "__dict__"):
            return "\n".join(f"{k}: {v}" for k, v in artifact.__dict__.items())
        else:
            return str(artifact)

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context for display in prompt."""
        lines = []
        for key, value in context.items():
            if isinstance(value, (list, dict)):
                lines.append(f"{key}:")
                lines.append(f"  {value}")
            else:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)

    async def evaluate_artifact_creation(
        self,
        task_results: list,
        artifact_specification: str,
        project_description: str,
        threshold: float = 0.7
    ) -> JudgeEvaluation:
        """Guide artifact creation/synthesis from task results."""

        prompt = f"""You are guiding the creation of a project artifact from completed tasks.

**Project Description:**
{project_description}

**Artifact Specification:**
{artifact_specification}

**Task Results:**
{self._format_task_results(task_results)}

Based on the task results and artifact specification, evaluate how well the artifact can be synthesized from the available outputs.

Provide guidance in the following format:

Score: <0.0-1.0>
Reasoning: <explanation of how to create/synthesize the artifact>
Feedback: <specific steps to create the artifact from task results>

Guidelines:
- Score 1.0 if all necessary components are available
- Score 0.7-0.9 if most components are available with minor synthesis needed
- Score 0.4-0.6 if significant synthesis work is needed
- Score 0.0-0.3 if critical components are missing"""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            response_text = message.content[0].text
            return JudgeEvaluation.from_llm_response(response_text, threshold=threshold)

        except Exception as e:
            return JudgeEvaluation(
                score=0.0,
                reasoning=f"Guidance failed: {str(e)}",
                approved=False,
                feedback=f"Could not provide guidance due to error: {str(e)}",
                threshold=threshold
            )

    def _format_task_results(self, task_results: list) -> str:
        """Format task results for display."""
        lines = []
        for i, result in enumerate(task_results, 1):
            lines.append(f"\nTask {i}:")
            if isinstance(result, dict):
                for k, v in result.items():
                    lines.append(f"  {k}: {v}")
            else:
                lines.append(f"  {result}")
        return "\n".join(lines)
