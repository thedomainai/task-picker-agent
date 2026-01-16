# Task Picker Agent

Extract tasks from your workspace and add them to tasks.md.
Detects added and completed tasks from files modified today.

## Steps

### 1. Current Date
$CURRENT_DATE

### 2. Gather Information

Extract tasks from the following sources:

#### 2.1 Detect Files Modified Today
Find .md files modified today in the workspace:

```bash
# Find .md files modified today
# Replace $WORKSPACE with your workspace path
find "$WORKSPACE" -name "*.md" -mtime -1 -type f 2>/dev/null | head -50
```

#### 2.2 Detect Task Changes from Git Diff
Detect task additions and completions in Git repositories:

```bash
# Detect task changes in each repository
find ~/workspace -name ".git" -type d 2>/dev/null | while read gitdir; do
  repo=$(dirname "$gitdir")
  # Only process repos with commits today
  if git -C "$repo" log --oneline --since="today 00:00" 2>/dev/null | grep -q .; then
    echo "=== $repo ==="
    # Detect task additions (+ - [ ]) and completions (- - [ ] → + - [x])
    git -C "$repo" diff HEAD~3 -- "*.md" 2>/dev/null | grep -E "^[\+\-].*\- \[.\]" | head -20
  fi
done
```

**Detection Patterns:**
- `+ - [ ] task` → Newly added task
- `- - [ ] task` → Deleted or changed to completed
- `+ - [x] task` → Marked as completed

#### 2.3 Extract from Session Logs (Optional)
If using CLI session integration, extract tasks from today's session logs:

```bash
# Check today's session logs
find "$WORKSPACE/sessions" -name "*.md" -mtime -1 -type f 2>/dev/null
```

#### 2.4 Extract TODO/FIXME from Updated Documents
Search for TODO/FIXME in files modified today:

```bash
# Extract TODO/FIXME from files modified today
find "$WORKSPACE" -name "*.md" -mtime -1 -type f -exec grep -l "TODO\|FIXME\|\- \[ \]" {} \; 2>/dev/null
```

### 3. Create Task List

Create a task list from gathered information:

```markdown
## Tasks picked on YYYY-MM-DD

### New Tasks
- [ ] New task 1 (filename)
- [ ] New task 2 (filename)

### Completed Tasks
- [x] Completed task 1 (filename)
- [x] Completed task 2 (filename)

### Session Log Tasks
- [ ] Session task (session-xxxx)

### TODO/FIXME in Documents
- [ ] TODO: description (filename)
```

### 4. Append to tasks.md

After user confirmation, append to:
```
$WORKSPACE/tasks.md
```

### 5. Summary

Display summary of added and completed tasks.
