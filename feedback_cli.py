#!/usr/bin/env python3
"""
Interactive Feedback CLI - Review and provide feedback on detected tasks.

This tool allows users to interactively review tasks detected by the LLM
and provide feedback (accept/reject/modify) which improves future detections.

Usage:
    # Analyze a file and interactively review tasks
    python feedback_cli.py review document.md

    # Show feedback statistics
    python feedback_cli.py stats

    # Export feedback examples
    python feedback_cli.py export
"""

import argparse
import sys
from pathlib import Path

from feedback import FeedbackStore, get_store


def report_missed_task(file_path: Path | None, store: FeedbackStore):
    """
    Report a task that should have been detected but wasn't.

    Args:
        file_path: Optional file where the task should have been detected.
        store: Feedback store instance.
    """
    print("\n📝 Report Missed Task")
    print("=" * 50)
    print("Enter details about a task that should have been detected.\n")

    task_text = input("Task text (what should have been detected): ").strip()
    if not task_text:
        print("Cancelled - no task text provided.")
        return

    source_text = input("Source text (the text that should have triggered detection): ").strip()
    reason = input("Why should this be a task? (optional): ").strip()

    file_str = ""
    if file_path:
        file_str = str(file_path)
    else:
        file_str = input("File path (optional): ").strip()

    store.add_feedback(
        task_text=task_text,
        feedback="missed",
        source_text=source_text,
        source_file=file_str,
        reason=reason if reason else None,
        confidence="user",  # User-reported
    )

    print(f"\n✓ Recorded missed task: {task_text}")
    print("This will help improve future detection!")


def detect_user_added_tasks(file_path: Path, store: FeedbackStore):
    """
    Detect tasks the user added manually that weren't detected by LLM.

    Compares LLM detection results with actual tasks in the file.

    Args:
        file_path: Path to analyze.
        store: Feedback store instance.
    """
    if not file_path.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        return

    try:
        from llm_analyzer import LLMAnalyzer
        from task_extractor import extract_tasks_from_file
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        return

    print(f"\n🔍 Comparing detected vs actual tasks in: {file_path.name}")
    print("=" * 50)

    # Get LLM detected tasks
    try:
        content = file_path.read_text(encoding="utf-8")
        analyzer = LLMAnalyzer(use_feedback=True)
        llm_result = analyzer.analyze_document(content, file_path.name)
        llm_tasks = {t["task"].lower().strip() for t in llm_result["implicit_tasks"]}
    except Exception as e:
        print(f"LLM analysis failed: {e}")
        llm_tasks = set()

    # Get explicit tasks from file (pattern-based)
    pattern_result = extract_tasks_from_file(file_path)
    explicit_tasks = pattern_result["added"] + pattern_result["todos"]

    # Find tasks that exist in file but weren't detected by LLM
    potentially_missed = []
    for task in explicit_tasks:
        task_lower = task.lower().strip()
        # Check if this task (or similar) was detected
        detected = any(
            task_lower in llm_task or llm_task in task_lower
            for llm_task in llm_tasks
        )
        if not detected:
            potentially_missed.append(task)

    if not potentially_missed:
        print("\n✨ No potentially missed tasks found!")
        print("LLM detection appears to be working well for this file.")
        return

    print(f"\n⚠️  Found {len(potentially_missed)} tasks in file that LLM didn't detect:")
    print("(These might be tasks that should have been detected as implicit)")
    print()

    for i, task in enumerate(potentially_missed, 1):
        print(f"[{i}] {task}")

    print("\nWould you like to report any of these as missed detections?")
    print("Enter numbers separated by comma (e.g., 1,3), 'all', or 'none':")

    choice = input("> ").strip().lower()

    if choice == "none" or not choice:
        print("No tasks reported.")
        return

    if choice == "all":
        indices = list(range(len(potentially_missed)))
    else:
        try:
            indices = [int(x.strip()) - 1 for x in choice.split(",")]
        except ValueError:
            print("Invalid input.")
            return

    for idx in indices:
        if 0 <= idx < len(potentially_missed):
            task = potentially_missed[idx]
            store.add_feedback(
                task_text=task,
                feedback="missed",
                source_file=str(file_path),
                confidence="user",
                reason="User confirmed this should have been detected",
            )
            print(f"✓ Reported: {task}")

    print(f"\nRecorded {len(indices)} missed task(s). Thank you!")


