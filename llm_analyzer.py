#!/usr/bin/env python3
"""
LLM Analyzer - Use Claude API to detect implicit tasks in documents.

This module analyzes documents to find:
- Implicit tasks (not marked with - [ ] but should be done)
- Incomplete sections
- Unanswered questions
- Follow-up items
- Draft/WIP content
"""

import json
import os
import sys
from pathlib import Path
from typing import TypedDict

# Try to import anthropic
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


class ImplicitTask(TypedDict):
    """An implicit task detected by LLM analysis."""
    task: str
    reason: str
    confidence: str  # "high", "medium", "low"
    source_text: str  # Original text that triggered this detection


class AnalysisResult(TypedDict):
    """Result of LLM document analysis."""
    implicit_tasks: list[ImplicitTask]
    incomplete_sections: list[str]
    unanswered_questions: list[str]
    summary: str


# System prompt for task analysis
ANALYSIS_PROMPT = """あなたはドキュメント分析のエキスパートです。
与えられたドキュメントを分析し、暗黙的なタスクや未完成の箇所を検出してください。

以下を探してください：
1. **暗黙的なタスク**: 明示的に「- [ ]」とマークされていないが、やるべきことを示唆する文
   - 例: 「後で確認する」「要検討」「〜が必要」「〜すべき」
2. **未完成セクション**: 空のセクション、「TBD」「WIP」「Draft」などの記載
3. **未回答の質問**: 「？」で終わる文で回答がないもの
4. **フォローアップ項目**: 「次回」「明日」「来週」などの時間表現を含むアクション

JSON形式で回答してください：
```json
{
  "implicit_tasks": [
    {
      "task": "タスクの内容",
      "reason": "なぜこれがタスクと判断したか",
      "confidence": "high/medium/low",
      "source_text": "元のテキスト"
    }
  ],
  "incomplete_sections": ["セクション名1", "セクション名2"],
  "unanswered_questions": ["質問1", "質問2"],
  "summary": "ドキュメント全体の完成度についての短い要約"
}
```

注意：
- 既に「- [ ]」や「- [x]」でマークされているタスクは除外
- TODO:, FIXME: など明示的なマーカーも除外（別途処理される）
- 確信度が低いものも含めてOK（ユーザーが判断できるように）
"""


