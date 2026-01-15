#!/usr/bin/env python3
"""
Tests for task_extractor module.

Run with: pytest tests/test_task_extractor.py -v
"""

import sys
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from task_extractor import (
    TaskResult,
    extract_tasks_from_file,
    filter_duplicates,
    normalize_task,
)


class TestNormalizeTask:
    """Tests for normalize_task function."""

    def test_strips_whitespace(self):
        assert normalize_task("  task  ") == "task"

    def test_lowercase_by_default(self):
        assert normalize_task("Task Name") == "task name"

    def test_case_sensitive_option(self):
        assert normalize_task("Task Name", case_insensitive=False) == "Task Name"

    def test_empty_string(self):
        assert normalize_task("") == ""


class TestExtractTasksFromFile:
    """Tests for extract_tasks_from_file function."""

    def test_extract_unchecked_tasks(self, tmp_path):
        file = tmp_path / "test.md"
        file.write_text("- [ ] Task 1\n- [ ] Task 2\n")

        result = extract_tasks_from_file(file)

        assert result["added"] == ["Task 1", "Task 2"]
        assert result["completed"] == []
        assert result["todos"] == []

    def test_extract_checked_tasks(self, tmp_path):
        file = tmp_path / "test.md"
        file.write_text("- [x] Done 1\n- [X] Done 2\n")

        result = extract_tasks_from_file(file)

        assert result["added"] == []
        assert result["completed"] == ["Done 1", "Done 2"]
        assert result["todos"] == []

    def test_extract_todo_comments(self, tmp_path):
        file = tmp_path / "test.md"
        file.write_text("TODO: Fix this\nFIXME: Also this\nXXX: And this\n")

        result = extract_tasks_from_file(file)

        assert result["added"] == []
        assert result["completed"] == []
        assert result["todos"] == ["Fix this", "Also this", "And this"]

    def test_extract_mixed_content(self, tmp_path):
        file = tmp_path / "test.md"
        content = """# My Tasks

## Pending
- [ ] New task

## Done
- [x] Completed task

Some text with TODO: inline todo
"""
        file.write_text(content)

        result = extract_tasks_from_file(file)

        assert "New task" in result["added"]
        assert "Completed task" in result["completed"]
        assert "inline todo" in result["todos"]

    def test_nonexistent_file(self, tmp_path):
        file = tmp_path / "nonexistent.md"

        result = extract_tasks_from_file(file)

        assert result == TaskResult(added=[], completed=[], todos=[])

    def test_empty_file(self, tmp_path):
        file = tmp_path / "empty.md"
        file.write_text("")

        result = extract_tasks_from_file(file)

        assert result == TaskResult(added=[], completed=[], todos=[])

    def test_indented_tasks(self, tmp_path):
        file = tmp_path / "test.md"
        file.write_text("  - [ ] Indented task\n    - [ ] More indented\n")

        result = extract_tasks_from_file(file)

        assert "Indented task" in result["added"]
        assert "More indented" in result["added"]

    def test_tasks_with_special_characters(self, tmp_path):
        file = tmp_path / "test.md"
        file.write_text("- [ ] Task with #tag @mention\n- [ ] Task (with parens)\n")

        result = extract_tasks_from_file(file)

        assert "Task with #tag @mention" in result["added"]
        assert "Task (with parens)" in result["added"]

    def test_japanese_tasks(self, tmp_path):
        file = tmp_path / "test.md"
        file.write_text("- [ ] テストタスク\n- [x] 完了済み\n")

        result = extract_tasks_from_file(file)

        assert "テストタスク" in result["added"]
        assert "完了済み" in result["completed"]


class TestFilterDuplicates:
    """Tests for filter_duplicates function."""

    def test_removes_exact_duplicates(self):
        tasks = TaskResult(added=["Task 1", "Task 2"], completed=[], todos=[])
        existing = {"task 1"}

        result = filter_duplicates(tasks, existing)

        assert result["added"] == ["Task 2"]

    def test_case_insensitive_matching(self):
        tasks = TaskResult(added=["TASK ONE", "task two"], completed=[], todos=[])
        # Existing set should contain normalized (lowercase) values
        existing = {"task one", "task two"}

        result = filter_duplicates(tasks, existing)

        assert result["added"] == []

    def test_preserves_non_duplicates(self):
        tasks = TaskResult(added=["New task"], completed=["Done task"], todos=["Todo"])
        existing = set()

        result = filter_duplicates(tasks, existing)

        assert result == tasks

    def test_filters_all_categories(self):
        tasks = TaskResult(
            added=["Existing", "New"],
            completed=["Done existing", "Done new"],
            todos=["Todo existing", "Todo new"],
        )
        existing = {"existing", "done existing", "todo existing"}

        result = filter_duplicates(tasks, existing)

        assert result["added"] == ["New"]
        assert result["completed"] == ["Done new"]
        assert result["todos"] == ["Todo new"]

    def test_empty_input(self):
        tasks = TaskResult(added=[], completed=[], todos=[])
        existing = {"some task"}

        result = filter_duplicates(tasks, existing)

        assert result == tasks


class TestTaskResultTypedDict:
    """Tests for TaskResult type."""

    def test_create_task_result(self):
        result = TaskResult(added=["a"], completed=["b"], todos=["c"])

        assert result["added"] == ["a"]
        assert result["completed"] == ["b"]
        assert result["todos"] == ["c"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
