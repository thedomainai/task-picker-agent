#!/bin/bash
# =============================================================================
# Task Picker Agent - Document Watcher
# =============================================================================
# Watch for .md file saves and extract tasks automatically
#
# Requirements:
#   brew install fswatch
#
# Usage:
#   ./watch_docs.sh [watch_directory]
#
# Examples:
#   ./watch_docs.sh                    # Watch current directory
#   ./watch_docs.sh ~/notes            # Watch specific directory
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WATCH_DIR="${1:-.}"  # Default to current directory
TASK_EXTRACTOR="$SCRIPT_DIR/task_extractor.py"

# Output file (must match config.yaml)
TASKS_FILE="$WATCH_DIR/tasks.md"

# Exclude patterns (sessions dir is handled separately by session hooks)
# Also exclude tasks.md to prevent infinite loop
EXCLUDE_PATTERN="sessions|\.git|node_modules|\.obsidian|tasks\.md"

echo "🔍 Task Picker Agent - Watching for .md file saves"
echo "   Directory: $WATCH_DIR"
echo "   Press Ctrl+C to stop"
echo ""

# Check if fswatch is installed
if ! command -v fswatch &> /dev/null; then
    echo "Error: fswatch is not installed"
    echo "Install with: brew install fswatch"
    exit 1
fi

# Watch for file modifications
fswatch -0 \
    --event Updated \
    --include '\.md$' \
    --exclude "$EXCLUDE_PATTERN" \
    "$WATCH_DIR" | while read -d "" file; do

    # Skip if file doesn't exist (might have been deleted)
    if [[ ! -f "$file" ]]; then
        continue
    fi

    # Skip session files (handled by session hooks)
    if [[ "$file" == *"/sessions/"* ]]; then
        continue
    fi

    # Skip the output tasks file to prevent infinite loop
    if [[ "$file" == "$TASKS_FILE" ]]; then
        continue
    fi

    # Skip .obsidian directory
    if [[ "$file" == *"/.obsidian/"* ]]; then
        continue
    fi

    echo "📄 File saved: $(basename "$file")"

    # Extract tasks from the saved file
    python3 "$TASK_EXTRACTOR" --file "$file"
done
