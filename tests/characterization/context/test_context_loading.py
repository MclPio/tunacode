"""Unit tests for TUNACODE.md context injection."""

import os
import tempfile
from pathlib import Path

import pytest

from tunacode.context import get_code_style, get_context
from tunacode.core.agents.main import get_or_create_agent
from tunacode.core.state import StateManager


@pytest.mark.asyncio
async def test_get_code_style_walks_up_directory_tree():
    """Test that get_code_style looks for TUNACODE.md up the directory tree."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create nested directories with TUNACODE.md files
        root_dir = Path(tmpdir)
        sub_dir = root_dir / "subdir"
        sub_sub_dir = sub_dir / "subsubdir"

        sub_sub_dir.mkdir(parents=True)

        # Create TUNACODE.md at different levels
        (root_dir / "TUNACODE.md").write_text("# Root context\nRoot level")
        (sub_dir / "TUNACODE.md").write_text("# Sub context\nSub level")

        # Change to deepest directory
        original_cwd = os.getcwd()
        try:
            os.chdir(sub_sub_dir)

            # Should concatenate both files
            style = await get_code_style()

            # Both contexts should be included (in reverse order - closest first)
            assert "Sub level" in style
            assert "Root level" in style

            # Verify order - sub should come before root
            assert style.index("Sub level") < style.index("Root level")

        finally:
            os.chdir(original_cwd)


@pytest.mark.asyncio
async def test_get_code_style_handles_empty_file():
    """Test that empty TUNACODE.md files don't break loading."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tunacode_path = Path(tmpdir) / "TUNACODE.md"
        tunacode_path.write_text("")  # Empty file

        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            style = await get_code_style()

            # Should return empty string for empty file
            assert style == ""

        finally:
            os.chdir(original_cwd)


@pytest.mark.asyncio
async def test_get_context_returns_all_context_types():
    """Test that get_context returns git, directory, style, and files info."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create TUNACODE.md
        tunacode_path = Path(tmpdir) / "TUNACODE.md"
        tunacode_path.write_text("# Test context")

        # Create some files for directory structure
        (Path(tmpdir) / "src").mkdir()
        (Path(tmpdir) / "tests").mkdir()

        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            context = await get_context()

            # Should have all context types
            assert "git" in context
            assert "directory" in context
            assert "codeStyle" in context
            assert "claudeFiles" in context

            # Code style should contain our content
            assert "Test context" in context["codeStyle"]

        finally:
            os.chdir(original_cwd)


def test_agent_creation_with_large_tunacode_md():
    """Test that agent handles large TUNACODE.md files gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a large TUNACODE.md (10KB)
        large_content = "# Large Context\n\n" + ("x" * 80 + "\n") * 125
        tunacode_path = Path(tmpdir) / "TUNACODE.md"
        tunacode_path.write_text(large_content)

        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            # Should not fail with large file
            state_manager = StateManager()
            agent = get_or_create_agent("openai:gpt-4", state_manager)

            assert agent is not None

        finally:
            os.chdir(original_cwd)


def test_agent_creation_with_malformed_tunacode_md():
    """Test that agent handles malformed TUNACODE.md gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create TUNACODE.md with potential encoding issues
        tunacode_path = Path(tmpdir) / "TUNACODE.md"

        # Write binary data that might cause encoding issues
        with open(tunacode_path, "wb") as f:
            f.write(b"# Context\n\x80\x81\x82Invalid UTF-8")

        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            # Should not crash on malformed file
            state_manager = StateManager()
            agent = get_or_create_agent("openai:gpt-4", state_manager)

            assert agent is not None

        finally:
            os.chdir(original_cwd)
