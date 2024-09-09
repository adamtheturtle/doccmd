"""Tests for `docrun`."""

from click.testing import CliRunner
from pytest_regressions.file_regression import FileRegressionFixture

from docrun import main


def test_help(file_regression: FileRegressionFixture) -> None:
    """Expected help text is shown.

    This help text is defined in files.
    To update these files, run ``pytest`` with the ``--regen-all`` flag.
    """
    runner = CliRunner()
    arguments = ["--help"]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    file_regression.check(contents=result.output)


def test_run_command() -> None:
    """Test running a command."""
    # TODO: Multiple files, rst and md


def test_modify_file() -> None:
    """Test modifying a file."""


def test_error() -> None:
    """Test an error."""


def test_file_ending() -> None:
    """Test that the file ending is correct."""


def test_file_ending_unknown_language() -> None:
    """Test that the file ending is correct for an unknown language."""


def test_file_given_twice() -> None:
    """Test that a file is not given twice."""