class LLMAnalyzer:
    """Analyze documents using Claude API to detect implicit tasks."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
        use_feedback: bool = True,
    ):
        """
        Initialize the LLM analyzer.

        Args:
            api_key: Anthropic API key. If None, uses ANTHROPIC_API_KEY env var.
            model: Model to use for analysis.
            use_feedback: Whether to include feedback examples in prompts.
        """
        if not HAS_ANTHROPIC:
            raise ImportError(
                "anthropic package is required for LLM analysis. "
                "Install with: pip install anthropic"
            )

        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key required. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.model = model
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.use_feedback = use_feedback
        self._feedback_context = ""

        # Load feedback examples if enabled
        if use_feedback:
            self._load_feedback_examples()

    def _load_feedback_examples(self):
        """Load feedback examples for few-shot learning."""
        try:
            from feedback import get_store, format_examples_for_prompt

            store = get_store()
            stats = store.get_stats()

            # Only use feedback if we have enough examples
            if stats["total"] >= 3:
                examples = store.get_balanced_examples(count_per_type=3)
                self._feedback_context = format_examples_for_prompt(examples)

                # Add stats context
                self._feedback_context += f"\n\n## Feedback Statistics:\n"
                self._feedback_context += f"- Total feedback: {stats['total']}\n"
                self._feedback_context += f"- Acceptance rate: {stats['acceptance_rate']:.1%}\n"
                self._feedback_context += f"- Missed tasks reported: {stats['missed']}\n"

                if stats["acceptance_rate"] < 0.5:
                    self._feedback_context += (
                        "\nNote: Low acceptance rate suggests being more conservative "
                        "with task detection. Focus on high-confidence detections.\n"
                    )

                if stats["missed"] > 0:
                    # Calculate recall issue ratio
                    recall_ratio = stats["missed"] / (stats["accepted"] + stats["missed"]) if (stats["accepted"] + stats["missed"]) > 0 else 0
                    if recall_ratio > 0.1:
                        self._feedback_context += (
                            f"\nIMPORTANT: {stats['missed']} tasks were missed (not detected). "
                            "Be more aggressive in detecting implicit tasks. "
                            "Look carefully at the MISSED examples above and detect similar patterns.\n"
                        )
        except Exception as e:
            # Feedback not available, continue without it
            print(f"Note: Feedback not available: {e}", file=sys.stderr)

    def analyze_document(self, content: str, file_name: str = "") -> AnalysisResult:
        """
        Analyze a document to detect implicit tasks.

        Args:
            content: The document content to analyze.
            file_name: Optional file name for context.

        Returns:
            AnalysisResult with detected implicit tasks and issues.
        """
        if not content.strip():
            return AnalysisResult(
                implicit_tasks=[],
                incomplete_sections=[],
                unanswered_questions=[],
                summary="Empty document"
            )

        # Truncate very long documents
        max_chars = 8000
        if len(content) > max_chars:
            content = content[:max_chars] + "\n\n[...truncated...]"

        user_message = f"ファイル: {file_name}\n\n```markdown\n{content}\n```"

        # Build system prompt with feedback context if available
        system_prompt = ANALYSIS_PROMPT
        if self._feedback_context:
            system_prompt += f"\n\n# User Feedback History\n{self._feedback_context}"

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )

            # Parse the response
            response_text = response.content[0].text

            # Extract JSON from response
            result = self._parse_response(response_text)
            return result

        except anthropic.APIError as e:
            print(f"API error: {e}", file=sys.stderr)
            return self._empty_result(f"API error: {e}")
        except Exception as e:
            print(f"Analysis error: {e}", file=sys.stderr)
            return self._empty_result(f"Error: {e}")

    def _parse_response(self, response_text: str) -> AnalysisResult:
        """Parse the LLM response into AnalysisResult."""
        try:
            # Try to extract JSON from the response
            # Handle case where JSON is wrapped in ```json ... ```
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_str = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                json_str = response_text[start:end].strip()
            else:
                # Try to find JSON object directly
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                json_str = response_text[start:end]

            data = json.loads(json_str)

            # Convert to proper types
            implicit_tasks = []
            for task in data.get("implicit_tasks", []):
                implicit_tasks.append(ImplicitTask(
                    task=task.get("task", ""),
                    reason=task.get("reason", ""),
                    confidence=task.get("confidence", "medium"),
                    source_text=task.get("source_text", "")
                ))

            return AnalysisResult(
                implicit_tasks=implicit_tasks,
                incomplete_sections=data.get("incomplete_sections", []),
                unanswered_questions=data.get("unanswered_questions", []),
                summary=data.get("summary", "")
            )

        except json.JSONDecodeError as e:
            print(f"Failed to parse LLM response: {e}", file=sys.stderr)
            print(f"Response was: {response_text[:500]}", file=sys.stderr)
            return self._empty_result("Failed to parse response")

    def _empty_result(self, summary: str = "") -> AnalysisResult:
        """Return an empty analysis result."""
        return AnalysisResult(
            implicit_tasks=[],
            incomplete_sections=[],
            unanswered_questions=[],
            summary=summary
        )

    def record_feedback(
        self,
        task: ImplicitTask,
        feedback: str,
        source_file: str = "",
        modified_text: str | None = None,
        reason: str | None = None,
    ):
        """
        Record user feedback for a detected task.

        Args:
            task: The ImplicitTask that was shown to user.
            feedback: "accepted", "rejected", or "modified".
            source_file: File where task was detected.
            modified_text: User's modified version (if feedback is "modified").
            reason: Reason for rejection (if feedback is "rejected").
        """
        try:
            from feedback import get_store

            store = get_store()
            store.add_feedback(
                task_text=task["task"],
                feedback=feedback,
                source_text=task.get("source_text", ""),
                source_file=source_file,
                modified_text=modified_text,
                reason=reason,
                confidence=task.get("confidence", "medium"),
            )
        except Exception as e:
            print(f"Failed to record feedback: {e}", file=sys.stderr)


def analyze_file(file_path: Path, api_key: str | None = None) -> AnalysisResult:
    """
    Convenience function to analyze a file.

    Args:
        file_path: Path to the file to analyze.
        api_key: Optional API key.

    Returns:
        AnalysisResult with detected issues.
    """
    if not file_path.exists():
        return AnalysisResult(
            implicit_tasks=[],
            incomplete_sections=[],
            unanswered_questions=[],
            summary="File not found"
        )

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return AnalysisResult(
            implicit_tasks=[],
            incomplete_sections=[],
            unanswered_questions=[],
            summary=f"Error reading file: {e}"
        )

    analyzer = LLMAnalyzer(api_key=api_key)
    return analyzer.analyze_document(content, file_path.name)


def main():
    """CLI entry point for testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Analyze documents for implicit tasks")
    parser.add_argument("file", type=Path, help="File to analyze")
    parser.add_argument("--api-key", help="Anthropic API key (or set ANTHROPIC_API_KEY)")

    args = parser.parse_args()

    try:
        result = analyze_file(args.file, args.api_key)

        print(f"\n📄 Analysis of: {args.file.name}")
        print("=" * 50)

        if result["implicit_tasks"]:
            print(f"\n🔍 Implicit Tasks ({len(result['implicit_tasks'])}):")
            for task in result["implicit_tasks"]:
                conf_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task["confidence"], "⚪")
                print(f"  {conf_icon} {task['task']}")
                print(f"      Reason: {task['reason']}")
                if task["source_text"]:
                    print(f"      Source: \"{task['source_text'][:50]}...\"")

        if result["incomplete_sections"]:
            print(f"\n📝 Incomplete Sections ({len(result['incomplete_sections'])}):")
            for section in result["incomplete_sections"]:
                print(f"  - {section}")

        if result["unanswered_questions"]:
            print(f"\n❓ Unanswered Questions ({len(result['unanswered_questions'])}):")
            for q in result["unanswered_questions"]:
                print(f"  - {q}")

        print(f"\n📊 Summary: {result['summary']}")

    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Install with: pip install anthropic", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
