#!/usr/bin/env python3
"""
Task Extractor - Extract tasks from markdown files and append to tasks.md

Usage:
    # Extract from a specific file (on save)
    python task_extractor.py --file /path/to/file.md

    # Extract from a session log (on session complete)
    python task_extractor.py --session <session_id>

    # Extract from git diff
    python task_extractor.py --git-diff

    # Use LLM analysis for implicit tasks
    python task_extractor.py --file /path/to/file.md --llm

    # Use custom config
    python task_extractor.py --config /path/to/config.yaml --file /path/to/file.md
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import TypedDict

from config import get_config, reload_config


class TaskResult(TypedDict):
    added: list[str]
    completed: list[str]
    todos: list[str]


class ExtendedTaskResult(TypedDict):
    """Extended task result including LLM-detected implicit tasks."""
    added: list[str]
    completed: list[str]
    todos: list[str]
    implicit: list[dict]  # List of ImplicitTask dicts
    incomplete_sections: list[str]
    unanswered_questions: list[str]


def normalize_task(task: str, case_insensitive: bool = True) -> str:
    """Normalize task text for comparison."""
    normalized = task.strip()
    if case_insensitive:
        normalized = normalized.lower()
    return normalized


def get_existing_tasks() -> set[str]:
    """Read existing tasks from tasks.md and return normalized set."""
    config = get_config()
    existing = set()

    if not config.output_file.exists():
        return existing

    try:
        content = config.output_file.read_text(encoding="utf-8")
        case_insensitive = config.dedup_case_insensitive

        # Extract all tasks (both checked and unchecked)
        for match in config.patterns["unchecked"].finditer(content):
            existing.add(normalize_task(match.group(2), case_insensitive))

        for match in config.patterns["checked"].finditer(content):
            existing.add(normalize_task(match.group(2), case_insensitive))

    except Exception as e:
        print(f"Warning: Could not read existing tasks: {e}", file=sys.stderr)

    return existing


def filter_duplicates(tasks: TaskResult, existing: set[str]) -> TaskResult:
    """Remove tasks that already exist in tasks.md."""
    config = get_config()
    case_insensitive = config.dedup_case_insensitive

    return TaskResult(
        added=[t for t in tasks["added"] if normalize_task(t, case_insensitive) not in existing],
        completed=[t for t in tasks["completed"] if normalize_task(t, case_insensitive) not in existing],
        todos=[t for t in tasks["todos"] if normalize_task(t, case_insensitive) not in existing],
    )


def extract_tasks_from_file(file_path: Path) -> TaskResult:
    """Extract tasks from a markdown file."""
    config = get_config()

    if not file_path.exists():
        return TaskResult(added=[], completed=[], todos=[])

    # Check if file should be excluded
    if config.is_excluded(file_path):
        print(f"Skipping excluded file: {file_path.name}")
        return TaskResult(added=[], completed=[], todos=[])

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading file {file_path}: {e}", file=sys.stderr)
        return TaskResult(added=[], completed=[], todos=[])

    added = []
    completed = []
    todos = []

    patterns = config.patterns

    # Extract unchecked tasks
    for match in patterns["unchecked"].finditer(content):
        task_text = match.group(2).strip()
        if task_text:
            added.append(task_text)

    # Extract checked tasks
    for match in patterns["checked"].finditer(content):
        task_text = match.group(2).strip()
        if task_text:
            completed.append(task_text)

    # Extract TODO/FIXME
    for match in patterns["todo"].finditer(content):
        todo_text = match.group(1).strip()
        if todo_text:
            todos.append(todo_text)

    return TaskResult(added=added, completed=completed, todos=todos)


def analyze_with_llm(file_path: Path) -> ExtendedTaskResult | None:
    """
    Analyze a file using LLM to detect implicit tasks.

    Returns None if LLM analysis is not available or fails.
    """
    try:
        from llm_analyzer import LLMAnalyzer
    except ImportError:
        print("LLM analyzer not available (missing anthropic package)", file=sys.stderr)
        return None

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading file for LLM analysis: {e}", file=sys.stderr)
        return None

    try:
        analyzer = LLMAnalyzer()
        result = analyzer.analyze_document(content, file_path.name)

        return ExtendedTaskResult(
            added=[],
            completed=[],
            todos=[],
            implicit=result["implicit_tasks"],
            incomplete_sections=result["incomplete_sections"],
            unanswered_questions=result["unanswered_questions"],
        )
    except ValueError as e:
        print(f"LLM analysis error: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"LLM analysis failed: {e}", file=sys.stderr)
        return None


def merge_with_llm_results(
    pattern_tasks: TaskResult,
    llm_result: ExtendedTaskResult | None
) -> ExtendedTaskResult:
    """Merge pattern-based tasks with LLM analysis results."""
    if llm_result is None:
        return ExtendedTaskResult(
            added=pattern_tasks["added"],
            completed=pattern_tasks["completed"],
            todos=pattern_tasks["todos"],
            implicit=[],
            incomplete_sections=[],
            unanswered_questions=[],
        )

    return ExtendedTaskResult(
        added=pattern_tasks["added"],
        completed=pattern_tasks["completed"],
        todos=pattern_tasks["todos"],
        implicit=llm_result["implicit"],
        incomplete_sections=llm_result["incomplete_sections"],
        unanswered_questions=llm_result["unanswered_questions"],
    )


def extract_tasks_from_session(session_id: str) -> TaskResult:
    """Extract tasks from a session log file."""
    config = get_config()
    sessions_dir = config.sessions_dir

    # Find session file
    if sessions_dir.exists():
        for month_dir in sessions_dir.iterdir():
            if month_dir.is_dir():
                session_file = month_dir / f"session-{session_id}.md"
                if session_file.exists():
                    return extract_tasks_from_file(session_file)

    return TaskResult(added=[], completed=[], todos=[])


def extract_tasks_from_git_diff(repo_path: Path | None = None) -> TaskResult:
    """Extract task changes from git diff."""
    config = get_config()
    patterns = config.patterns

    if repo_path is None:
        repo_path = Path.cwd()

    added = []
    completed = []

    try:
        # Get diff for markdown files
        result = subprocess.run(
            ["git", "diff", "HEAD~1", "--", "*.md"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return TaskResult(added=[], completed=[], todos=[])

        diff_output = result.stdout

        # Parse diff lines
        for line in diff_output.split("\n"):
            # Added unchecked task
            if line.startswith("+") and not line.startswith("+++"):
                match = patterns["unchecked"].search(line[1:])
                if match:
                    added.append(match.group(2).strip())

            # Added checked task (completed)
            if line.startswith("+") and not line.startswith("+++"):
                match = patterns["checked"].search(line[1:])
                if match:
                    completed.append(match.group(2).strip())

    except Exception as e:
        print(f"Error reading git diff: {e}", file=sys.stderr)

    return TaskResult(added=added, completed=completed, todos=[])


def append_to_tasks_file(
    tasks: TaskResult | ExtendedTaskResult,
    source: str,
    skip_duplicates: bool | None = None
):
    """Append extracted tasks to tasks.md."""
    config = get_config()

    # Use config default if not specified
    if skip_duplicates is None:
        skip_duplicates = config.dedup_enabled

    # Filter duplicates if enabled (for pattern-based tasks)
    if skip_duplicates:
        existing = get_existing_tasks()
        original_counts = (len(tasks["added"]), len(tasks["completed"]), len(tasks["todos"]))
        filtered = filter_duplicates(
            TaskResult(
                added=tasks["added"],
                completed=tasks["completed"],
                todos=tasks["todos"]
            ),
            existing
        )
        # Update tasks with filtered values
        tasks = dict(tasks)  # Make a copy
        tasks["added"] = filtered["added"]
        tasks["completed"] = filtered["completed"]
        tasks["todos"] = filtered["todos"]
        filtered_counts = (len(tasks["added"]), len(tasks["completed"]), len(tasks["todos"]))

        skipped = sum(o - f for o, f in zip(original_counts, filtered_counts))
        if skipped > 0:
            print(f"Skipped {skipped} duplicate task(s)")

    # Check if we have extended results (with implicit tasks)
    implicit = tasks.get("implicit", [])
    incomplete_sections = tasks.get("incomplete_sections", [])
    unanswered_questions = tasks.get("unanswered_questions", [])

    # Filter implicit tasks for duplicates too
    if skip_duplicates and implicit:
        existing = get_existing_tasks()
        case_insensitive = config.dedup_case_insensitive
        implicit = [
            t for t in implicit
            if normalize_task(t["task"], case_insensitive) not in existing
        ]

    has_content = (
        tasks["added"] or tasks["completed"] or tasks["todos"] or
        implicit or incomplete_sections or unanswered_questions
    )

    if not has_content:
        print("No new tasks to add")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Build content to append
    lines = [f"\n## Tasks from {source} ({timestamp})\n"]

    if tasks["added"]:
        lines.append("\n### New Tasks\n")
        for task in tasks["added"]:
            lines.append(f"- [ ] {task}\n")

    if tasks["completed"]:
        lines.append("\n### Completed\n")
        for task in tasks["completed"]:
            lines.append(f"- [x] {task}\n")

    if tasks["todos"]:
        lines.append("\n### TODO/FIXME\n")
        for todo in tasks["todos"]:
            lines.append(f"- [ ] {todo}\n")

    # Add LLM-detected implicit tasks
    if implicit:
        lines.append("\n### Implicit Tasks (AI-detected)\n")
        for task in implicit:
            conf_marker = {"high": "!", "medium": "?", "low": "~"}.get(task["confidence"], "?")
            lines.append(f"- [ ] [{conf_marker}] {task['task']}\n")
            if task.get("reason"):
                lines.append(f"  - Reason: {task['reason']}\n")

    # Add incomplete sections as tasks
    if incomplete_sections:
        lines.append("\n### Incomplete Sections\n")
        for section in incomplete_sections:
            lines.append(f"- [ ] Complete section: {section}\n")

    # Add unanswered questions as tasks
    if unanswered_questions:
        lines.append("\n### Unanswered Questions\n")
        for question in unanswered_questions:
            lines.append(f"- [ ] Answer: {question}\n")

    # Append to tasks file
    output_file = config.output_file
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "a", encoding="utf-8") as f:
        f.writelines(lines)

    counts = [
        f"{len(tasks['added'])} new",
        f"{len(tasks['completed'])} completed",
        f"{len(tasks['todos'])} TODOs",
    ]
    if implicit:
        counts.append(f"{len(implicit)} implicit")
    if incomplete_sections:
        counts.append(f"{len(incomplete_sections)} incomplete sections")
    if unanswered_questions:
        counts.append(f"{len(unanswered_questions)} questions")

    print(f"Added: {', '.join(counts)}")


def main():
    parser = argparse.ArgumentParser(description="Extract tasks from markdown files")
    parser.add_argument("--file", "-f", type=Path, help="Extract from specific file")
    parser.add_argument("--session", "-s", type=str, help="Extract from session log")
    parser.add_argument("--git-diff", "-g", action="store_true", help="Extract from git diff")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Don't write to tasks.md")
    parser.add_argument("--no-dedup", action="store_true", help="Don't skip duplicate tasks")
    parser.add_argument("--config", "-c", type=Path, help="Path to config.yaml")
    parser.add_argument("--llm", "-l", action="store_true", help="Use LLM to detect implicit tasks")

    args = parser.parse_args()

    # Load custom config if specified
    if args.config:
        reload_config(args.config)

    file_path = None
    if args.file:
        tasks = extract_tasks_from_file(args.file)
        source = args.file.name
        file_path = args.file
    elif args.session:
        tasks = extract_tasks_from_session(args.session)
        source = f"session-{args.session}"
        # Find session file for LLM analysis
        config = get_config()
        if config.sessions_dir.exists():
            for month_dir in config.sessions_dir.iterdir():
                if month_dir.is_dir():
                    session_file = month_dir / f"session-{args.session}.md"
                    if session_file.exists():
                        file_path = session_file
                        break
    elif args.git_diff:
        tasks = extract_tasks_from_git_diff()
        source = "git-diff"
    else:
        parser.print_help()
        sys.exit(1)

    # Run LLM analysis if requested
    extended_tasks = None
    if args.llm and file_path:
        print(f"Running LLM analysis on {file_path.name}...")
        llm_result = analyze_with_llm(file_path)
        extended_tasks = merge_with_llm_results(tasks, llm_result)
    else:
        extended_tasks = merge_with_llm_results(tasks, None)

    if args.dry_run:
        print(f"Tasks from {source}:")
        print(f"  Added: {extended_tasks['added']}")
        print(f"  Completed: {extended_tasks['completed']}")
        print(f"  TODOs: {extended_tasks['todos']}")
        if args.llm:
            print(f"  Implicit: {[t['task'] for t in extended_tasks['implicit']]}")
            print(f"  Incomplete sections: {extended_tasks['incomplete_sections']}")
            print(f"  Unanswered questions: {extended_tasks['unanswered_questions']}")
    else:
        skip_duplicates = None if not args.no_dedup else False
        append_to_tasks_file(extended_tasks, source, skip_duplicates=skip_duplicates)


if __name__ == "__main__":
    main()
