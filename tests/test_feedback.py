#!/usr/bin/env python3
"""
Tests for feedback module.

Run with: pytest tests/test_feedback.py -v
"""

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from feedback import FeedbackStore, FeedbackEntry, format_examples_for_prompt


class TestFeedbackStore:
    """Tests for FeedbackStore class."""

    @pytest.fixture
    def store(self, tmp_path):
        """Create a temporary feedback store."""
        db_path = tmp_path / "test_feedback.db"
        return FeedbackStore(db_path)

    def test_add_feedback_accepted(self, store):
        """Test adding accepted feedback."""
        entry_id = store.add_feedback(
            task_text="Review the documentation",
            feedback="accepted",
            source_text="The docs need review",
            source_file="test.md",
            confidence="high",
        )

        assert entry_id > 0

        examples = store.get_examples("accepted")
        assert len(examples) == 1
        assert examples[0]["task_text"] == "Review the documentation"
        assert examples[0]["feedback"] == "accepted"

    def test_add_feedback_rejected(self, store):
        """Test adding rejected feedback with reason."""
        store.add_feedback(
            task_text="This is not a task",
            feedback="rejected",
            reason="Just informational text",
            confidence="low",
        )

        examples = store.get_examples("rejected")
        assert len(examples) == 1
        assert examples[0]["reason"] == "Just informational text"

    def test_add_feedback_modified(self, store):
        """Test adding modified feedback."""
        store.add_feedback(
            task_text="Original task text",
            feedback="modified",
            modified_text="Better task text",
            confidence="medium",
        )

        examples = store.get_examples("modified")
        assert len(examples) == 1
        assert examples[0]["modified_text"] == "Better task text"

    def test_get_stats_empty(self, store):
        """Test stats with no feedback."""
        stats = store.get_stats()

        assert stats["total"] == 0
        assert stats["accepted"] == 0
        assert stats["rejected"] == 0
        assert stats["modified"] == 0
        assert stats["acceptance_rate"] == 0.0

    def test_get_stats_with_data(self, store):
        """Test stats with feedback data."""
        # Add 3 accepted, 1 rejected, 1 modified
        for _ in range(3):
            store.add_feedback("Task", "accepted")
        store.add_feedback("Task", "rejected")
        store.add_feedback("Task", "modified")

        stats = store.get_stats()

        assert stats["total"] == 5
        assert stats["accepted"] == 3
        assert stats["rejected"] == 1
        assert stats["modified"] == 1
        assert stats["acceptance_rate"] == 0.6  # 3/5

    def test_get_balanced_examples(self, store):
        """Test getting balanced examples of each type."""
        # Add varying amounts of each type
        for i in range(5):
            store.add_feedback(f"Accepted {i}", "accepted")
        for i in range(3):
            store.add_feedback(f"Rejected {i}", "rejected")
        store.add_feedback("Modified", "modified")

        examples = store.get_balanced_examples(count_per_type=2)

        assert len(examples["accepted"]) == 2
        assert len(examples["rejected"]) == 2
        assert len(examples["modified"]) == 1  # Only 1 available

    def test_search_similar(self, store):
        """Test searching for similar patterns."""
        store.add_feedback("Review documentation", "accepted")
        store.add_feedback("Update tests", "accepted")
        store.add_feedback("Review code", "rejected")

        results = store.search_similar("Review")

        assert len(results) == 2
        assert all("Review" in r["task_text"] for r in results)

    def test_get_rejection_patterns(self, store):
        """Test getting common rejection reasons."""
        store.add_feedback("Task 1", "rejected", reason="Not a task")
        store.add_feedback("Task 2", "rejected", reason="Not a task")
        store.add_feedback("Task 3", "rejected", reason="Already done")

        patterns = store.get_rejection_patterns()

        assert len(patterns) == 2
        assert patterns[0][0] == "Not a task"
        assert patterns[0][1] == 2

    def test_clear_all(self, store):
        """Test clearing all feedback."""
        store.add_feedback("Task", "accepted")
        store.add_feedback("Task", "rejected")

        assert store.get_stats()["total"] == 2

        store.clear_all()

        assert store.get_stats()["total"] == 0

    def test_examples_ordered_by_date(self, store):
        """Test that examples are returned in chronological order."""
        store.add_feedback("First", "accepted")
        store.add_feedback("Second", "accepted")
        store.add_feedback("Third", "accepted")

        examples = store.get_examples("accepted", limit=3)

        # Should be most recent first
        assert examples[0]["task_text"] == "Third"
        assert examples[2]["task_text"] == "First"

    def test_limit_respected(self, store):
        """Test that limit parameter is respected."""
        for i in range(10):
            store.add_feedback(f"Task {i}", "accepted")

        examples = store.get_examples("accepted", limit=3)

        assert len(examples) == 3


class TestFormatExamplesForPrompt:
    """Tests for format_examples_for_prompt function."""

    def test_format_empty_examples(self):
        """Test formatting with no examples."""
        examples = {
            "accepted": [],
            "rejected": [],
            "modified": [],
        }

        result = format_examples_for_prompt(examples)

        assert result == ""

    def test_format_accepted_examples(self):
        """Test formatting accepted examples."""
        examples = {
            "accepted": [
                FeedbackEntry(
                    id=1,
                    task_text="Review docs",
                    source_text="The docs need review",
                    source_file="test.md",
                    feedback="accepted",
                    modified_text=None,
                    reason=None,
                    confidence="high",
                    created_at="2026-01-15",
                    tags=[],
                )
            ],
            "rejected": [],
            "modified": [],
        }

        result = format_examples_for_prompt(examples)

        assert "GOOD task detections" in result
        assert "Review docs" in result
        assert "high" in result

    def test_format_rejected_examples(self):
        """Test formatting rejected examples."""
        examples = {
            "accepted": [],
            "rejected": [
                FeedbackEntry(
                    id=1,
                    task_text="Not a task",
                    source_text="Some text",
                    source_file="test.md",
                    feedback="rejected",
                    modified_text=None,
                    reason="Just informational",
                    confidence="low",
                    created_at="2026-01-15",
                    tags=[],
                )
            ],
            "modified": [],
        }

        result = format_examples_for_prompt(examples)

        assert "FALSE POSITIVES" in result
        assert "Just informational" in result

    def test_format_modified_examples(self):
        """Test formatting modified examples."""
        examples = {
            "accepted": [],
            "rejected": [],
            "modified": [
                FeedbackEntry(
                    id=1,
                    task_text="Original",
                    source_text="",
                    source_file="",
                    feedback="modified",
                    modified_text="Better version",
                    reason=None,
                    confidence="medium",
                    created_at="2026-01-15",
                    tags=[],
                )
            ],
        }

        result = format_examples_for_prompt(examples)

        assert "MODIFIED tasks" in result
        assert "Original" in result
        assert "Better version" in result


class TestFeedbackEntry:
    """Tests for FeedbackEntry type."""

    def test_create_entry(self):
        entry = FeedbackEntry(
            id=1,
            task_text="Test task",
            source_text="Source",
            source_file="file.md",
            feedback="accepted",
            modified_text=None,
            reason=None,
            confidence="high",
            created_at="2026-01-15",
            tags=["tag1"],
        )

        assert entry["id"] == 1
        assert entry["task_text"] == "Test task"
        assert entry["tags"] == ["tag1"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
