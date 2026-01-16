# Task Picker Agent

Automatically extract tasks from markdown files and consolidate them into a single `tasks.md` file.

## Features

- **Real-time extraction** - Automatically detects tasks when .md files are saved
- **Pattern matching** - Extracts `- [ ]`, `- [x]`, `TODO:`, `FIXME:`, `XXX:` patterns
- **Duplicate detection** - Skips tasks that already exist in tasks.md
- **LLM analysis** (optional) - Uses Claude API to detect implicit tasks
- **Feedback learning** - Improves over time based on your corrections

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/thedomainai/task-picker-agent.git
cd task-picker-agent
```

### 2. Create configuration

```bash
cp config.yaml.example config.yaml
```

Edit `config.yaml` to set your workspace path:

```yaml
# Point to your notes/documents directory
workspace: ~/your-notes-directory

# Where to output extracted tasks (relative to workspace)
output: tasks.md
```

### 3. Install dependencies

```bash
# Required
pip install pyyaml

# Optional (for LLM analysis)
pip install anthropic
```

### 4. Install fswatch (for real-time monitoring)

```bash
# macOS
brew install fswatch

# Linux (Ubuntu/Debian)
sudo apt-get install fswatch
```

### 5. Start watching

```bash
./watch_docs.sh ~/your-notes-directory
```

## Configuration

All settings are in `config.yaml`:

| Setting | Description | Default |
|---------|-------------|---------|
| `workspace` | Base directory for operations | `.` (current dir) |
| `output` | Output file path (relative to workspace) | `tasks.md` |
| `inbox_section` | Section header for new tasks | `## Inbox` |
| `sessions_dir` | Session logs directory | `sessions` |
| `exclude` | Paths to ignore | `.git/`, `node_modules/`, etc. |
| `dedup.enabled` | Skip duplicate tasks | `true` |
| `dedup.case_insensitive` | Case-insensitive comparison | `true` |
| `llm.enabled` | Enable LLM analysis by default | `false` |

## Usage

### Automatic (Recommended)

Start the file watcher:

```bash
./watch_docs.sh ~/your-notes-directory
```

Tasks are automatically extracted when you save any `.md` file.

### Manual

```bash
# Extract from a specific file
python task_extractor.py --file /path/to/file.md

# Extract from a session log
python task_extractor.py --session <session_id>

# Extract from git diff
python task_extractor.py --git-diff

# Dry run (preview without writing)
python task_extractor.py --file /path/to/file.md --dry-run

# Use LLM analysis (requires ANTHROPIC_API_KEY)
python task_extractor.py --file /path/to/file.md --llm
```

## Task Format

The agent recognizes these patterns:

| Pattern | Example |
|---------|---------|
| Unchecked task | `- [ ] Do something` |
| Checked task | `- [x] Done item` |
| TODO comment | `TODO: Fix this later` |
| FIXME comment | `FIXME: Bug here` |
| XXX comment | `XXX: Needs review` |

## Output

Tasks are inserted under the `## Inbox` section in your tasks.md:

```markdown
## Inbox
- [ ] New task from document A
- [ ] TODO: Fix authentication
- [x] Completed task

## Archive
```

## LLM Analysis (Optional)

Enable AI-powered implicit task detection:

1. Set your API key:
   ```bash
   export ANTHROPIC_API_KEY=your-key-here
   ```

2. Use the `--llm` flag:
   ```bash
   python task_extractor.py --file /path/to/file.md --llm
   ```

The LLM can detect:
- Incomplete sections that need work
- Unanswered questions
- Implicit tasks mentioned in text

## Feedback Learning

Review and improve LLM suggestions:

```bash
# Interactive review of pending tasks
python feedback_cli.py review

# Report a missed task
python feedback_cli.py missed "Task that should have been detected" source.md

# View statistics
python feedback_cli.py stats
```

## File Structure

```
task-picker-agent/
├── task_extractor.py      # Core extraction logic
├── config.py              # Configuration management
├── config.yaml.example    # Example configuration
├── watch_docs.sh          # File watcher script
├── llm_analyzer.py        # LLM integration (optional)
├── feedback.py            # Feedback storage
├── feedback_cli.py        # Feedback CLI
├── tests/                 # Test suite
└── .claude/
    └── commands/
        └── daily-tasks.md # Claude Code command
```

## Requirements

- Python 3.10+
- fswatch (for file watching)
- PyYAML
- anthropic (optional, for LLM features)

## License

MIT