def review_tasks(file_path: Path, store: FeedbackStore):
    """
    Analyze a file and interactively review detected tasks.

    Args:
        file_path: Path to the file to analyze.
        store: Feedback store instance.
    """
    if not file_path.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        return

    # Import here to avoid circular imports
    try:
        from llm_analyzer import LLMAnalyzer
    except ImportError:
        print("Error: LLM analyzer not available", file=sys.stderr)
        return

    print(f"\n📄 Analyzing: {file_path.name}")
    print("=" * 50)

    try:
        content = file_path.read_text(encoding="utf-8")
        analyzer = LLMAnalyzer(use_feedback=True)
        result = analyzer.analyze_document(content, file_path.name)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return
    except Exception as e:
        print(f"Analysis failed: {e}", file=sys.stderr)
        return

    implicit_tasks = result["implicit_tasks"]
    incomplete_sections = result["incomplete_sections"]
    unanswered_questions = result["unanswered_questions"]

    if not implicit_tasks and not incomplete_sections and not unanswered_questions:
        print("\n✨ No implicit tasks or issues detected!")
        # Ask about missed tasks
        print("\nWere there any tasks that should have been detected?")
        if input("Report missed tasks? [y/N]: ").strip().lower() == 'y':
            detect_user_added_tasks(file_path, store)
        return

    print(f"\n🔍 Found {len(implicit_tasks)} implicit tasks")
    print(f"📝 Found {len(incomplete_sections)} incomplete sections")
    print(f"❓ Found {len(unanswered_questions)} unanswered questions")

    # Review implicit tasks
    if implicit_tasks:
        print("\n" + "=" * 50)
        print("IMPLICIT TASKS - Please review each one:")
        print("=" * 50)

        for i, task in enumerate(implicit_tasks, 1):
            print(f"\n[{i}/{len(implicit_tasks)}] Task: {task['task']}")
            print(f"    Confidence: {task['confidence']}")
            print(f"    Reason: {task['reason']}")
            if task['source_text']:
                preview = task['source_text'][:80].replace('\n', ' ')
                print(f"    Source: \"{preview}...\"")

            # Get user feedback
            while True:
                print("\n    Options:")
                print("      [a] Accept - This is a valid task")
                print("      [r] Reject - This is not a task")
                print("      [m] Modify - Accept with changes")
                print("      [s] Skip - Don't record feedback")
                print("      [q] Quit - Stop reviewing")

                choice = input("    Your choice: ").strip().lower()

                if choice == 'a':
                    store.add_feedback(
                        task_text=task['task'],
                        feedback="accepted",
                        source_text=task.get('source_text', ''),
                        source_file=str(file_path),
                        confidence=task['confidence'],
                    )
                    print("    ✓ Marked as accepted")
                    break

                elif choice == 'r':
                    reason = input("    Reason for rejection (optional): ").strip()
                    store.add_feedback(
                        task_text=task['task'],
                        feedback="rejected",
                        source_text=task.get('source_text', ''),
                        source_file=str(file_path),
                        reason=reason if reason else None,
                        confidence=task['confidence'],
                    )
                    print("    ✗ Marked as rejected")
                    break

                elif choice == 'm':
                    modified = input("    Enter modified task text: ").strip()
                    if modified:
                        store.add_feedback(
                            task_text=task['task'],
                            feedback="modified",
                            source_text=task.get('source_text', ''),
                            source_file=str(file_path),
                            modified_text=modified,
                            confidence=task['confidence'],
                        )
                        print(f"    ~ Modified to: {modified}")
                    else:
                        print("    (No modification entered, skipping)")
                    break

                elif choice == 's':
                    print("    - Skipped")
                    break

                elif choice == 'q':
                    print("\nReview stopped.")
                    return

                else:
                    print("    Invalid choice, please try again.")

    # Ask about missed tasks
    print("\n" + "-" * 50)
    print("Were there any tasks that should have been detected but weren't?")
    if input("Check for missed tasks? [y/N]: ").strip().lower() == 'y':
        detect_user_added_tasks(file_path, store)

    # Summary
    print("\n" + "=" * 50)
    stats = store.get_stats()
    print(f"📊 Total feedback recorded: {stats['total']}")
    print(f"   Acceptance rate: {stats['acceptance_rate']:.1%}")
    if stats['missed'] > 0:
        print(f"   Missed tasks reported: {stats['missed']}")
    print("\nThank you for your feedback! This helps improve future detections.")


