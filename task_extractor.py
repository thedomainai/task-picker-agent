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
"""

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Configuration
WORKSPACE_DIR = Path.home() / "workspace/obsidian_vault"
TASKS_FILE = WORKSPACE_DIR / "docs/01_resource/tasks.md"
SESSIONS_DIR = WORKSPACE_DIR / "docs/01_resource/sessions"

# Task patterns
TASK_UNCHECKED = re.compile(r"^(\s*)-\s*\[\s*\]\s*(.+)$", re.MULTILINE)
TASK_CHECKED = re.compile(r"^(\s*)-\s*\[x\]\s*(.+)$", re.MULTILINE | re.IGNORECASE)
TODO_PATTERN = re.compile(r"(?:TODO|FIXME|XXX):\s*(.+)$", re.MULTILINE | re.IGNORECASE)


def extract_tasks_from_file(file_path: Path) -> dict:
    """Extract tasks from a markdown file."""
    if not file_path.exists():
        return {"added": [], "completed": [], "todos": []}

    content = file_path.read_text(encoding="utf-8")

    added = []
    completed = []
    todos = []

    # Extract unchecked tasks
    for match in TASK_UNCHECKED.finditer(content):
        task_text = match.group(2).strip()
        if task_text:
            added.append(task_text)

    # Extract checked tasks
    for match in TASK_CHECKED.finditer(content):
        task_text = match.group(2).strip()
        if task_text:
            completed.append(task_text)

    # Extract TODO/FIXME
    for match in TODO_PATTERN.finditer(content):
        todo_text = match.group(1).strip()
        if todo_text:
            todos.append(todo_text)

    return {"added": added, "completed": completed, "todos": todos}


def extract_tasks_from_session(session_id: str) -> dict:
    """Extract tasks from a session log file."""
    # Find session file
    for month_dir in SESSIONS_DIR.iterdir():
        if month_dir.is_dir():
            session_file = month_dir / f"session-{session_id}.md"
            if session_file.exists():
                return extract_tasks_from_file(session_file)

    return {"added": [], "completed": [], "todos": []}


def extract_tasks_from_git_diff(repo_path: Path = None) -> dict:
    """Extract task changes from git diff."""
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
            return {"added": [], "completed": [], "todos": []}

        diff_output = result.stdout

        # Parse diff lines
        for line in diff_output.split("\n"):
            # Added unchecked task
            if line.startswith("+") and not line.startswith("+++"):
                match = TASK_UNCHECKED.search(line[1:])
                if match:
                    added.append(match.group(2).strip())

            # Added checked task (completed)
            if line.startswith("+") and not line.startswith("+++"):
                match = TASK_CHECKED.search(line[1:])
                if match:
                    completed.append(match.group(2).strip())

    except Exception as e:
        print(f"Error reading git diff: {e}", file=sys.stderr)

    return {"added": added, "completed": completed, "todos": []}


def append_to_tasks_file(tasks: dict, source: str):
    """Append extracted tasks to tasks.md."""
    if not any(tasks.values()):
        print("No tasks to add")
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

    # Append to tasks file
    TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(TASKS_FILE, "a", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"Added {len(tasks['added'])} new tasks, {len(tasks['completed'])} completed, {len(tasks['todos'])} TODOs")


def main():
    parser = argparse.ArgumentParser(description="Extract tasks from markdown files")
    parser.add_argument("--file", "-f", type=Path, help="Extract from specific file")
    parser.add_argument("--session", "-s", type=str, help="Extract from session log")
    parser.add_argument("--git-diff", "-g", action="store_true", help="Extract from git diff")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Don't write to tasks.md")

    args = parser.parse_args()

    if args.file:
        tasks = extract_tasks_from_file(args.file)
        source = args.file.name
    elif args.session:
        tasks = extract_tasks_from_session(args.session)
        source = f"session-{args.session}"
    elif args.git_diff:
        tasks = extract_tasks_from_git_diff()
        source = "git-diff"
    else:
        parser.print_help()
        sys.exit(1)

    if args.dry_run:
        print(f"Tasks from {source}:")
        print(f"  Added: {tasks['added']}")
        print(f"  Completed: {tasks['completed']}")
        print(f"  TODOs: {tasks['todos']}")
    else:
        append_to_tasks_file(tasks, source)


if __name__ == "__main__":
    main()
