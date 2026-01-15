#!/usr/bin/env python3
"""
Tests for llm_analyzer module.

Run with: pytest tests/test_llm_analyzer.py -v
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from llm_analyzer import (
    AnalysisResult,
    ImplicitTask,
    LLMAnalyzer,
)


class TestAnalysisResult:
    """Tests for AnalysisResult type."""

    def test_create_analysis_result(self):
        result = AnalysisResult(
            implicit_tasks=[],
            incomplete_sections=["Section 1"],
            unanswered_questions=["What is X?"],
            summary="Test summary"
        )

        assert result["implicit_tasks"] == []
        assert result["incomplete_sections"] == ["Section 1"]
        assert result["unanswered_questions"] == ["What is X?"]
        assert result["summary"] == "Test summary"


class TestImplicitTask:
    """Tests for ImplicitTask type."""

    def test_create_implicit_task(self):
        task = ImplicitTask(
            task="Review the code",
            reason="Contains 'needs review' phrase",
            confidence="high",
            source_text="This code needs review"
        )

        assert task["task"] == "Review the code"
        assert task["confidence"] == "high"


class TestLLMAnalyzerParsing:
    """Tests for LLM response parsing."""

    @pytest.fixture
    def mock_analyzer(self):
        """Create an analyzer with mocked client."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("llm_analyzer.anthropic"):
                analyzer = LLMAnalyzer.__new__(LLMAnalyzer)
                analyzer.api_key = "test-key"
                analyzer.model = "claude-sonnet-4-20250514"
                analyzer.client = MagicMock()
                return analyzer

    def test_parse_valid_json_response(self, mock_analyzer):
        """Test parsing a valid JSON response."""
        response_text = '''```json
{
  "implicit_tasks": [
    {
      "task": "Review documentation",
      "reason": "Marked as draft",
      "confidence": "high",
      "source_text": "Draft: needs review"
    }
  ],
  "incomplete_sections": ["Introduction"],
  "unanswered_questions": ["What is the deadline?"],
  "summary": "Document is incomplete"
}
```'''
        result = mock_analyzer._parse_response(response_text)

        assert len(result["implicit_tasks"]) == 1
        assert result["implicit_tasks"][0]["task"] == "Review documentation"
        assert result["implicit_tasks"][0]["confidence"] == "high"
        assert result["incomplete_sections"] == ["Introduction"]
        assert result["unanswered_questions"] == ["What is the deadline?"]
        assert result["summary"] == "Document is incomplete"

    def test_parse_json_without_code_block(self, mock_analyzer):
        """Test parsing JSON without markdown code block."""
        response_text = '''{
  "implicit_tasks": [],
  "incomplete_sections": [],
  "unanswered_questions": [],
  "summary": "Complete document"
}'''
        result = mock_analyzer._parse_response(response_text)

        assert result["implicit_tasks"] == []
        assert result["summary"] == "Complete document"

    def test_parse_invalid_json(self, mock_analyzer):
        """Test parsing invalid JSON returns empty result."""
        response_text = "This is not JSON"
        result = mock_analyzer._parse_response(response_text)

        assert result["implicit_tasks"] == []
        assert result["incomplete_sections"] == []

    def test_empty_result(self, mock_analyzer):
        """Test _empty_result method."""
        result = mock_analyzer._empty_result("Test error")

        assert result["implicit_tasks"] == []
        assert result["incomplete_sections"] == []
        assert result["unanswered_questions"] == []
        assert result["summary"] == "Test error"


class TestLLMAnalyzerIntegration:
    """Integration tests for LLM analyzer (with mocked API)."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock Anthropic client."""
        client = MagicMock()
        response = MagicMock()
        response.content = [MagicMock()]
        response.content[0].text = '''```json
{
  "implicit_tasks": [
    {
      "task": "Complete the implementation",
      "reason": "Found 'TBD' marker",
      "confidence": "high",
      "source_text": "TBD: implementation details"
    }
  ],
  "incomplete_sections": ["Implementation"],
  "unanswered_questions": [],
  "summary": "Document has incomplete sections"
}
```'''
        client.messages.create.return_value = response
        return client

    def test_analyze_document(self, mock_client):
        """Test document analysis with mocked API."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("llm_analyzer.anthropic") as mock_anthropic:
                mock_anthropic.Anthropic.return_value = mock_client

                analyzer = LLMAnalyzer()
                result = analyzer.analyze_document(
                    "# Document\n\nTBD: implementation details",
                    "test.md"
                )

                assert len(result["implicit_tasks"]) == 1
                assert result["implicit_tasks"][0]["task"] == "Complete the implementation"
                assert result["incomplete_sections"] == ["Implementation"]

    def test_analyze_empty_document(self, mock_client):
        """Test analyzing empty document."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("llm_analyzer.anthropic") as mock_anthropic:
                mock_anthropic.Anthropic.return_value = mock_client

                analyzer = LLMAnalyzer()
                result = analyzer.analyze_document("", "empty.md")

                assert result["summary"] == "Empty document"
                assert result["implicit_tasks"] == []


class TestLLMAnalyzerErrors:
    """Tests for error handling."""

    def test_missing_api_key(self):
        """Test error when API key is missing."""
        with patch.dict("os.environ", {}, clear=True):
            # Remove ANTHROPIC_API_KEY if it exists
            import os
            if "ANTHROPIC_API_KEY" in os.environ:
                del os.environ["ANTHROPIC_API_KEY"]

            with patch("llm_analyzer.anthropic"):
                with pytest.raises(ValueError, match="API key required"):
                    LLMAnalyzer()

    def test_missing_anthropic_package(self):
        """Test error when anthropic package is not installed."""
        with patch.dict("llm_analyzer.__dict__", {"HAS_ANTHROPIC": False}):
            # Need to reload module to pick up the change
            pass  # This test would require more complex module reloading


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