def show_stats(store: FeedbackStore):
    """Show feedback statistics."""
    stats = store.get_stats()

    print("\n📊 Feedback Statistics")
    print("=" * 30)
    print(f"Total entries: {stats['total']}")
    print(f"  ✓ Accepted:  {stats['accepted']}")
    print(f"  ✗ Rejected:  {stats['rejected']}")
    print(f"  ~ Modified:  {stats['modified']}")
    print(f"  ⚠ Missed:    {stats['missed']}")
    print(f"\nAcceptance rate: {stats['acceptance_rate']:.1%}")

    if stats['missed'] > 0:
        recall_ratio = stats['missed'] / (stats['accepted'] + stats['missed']) if (stats['accepted'] + stats['missed']) > 0 else 0
        print(f"Missed task ratio: {recall_ratio:.1%}")
        if recall_ratio > 0.2:
            print("⚠️  High missed ratio - LLM may need more aggressive detection")

    if stats['total'] > 0:
        # Show rejection patterns
        patterns = store.get_rejection_patterns(5)
        if patterns:
            print("\n❌ Common rejection reasons:")
            for reason, count in patterns:
                print(f"  - {reason} ({count}x)")

    print()


def export_examples(store: FeedbackStore):
    """Export feedback examples for LLM prompt."""
    from feedback import format_examples_for_prompt

    examples = store.get_balanced_examples(count_per_type=3)
    formatted = format_examples_for_prompt(examples)

    if formatted:
        print(formatted)
    else:
        print("No feedback examples available yet.")
        print("Use 'review' command to provide feedback on detected tasks.")


def list_feedback(store: FeedbackStore, feedback_type: str | None, limit: int):
    """List feedback entries."""
    examples = store.get_examples(feedback_type, limit)

    if not examples:
        print("No feedback entries found.")
        return

    print(f"\n📋 Feedback Entries ({len(examples)})")
    print("=" * 50)

    for ex in examples:
        icon = {"accepted": "✓", "rejected": "✗", "modified": "~", "missed": "⚠"}[ex["feedback"]]
        conf = {"high": "🔴", "medium": "🟡", "low": "🟢", "user": "👤"}.get(ex["confidence"], "⚪")

        print(f"\n{icon} {conf} {ex['task_text'][:60]}...")
        print(f"   File: {ex['source_file']}")
        print(f"   Date: {ex['created_at'][:10]}")
        if ex["reason"]:
            print(f"   Reason: {ex['reason']}")
        if ex["modified_text"]:
            print(f"   Modified: {ex['modified_text']}")


def main():
    parser = argparse.ArgumentParser(
        description="Interactive feedback for task detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Review tasks in a document interactively
  python feedback_cli.py review document.md

  # Report a missed task
  python feedback_cli.py missed

  # Check for missed tasks in a file
  python feedback_cli.py check document.md

  # Show feedback statistics
  python feedback_cli.py stats

  # List recent feedback
  python feedback_cli.py list --limit 20

  # Export examples for LLM prompt
  python feedback_cli.py export
""",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Review command
    review_parser = subparsers.add_parser(
        "review", help="Analyze a file and review tasks interactively"
    )
    review_parser.add_argument("file", type=Path, help="File to analyze")

    # Missed command - report a missed task manually
    missed_parser = subparsers.add_parser(
        "missed", help="Report a task that should have been detected"
    )
    missed_parser.add_argument(
        "--file", "-f", type=Path, help="File where task should have been detected"
    )

    # Check command - detect user-added tasks
    check_parser = subparsers.add_parser(
        "check", help="Check for tasks in file that weren't detected"
    )
    check_parser.add_argument("file", type=Path, help="File to check")

    # Stats command
    subparsers.add_parser("stats", help="Show feedback statistics")

    # List command
    list_parser = subparsers.add_parser("list", help="List feedback entries")
    list_parser.add_argument(
        "--type", "-t",
        choices=["accepted", "rejected", "modified", "missed"],
        help="Filter by feedback type",
    )
    list_parser.add_argument(
        "--limit", "-n",
        type=int,
        default=10,
        help="Maximum entries to show",
    )

    # Export command
    subparsers.add_parser("export", help="Export examples for LLM prompt")

    args = parser.parse_args()
    store = get_store()

    if args.command == "review":
        review_tasks(args.file, store)
    elif args.command == "missed":
        report_missed_task(args.file, store)
    elif args.command == "check":
        detect_user_added_tasks(args.file, store)
    elif args.command == "stats":
        show_stats(store)
    elif args.command == "list":
        list_feedback(store, args.type, args.limit)
    elif args.command == "export":
        export_examples(store)


if __name__ == "__main__":
    main()
