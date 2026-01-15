#!/usr/bin/env python3
"""
Configuration loader for Task Picker Agent.

Loads configuration from config.yaml with defaults fallback.
"""

import re
import sys
from pathlib import Path
from typing import Any

# Try to import yaml, fall back to basic parsing if not available
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# Default configuration
DEFAULT_CONFIG = {
    "workspace": "~/workspace/obsidian_vault",
    "output": "docs/01_resource/tasks.md",
    "sessions_dir": "docs/01_resource/sessions",
    "patterns": {
        "unchecked": r"^(\s*)-\s*\[\s*\]\s*(.+)$",
        "checked": r"^(\s*)-\s*\[x\]\s*(.+)$",
        "todo": r"(?:TODO|FIXME|XXX):\s*(.+)$",
    },
    "exclude": [
        "docs/01_resource/sessions/",
        "docs/01_resource/tasks.md",
        ".git/",
        "node_modules/",
        ".obsidian/",
    ],
    "dedup": {
        "enabled": True,
        "case_insensitive": True,
    },
    "logging": {
        "level": "INFO",
        "file": None,
    },
    "llm": {
        "enabled": False,
        "model": "claude-sonnet-4-20250514",
        "api_key": None,
        "min_confidence": "low",
        "analyze_on_save": False,
    },
}


class Config:
    """Configuration manager for Task Picker Agent."""

    def __init__(self, config_path: Path | None = None):
        """Initialize configuration from file or defaults."""
        import copy
        self._config = copy.deepcopy(DEFAULT_CONFIG)

        if config_path is None:
            config_path = Path(__file__).parent / "config.yaml"

        if config_path.exists():
            self._load_from_file(config_path)

        # Resolve paths
        self._workspace = Path(self._config["workspace"]).expanduser()
        self._output = self._workspace / self._config["output"]
        self._sessions_dir = self._workspace / self._config["sessions_dir"]

        # Compile patterns
        self._patterns = {
            "unchecked": re.compile(
                self._config["patterns"]["unchecked"],
                re.MULTILINE
            ),
            "checked": re.compile(
                self._config["patterns"]["checked"],
                re.MULTILINE | re.IGNORECASE
            ),
            "todo": re.compile(
                self._config["patterns"]["todo"],
                re.MULTILINE | re.IGNORECASE
            ),
        }

        # Build exclude patterns
        self._exclude_paths = [
            self._workspace / exc for exc in self._config["exclude"]
        ]

    def _load_from_file(self, config_path: Path):
        """Load configuration from YAML file."""
        if not HAS_YAML:
            print(
                "Warning: PyYAML not installed. Using default configuration.",
                file=sys.stderr
            )
            print("Install with: pip install pyyaml", file=sys.stderr)
            return

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_config = yaml.safe_load(f)

            if user_config:
                self._merge_config(self._config, user_config)
        except Exception as e:
            print(f"Warning: Could not load config: {e}", file=sys.stderr)

    def _merge_config(self, base: dict, override: dict):
        """Recursively merge override into base config."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    @property
    def workspace(self) -> Path:
        """Get workspace directory."""
        return self._workspace

    @property
    def output_file(self) -> Path:
        """Get output tasks file path."""
        return self._output

    @property
    def sessions_dir(self) -> Path:
        """Get sessions directory."""
        return self._sessions_dir

    @property
    def patterns(self) -> dict[str, re.Pattern]:
        """Get compiled regex patterns."""
        return self._patterns

    @property
    def exclude_paths(self) -> list[Path]:
        """Get list of paths to exclude from watching."""
        return self._exclude_paths

    @property
    def dedup_enabled(self) -> bool:
        """Check if duplicate detection is enabled."""
        return self._config["dedup"]["enabled"]

    @property
    def dedup_case_insensitive(self) -> bool:
        """Check if case-insensitive comparison is enabled."""
        return self._config["dedup"]["case_insensitive"]

    @property
    def log_level(self) -> str:
        """Get logging level."""
        return self._config["logging"]["level"]

    @property
    def log_file(self) -> Path | None:
        """Get log file path if specified."""
        log_file = self._config["logging"]["file"]
        return Path(log_file).expanduser() if log_file else None

    @property
    def llm_enabled(self) -> bool:
        """Check if LLM analysis is enabled by default."""
        return self._config["llm"]["enabled"]

    @property
    def llm_model(self) -> str:
        """Get the LLM model to use."""
        return self._config["llm"]["model"]

    @property
    def llm_api_key(self) -> str | None:
        """Get the LLM API key if configured."""
        return self._config["llm"]["api_key"]

    @property
    def llm_min_confidence(self) -> str:
        """Get minimum confidence level for implicit tasks."""
        return self._config["llm"]["min_confidence"]

    @property
    def llm_analyze_on_save(self) -> bool:
        """Check if LLM analysis should run on every file save."""
        return self._config["llm"]["analyze_on_save"]

    def is_excluded(self, file_path: Path) -> bool:
        """Check if a file path should be excluded."""
        try:
            file_path = file_path.resolve()
            for exclude in self._exclude_paths:
                exclude = exclude.resolve()
                if file_path == exclude or exclude in file_path.parents:
                    return True
                # Also check if path starts with exclude path string
                if str(file_path).startswith(str(exclude)):
                    return True
        except Exception:
            pass
        return False

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key."""
        return self._config.get(key, default)


# Global config instance (lazy loaded)
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reload_config(config_path: Path | None = None) -> Config:
    """Reload configuration from file."""
    global _config
    _config = Config(config_path)
    return _config
