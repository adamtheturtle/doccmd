"""Tests for `docrun`."""

import textwrap
from pathlib import Path

from click.testing import CliRunner
from pytest_regressions.file_regression import FileRegressionFixture

from docrun import main


def test_help(file_regression: FileRegressionFixture) -> None:
    """Expected help text is shown.

    This help text is defined in files.
    To update these files, run ``pytest`` with the ``--regen-all`` flag.
    """
    runner = CliRunner(mix_stderr=False)
    arguments = ["--help"]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    file_regression.check(contents=result.output)


def test_run_command(tmp_path: Path) -> None:
    """It is possible to run a command against a code block in a document."""
    runner = CliRunner(mix_stderr=False)
    rst_file = tmp_path / "example.rst"
    content = """
    .. code-block:: python

        x = 2 + 2
        assert x == 4
    """
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = ["--language", "python", "--command", "cat", str(rst_file)]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    expected_output = textwrap.dedent(
        text="""\



        x = 2 + 2
        assert x == 4
        """,
    )

    assert result.stdout == expected_output
    assert result.stderr == ""


def test_file_does_not_exist() -> None:
    """An error is shown when a file does not exist."""


def test_line_numbers() -> None:
    """Files are padded."""


def test_multiple_code_blocks() -> None:
    """
    It is possible to run a command against multiple code blocks in a
    document.
    """


def test_language_filters() -> None:
    """Languages not specified are not run."""


def test_run_command_no_pad_file() -> None:
    """It is possible to not pad the file."""


def test_multiple_files() -> None:
    """Test running a command against multiple files."""


def test_multiple_files_multiple_types() -> None:
    """Test running a command against multiple files."""


def test_modify_file() -> None:
    """Test modifying a file."""


def test_error_code() -> None:
    """Test an error."""


def test_file_extension() -> None:
    """Test that the file extension is correct."""


def test_file_extension_unknown_language() -> None:
    """Test that the file extension is correct for an unknown language."""


def test_file_given_twice() -> None:
    """Test that a file is not given twice."""
