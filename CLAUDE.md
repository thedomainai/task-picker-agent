# GitHub Automator - Claude Code Project Memory

## Project Overview

This repository provides an automated GitHub Issue-driven development workflow with Claude Code.
All GitHub content (Issues, commits, PRs) must be written in **native English**.

---

## IMPORTANT: Automatic Workflow (Full-Auto Mode)

**Claude Code MUST automatically execute the following workflow without waiting for user commands.**

### When User Requests a New Feature/Task:

1. **IMMEDIATELY create a GitHub Issue** using `gh issue create`
   - Title and body in native English
   - Apply appropriate labels

2. **Create a feature branch** linked to the Issue
   - Format: `<type>/<issue-number>-<short-description>`

3. **Save task state** to `.claude/current-task.json`

4. **Implement the feature**

5. **Commit changes** with Conventional Commits format
   - Always reference Issue number: `(#<issue>)`

6. **When implementation is complete**, automatically:
   - Push to remote
   - Create Pull Request with `Closes #<issue>`
   - Clean up state file

### Automatic Triggers:

| Situation | Action |
|-----------|--------|
| User says "implement X" / "add X" / "create X" | → Create Issue + branch, start work |
| Significant code changes made | → Commit with proper message |
| Feature implementation complete | → Push + Create PR |
| User says "done" / "finish" / "complete" | → Finalize PR if not already done |

### Do NOT Wait For:

- `/start-task` command - just start automatically
- `/quick-commit` command - commit when appropriate
- `/finish-task` command - create PR when done

---

## Development Workflow

### Issue-Driven Development (Automated)

```
User: "Add user authentication"
         │
         ▼ [Claude Code automatically]
    1. gh issue create → Issue #1
    2. git checkout -b feat/1-user-auth
    3. Save .claude/current-task.json
         │
         ▼ [Implementation]
    4. Write code
    5. git commit (Conventional Commits)
         │
         ▼ [Completion]
    6. git push
    7. gh pr create (Closes #1)
    8. rm .claude/current-task.json
```

### Branch Naming Convention

```
<type>/<issue-number>-<short-description>
```

**Important**: No `#` symbol in branch names (causes shell issues).

Examples:
- `feat/1-user-authentication`
- `fix/23-login-redirect-bug`
- `docs/45-api-documentation`

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

### Task State Management

The current task state is stored in `.claude/current-task.json`:

```json
{
  "issue_number": 1,
  "issue_title": "Add user authentication",
  "branch": "feat/1-user-authentication",
  "type": "feat",
  "description": "Implement user login and registration",
  "created_at": "2024-01-15T12:00:00Z"
}
```

This file:
- Is created when starting a new task
- Is read for Issue reference during commits/PR
- Is deleted after PR creation
- Should be in `.gitignore`

## Git Rules

### Commit Message Format (Conventional Commits)

```
<type>(<scope>): <description> (#<issue>)

[optional body]

[optional footer]
Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

**Types:**
- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring without functionality changes
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(auth): implement JWT token validation (#12)
fix(api): resolve null pointer in user endpoint (#34)
docs(readme): add installation instructions (#56)
```

### Important Rules

- **All commit messages MUST be in English**
- **Always reference the Issue number** in commits: `(#123)`
- **Never commit directly to main** - always use feature branches
- **PR titles** should match the Issue title
- **PR body** must include `Closes #<issue-number>`

## Manual Commands (Optional)

These commands are available if you prefer manual control:

| Command | Description |
|---------|-------------|
| `/start-task` | Manually create Issue + branch |
| `/quick-commit` | Manually commit changes |
| `/finish-task` | Manually create PR |

## File Structure

```
.github/
├── ISSUE_TEMPLATE/     # Issue templates
└── PULL_REQUEST_TEMPLATE.md
.claude/
├── commands/           # Slash commands
├── rules/              # Additional rules
├── settings.json       # Hooks configuration
└── current-task.json   # Current task state (gitignored)
```

## Code Style

- Follow existing patterns in the codebase
- Write clear, self-documenting code
- Add comments only when logic is not self-evident
