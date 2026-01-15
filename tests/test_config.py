#!/usr/bin/env python3
"""
Tests for config module.

Run with: pytest tests/test_config.py -v
"""

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config, DEFAULT_CONFIG


class TestConfig:
    """Tests for Config class."""

    def test_default_config_values(self):
        """Test that default config is loaded when no file exists."""
        with TemporaryDirectory() as tmpdir:
            nonexistent = Path(tmpdir) / "nonexistent.yaml"
            config = Config(nonexistent)

            assert config.workspace == Path(DEFAULT_CONFIG["workspace"]).expanduser()
            assert config.dedup_enabled == DEFAULT_CONFIG["dedup"]["enabled"]
            assert config.log_level == DEFAULT_CONFIG["logging"]["level"]

    def test_patterns_are_compiled(self):
        """Test that regex patterns are compiled."""
        with TemporaryDirectory() as tmpdir:
            config = Config(Path(tmpdir) / "nonexistent.yaml")

            assert hasattr(config.patterns["unchecked"], "match")
            assert hasattr(config.patterns["checked"], "match")
            assert hasattr(config.patterns["todo"], "match")

    def test_unchecked_pattern_matches(self):
        """Test unchecked task pattern matching."""
        with TemporaryDirectory() as tmpdir:
            config = Config(Path(tmpdir) / "nonexistent.yaml")
            pattern = config.patterns["unchecked"]

            match = pattern.search("- [ ] Task text")
            assert match is not None
            assert match.group(2) == "Task text"

            # Indented
            match = pattern.search("  - [ ] Indented task")
            assert match is not None
            assert match.group(2) == "Indented task"

    def test_checked_pattern_matches(self):
        """Test checked task pattern matching."""
        with TemporaryDirectory() as tmpdir:
            config = Config(Path(tmpdir) / "nonexistent.yaml")
            pattern = config.patterns["checked"]

            # Lowercase x
            match = pattern.search("- [x] Done task")
            assert match is not None
            assert match.group(2) == "Done task"

            # Uppercase X
            match = pattern.search("- [X] Also done")
            assert match is not None
            assert match.group(2) == "Also done"

    def test_todo_pattern_matches(self):
        """Test TODO pattern matching."""
        with TemporaryDirectory() as tmpdir:
            config = Config(Path(tmpdir) / "nonexistent.yaml")
            pattern = config.patterns["todo"]

            for keyword in ["TODO:", "FIXME:", "XXX:"]:
                match = pattern.search(f"{keyword} Fix this bug")
                assert match is not None
                assert match.group(1) == "Fix this bug"

    def test_is_excluded_matches_file(self, tmp_path):
        """Test is_excluded for exact file match."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(f"""
workspace: {tmp_path}
exclude:
  - excluded.md
""")
        config = Config(config_file)

        excluded_file = tmp_path / "excluded.md"
        excluded_file.touch()

        assert config.is_excluded(excluded_file)

    def test_is_excluded_matches_directory(self, tmp_path):
        """Test is_excluded for directory contents."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(f"""
workspace: {tmp_path}
exclude:
  - excluded_dir/
""")
        config = Config(config_file)

        excluded_dir = tmp_path / "excluded_dir"
        excluded_dir.mkdir()
        excluded_file = excluded_dir / "file.md"
        excluded_file.touch()

        assert config.is_excluded(excluded_file)

    def test_is_excluded_allows_non_excluded(self, tmp_path):
        """Test is_excluded returns False for non-excluded files."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(f"""
workspace: {tmp_path}
exclude:
  - excluded.md
""")
        config = Config(config_file)

        allowed_file = tmp_path / "allowed.md"
        allowed_file.touch()

        assert not config.is_excluded(allowed_file)

    def test_load_custom_config(self, tmp_path):
        """Test loading custom configuration."""
        config_file = tmp_path / "custom.yaml"
        config_file.write_text(f"""
workspace: {tmp_path}
output: custom_tasks.md
dedup:
  enabled: false
  case_insensitive: false
logging:
  level: DEBUG
""")
        config = Config(config_file)

        assert config.workspace == tmp_path
        assert config.output_file == tmp_path / "custom_tasks.md"
        assert config.dedup_enabled is False
        assert config.dedup_case_insensitive is False
        assert config.log_level == "DEBUG"

    def test_merge_partial_config(self, tmp_path):
        """Test that partial config merges with defaults."""
        config_file = tmp_path / "partial.yaml"
        config_file.write_text("""
dedup:
  enabled: false
""")
        config = Config(config_file)

        # Custom value
        assert config.dedup_enabled is False
        # Default value preserved
        assert config.dedup_case_insensitive is True

    def test_get_method(self, tmp_path):
        """Test get method for raw config access."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("")
        config = Config(config_file)

        assert config.get("workspace") == DEFAULT_CONFIG["workspace"]
        assert config.get("nonexistent", "default") == "default"


class TestConfigPatterns:
    """Test pattern matching edge cases."""

    @pytest.fixture
    def config(self, tmp_path):
        return Config(tmp_path / "nonexistent.yaml")

    def test_unchecked_no_match_for_checked(self, config):
        """Unchecked pattern should not match checked tasks."""
        pattern = config.patterns["unchecked"]
        assert pattern.search("- [x] Done") is None

    def test_checked_no_match_for_unchecked(self, config):
        """Checked pattern should not match unchecked tasks."""
        pattern = config.patterns["checked"]
        assert pattern.search("- [ ] Not done") is None

    def test_patterns_match_multiline(self, config):
        """Test patterns work with multiline content."""
        content = """
# Tasks
- [ ] Task 1
- [x] Task 2
- [ ] Task 3
"""
        unchecked = config.patterns["unchecked"].findall(content)
        checked = config.patterns["checked"].findall(content)

        assert len(unchecked) == 2
        assert len(checked) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
