#!/usr/bin/env python3
"""
Feedback System - Learn from user approvals/rejections of tasks.

This module tracks user feedback on detected tasks to improve future suggestions.
Feedback is stored in SQLite and used as few-shot examples for LLM analysis.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Literal, TypedDict

# Default feedback database location
DEFAULT_DB_PATH = Path.home() / ".config/task-picker-agent/feedback.db"


class FeedbackEntry(TypedDict):
    """A feedback entry for a task."""
    id: int
    task_text: str
    source_text: str
    source_file: str
    feedback: Literal["accepted", "rejected", "modified", "missed"]
    modified_text: str | None  # If user modified the task
    reason: str | None  # Optional reason for rejection
    confidence: str  # Original confidence: high/medium/low (or "user" for missed)
    created_at: str
    tags: list[str]  # User-added tags


class FeedbackStats(TypedDict):
    """Statistics about feedback."""
    total: int
    accepted: int
    rejected: int
    modified: int
    missed: int
    acceptance_rate: float
    recall_issues: int  # missed tasks indicate recall problems


class FeedbackStore:
    """SQLite-based feedback storage."""

    def __init__(self, db_path: Path | None = None):
        """
        Initialize feedback store.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.config/task-picker-agent/feedback.db
        """
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            # Create table if not exists (with missed type)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_text TEXT NOT NULL,
                    source_text TEXT,
                    source_file TEXT,
                    feedback TEXT NOT NULL CHECK (feedback IN ('accepted', 'rejected', 'modified', 'missed')),
                    modified_text TEXT,
                    reason TEXT,
                    confidence TEXT,
                    created_at TEXT NOT NULL,
                    tags TEXT DEFAULT '[]'
                )
            """)

            # Migration: Add 'missed' to existing tables
            # SQLite doesn't support ALTER CHECK, so we handle this gracefully
            try:
                # Test if missed is allowed
                conn.execute(
                    "INSERT INTO feedback (task_text, feedback, created_at) VALUES (?, ?, ?)",
                    ("__test__", "missed", "2000-01-01")
                )
                conn.execute("DELETE FROM feedback WHERE task_text = '__test__'")
            except sqlite3.IntegrityError:
                # Need to recreate table with new constraint
                conn.execute("ALTER TABLE feedback RENAME TO feedback_old")
                conn.execute("""
                    CREATE TABLE feedback (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task_text TEXT NOT NULL,
                        source_text TEXT,
                        source_file TEXT,
                        feedback TEXT NOT NULL CHECK (feedback IN ('accepted', 'rejected', 'modified', 'missed')),
                        modified_text TEXT,
                        reason TEXT,
                        confidence TEXT,
                        created_at TEXT NOT NULL,
                        tags TEXT DEFAULT '[]'
                    )
                """)
                conn.execute("""
                    INSERT INTO feedback SELECT * FROM feedback_old
                """)
                conn.execute("DROP TABLE feedback_old")

            # Index for common queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedback_type
                ON feedback(feedback)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_source_file
                ON feedback(source_file)
            """)

            conn.commit()

    def add_feedback(
        self,
        task_text: str,
        feedback: Literal["accepted", "rejected", "modified", "missed"],
        source_text: str = "",
        source_file: str = "",
        modified_text: str | None = None,
        reason: str | None = None,
        confidence: str = "medium",
        tags: list[str] | None = None,
    ) -> int:
        """
        Add a feedback entry.

        Args:
            task_text: The original task text.
            feedback: User's feedback (accepted/rejected/modified).
            source_text: Original source text that triggered detection.
            source_file: File where task was detected.
            modified_text: User's modified version (if modified).
            reason: Reason for rejection.
            confidence: Original detection confidence.
            tags: User-added tags.

        Returns:
            ID of the created entry.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO feedback
                (task_text, source_text, source_file, feedback, modified_text, reason, confidence, created_at, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_text,
                    source_text,
                    source_file,
                    feedback,
                    modified_text,
                    reason,
                    confidence,
                    datetime.now().isoformat(),
                    json.dumps(tags or []),
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_examples(
        self,
        feedback_type: Literal["accepted", "rejected", "modified"] | None = None,
        limit: int = 10,
    ) -> list[FeedbackEntry]:
        """
        Get feedback examples for few-shot learning.

        Args:
            feedback_type: Filter by feedback type.
            limit: Maximum number of examples.

        Returns:
            List of feedback entries.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            if feedback_type:
                cursor = conn.execute(
                    """
                    SELECT * FROM feedback
                    WHERE feedback = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (feedback_type, limit),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT * FROM feedback
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                )

            return [self._row_to_entry(row) for row in cursor.fetchall()]

    def get_balanced_examples(self, count_per_type: int = 3) -> dict[str, list[FeedbackEntry]]:
        """
        Get balanced examples of each feedback type.

        Args:
            count_per_type: Number of examples per feedback type.

        Returns:
            Dict with 'accepted', 'rejected', 'modified', 'missed' keys.
        """
        return {
            "accepted": self.get_examples("accepted", count_per_type),
            "rejected": self.get_examples("rejected", count_per_type),
            "modified": self.get_examples("modified", count_per_type),
            "missed": self.get_examples("missed", count_per_type),
        }

    def get_stats(self) -> FeedbackStats:
        """Get feedback statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN feedback = 'accepted' THEN 1 ELSE 0 END) as accepted,
                    SUM(CASE WHEN feedback = 'rejected' THEN 1 ELSE 0 END) as rejected,
                    SUM(CASE WHEN feedback = 'modified' THEN 1 ELSE 0 END) as modified,
                    SUM(CASE WHEN feedback = 'missed' THEN 1 ELSE 0 END) as missed
                FROM feedback
                """
            )
            row = cursor.fetchone()

            total = row[0] or 0
            accepted = row[1] or 0
            rejected = row[2] or 0
            modified = row[3] or 0
            missed = row[4] or 0

            # Acceptance rate based on detected tasks (excluding missed)
            detected_total = accepted + rejected + modified
            acceptance_rate = accepted / detected_total if detected_total > 0 else 0.0

            return FeedbackStats(
                total=total,
                accepted=accepted,
                rejected=rejected,
                modified=modified,
                missed=missed,
                acceptance_rate=acceptance_rate,
                recall_issues=missed,
            )

    def search_similar(self, text: str, limit: int = 5) -> list[FeedbackEntry]:
        """
        Search for similar task patterns in feedback history.

        Simple substring matching. For better results, consider
        using embeddings or fuzzy matching.

        Args:
            text: Text to search for.
            limit: Maximum results.

        Returns:
            List of matching feedback entries.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Simple LIKE search - could be improved with FTS5
            cursor = conn.execute(
                """
                SELECT * FROM feedback
                WHERE task_text LIKE ? OR source_text LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (f"%{text}%", f"%{text}%", limit),
            )

            return [self._row_to_entry(row) for row in cursor.fetchall()]

    def get_rejection_patterns(self, limit: int = 20) -> list[tuple[str, int]]:
        """
        Get common rejection patterns.

        Returns:
            List of (reason, count) tuples.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT reason, COUNT(*) as cnt
                FROM feedback
                WHERE feedback = 'rejected' AND reason IS NOT NULL
                GROUP BY reason
                ORDER BY cnt DESC
                LIMIT ?
                """,
                (limit,),
            )
            return cursor.fetchall()

    def clear_all(self):
        """Clear all feedback data. Use with caution!"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM feedback")
            conn.commit()

    def _row_to_entry(self, row: sqlite3.Row) -> FeedbackEntry:
        """Convert a database row to FeedbackEntry."""
        return FeedbackEntry(
            id=row["id"],
            task_text=row["task_text"],
            source_text=row["source_text"] or "",
            source_file=row["source_file"] or "",
            feedback=row["feedback"],
            modified_text=row["modified_text"],
            reason=row["reason"],
            confidence=row["confidence"] or "medium",
            created_at=row["created_at"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
        )


def format_examples_for_prompt(examples: dict[str, list[FeedbackEntry]]) -> str:
    """
    Format feedback examples for inclusion in LLM prompt.

    Args:
        examples: Dict with accepted/rejected/modified/missed lists.

    Returns:
        Formatted string for prompt.
    """
    lines = []

    if examples.get("accepted"):
        lines.append("## Examples of GOOD task detections (user accepted):")
        for ex in examples["accepted"]:
            lines.append(f"- Source: \"{ex['source_text'][:100]}...\"")
            lines.append(f"  Task: \"{ex['task_text']}\"")
            lines.append(f"  Confidence: {ex['confidence']}")
            lines.append("")

    if examples.get("rejected"):
        lines.append("## Examples of FALSE POSITIVES (user rejected):")
        for ex in examples["rejected"]:
            lines.append(f"- Source: \"{ex['source_text'][:100]}...\"")
            lines.append(f"  Suggested task: \"{ex['task_text']}\"")
            if ex["reason"]:
                lines.append(f"  Reason for rejection: {ex['reason']}")
            lines.append("")

    if examples.get("modified"):
        lines.append("## Examples of MODIFIED tasks (user improved):")
        for ex in examples["modified"]:
            lines.append(f"- Original: \"{ex['task_text']}\"")
            lines.append(f"  User's version: \"{ex['modified_text']}\"")
            lines.append("")

    if examples.get("missed"):
        lines.append("## Examples of MISSED tasks (should have been detected):")
        lines.append("IMPORTANT: These are tasks the user had to add manually because they were not detected.")
        lines.append("Look for similar patterns and make sure to detect them!")
        lines.append("")
        for ex in examples["missed"]:
            lines.append(f"- Missed task: \"{ex['task_text']}\"")
            if ex["source_text"]:
                lines.append(f"  Source text: \"{ex['source_text'][:100]}...\"")
            if ex["reason"]:
                lines.append(f"  Why it should be detected: {ex['reason']}")
            lines.append("")

    return "\n".join(lines)


# Global store instance (lazy loaded)
_store: FeedbackStore | None = None


def get_store(db_path: Path | None = None) -> FeedbackStore:
    """Get the global feedback store instance."""
    global _store
    if _store is None:
        _store = FeedbackStore(db_path)
    return _store


def main():
    """CLI for feedback management."""
    import argparse

    parser = argparse.ArgumentParser(description="Manage task feedback")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Add feedback
    add_parser = subparsers.add_parser("add", help="Add feedback for a task")
    add_parser.add_argument("task", help="Task text")
    add_parser.add_argument(
        "feedback",
        choices=["accepted", "rejected", "modified"],
        help="Feedback type",
    )
    add_parser.add_argument("--source", "-s", help="Source text")
    add_parser.add_argument("--file", "-f", help="Source file")
    add_parser.add_argument("--modified", "-m", help="Modified task text")
    add_parser.add_argument("--reason", "-r", help="Reason for rejection")
    add_parser.add_argument("--confidence", "-c", default="medium", help="Confidence level")

    # Show stats
    subparsers.add_parser("stats", help="Show feedback statistics")

    # List examples
    list_parser = subparsers.add_parser("list", help="List feedback examples")
    list_parser.add_argument("--type", "-t", choices=["accepted", "rejected", "modified"])
    list_parser.add_argument("--limit", "-n", type=int, default=10)

    # Export for prompt
    subparsers.add_parser("export", help="Export examples for LLM prompt")

    args = parser.parse_args()
    store = get_store()

    if args.command == "add":
        entry_id = store.add_feedback(
            task_text=args.task,
            feedback=args.feedback,
            source_text=args.source or "",
            source_file=args.file or "",
            modified_text=args.modified,
            reason=args.reason,
            confidence=args.confidence,
        )
        print(f"Added feedback entry #{entry_id}")

    elif args.command == "stats":
        stats = store.get_stats()
        print(f"Total feedback: {stats['total']}")
        print(f"  Accepted: {stats['accepted']}")
        print(f"  Rejected: {stats['rejected']}")
        print(f"  Modified: {stats['modified']}")
        print(f"  Acceptance rate: {stats['acceptance_rate']:.1%}")

    elif args.command == "list":
        examples = store.get_examples(args.type, args.limit)
        for ex in examples:
            icon = {"accepted": "✓", "rejected": "✗", "modified": "~"}[ex["feedback"]]
            print(f"{icon} [{ex['confidence']}] {ex['task_text'][:60]}...")
            if ex["reason"]:
                print(f"    Reason: {ex['reason']}")

    elif args.command == "export":
        examples = store.get_balanced_examples(3)
        print(format_examples_for_prompt(examples))


if __name__ == "__main__":
    main()
