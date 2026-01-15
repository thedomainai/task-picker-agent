#!/usr/bin/env python3
"""
Pytest configuration and shared fixtures.
"""

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace with standard structure."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    # Create standard directories
    (workspace / "docs" / "01_resource").mkdir(parents=True)
    (workspace / "docs" / "01_resource" / "sessions" / "2026-01").mkdir(parents=True)

    # Create empty tasks.md
    tasks_file = workspace / "docs" / "01_resource" / "tasks.md"
    tasks_file.write_text("# Tasks\n")

    return workspace


@pytest.fixture
def sample_markdown_file(temp_workspace):
    """Create a sample markdown file with tasks."""
    file = temp_workspace / "sample.md"
    file.write_text("""# Sample Document

## Tasks
- [ ] Unchecked task 1
- [ ] Unchecked task 2
- [x] Completed task 1
- [X] Completed task 2

## Notes
Some regular text here.

TODO: This is a todo item
FIXME: This needs fixing
""")
    return file


@pytest.fixture
def sample_session_file(temp_workspace):
    """Create a sample session log file."""
    session_dir = temp_workspace / "docs" / "01_resource" / "sessions" / "2026-01"
    file = session_dir / "session-abc123.md"
    file.write_text("""---
id: abc123
title: Test Session
status: completed
created_at: 2026-01-15T10:00:00
---

## Conversation Log

**User**: Can you help me with a task?

**AI**: Sure, here's what we need to do:
- [ ] First task
- [ ] Second task

TODO: Follow up on this

**User**: Thanks!

**AI**: You're welcome. The first task is now done.
- [x] First task
""")
    return file


@pytest.fixture
def config_file(temp_workspace):
    """Create a test configuration file."""
    config = temp_workspace / "config.yaml"
    config.write_text(f"""
workspace: {temp_workspace}
output: docs/01_resource/tasks.md
sessions_dir: docs/01_resource/sessions
exclude:
  - docs/01_resource/sessions/
  - docs/01_resource/tasks.md
  - .git/
dedup:
  enabled: true
  case_insensitive: true
""")
    return config
