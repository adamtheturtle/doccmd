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
    content = """\
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
        # The file is padded so that any error messages relate to the correct
        # line number in the original file.
        text="""\


        x = 2 + 2
        assert x == 4
        """,
    )

    assert result.stdout == expected_output
    assert result.stderr == ""


def test_file_does_not_exist() -> None:
    """An error is shown when a file does not exist."""
    runner = CliRunner(mix_stderr=False)
    arguments = [
        "--language",
        "python",
        "--command",
        "cat",
        "non_existent_file.rst",
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    assert "Path 'non_existent_file.rst' does not exist" in result.stderr


def test_multiple_code_blocks(tmp_path: Path) -> None:
    """
    It is possible to run a command against multiple code blocks in a
    document.
    """
    runner = CliRunner(mix_stderr=False)
    rst_file = tmp_path / "example.rst"
    content = """\
    .. code-block:: python

        x = 2 + 2
        assert x == 4

    .. code-block:: python

        y = 3 + 3
        assert y == 6
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







        y = 3 + 3
        assert y == 6
        """,
    )

    assert result.stdout == expected_output
    assert result.stderr == ""


def test_language_filters(tmp_path: Path) -> None:
    """Languages not specified are not run."""
    runner = CliRunner(mix_stderr=False)
    rst_file = tmp_path / "example.rst"
    content = """\
    .. code-block:: python

        x = 2 + 2
        assert x == 4

    .. code-block:: javascript

        var y = 3 + 3;
        console.assert(y === 6);
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


def test_run_command_no_pad_file(tmp_path: Path) -> None:
    """It is possible to not pad the file."""
    runner = CliRunner(mix_stderr=False)
    rst_file = tmp_path / "example.rst"
    content = """\
    .. code-block:: python

        x = 2 + 2
        assert x == 4
    """
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--command",
        "cat",
        "--no-pad-file",
        str(rst_file),
    ]
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


def test_multiple_files() -> None:
    """It is possible to run a command against multiple files."""


def test_multiple_files_multiple_types() -> None:
    """
    It is possible to run a command against multiple files of multiple
    types (Markdown and rST).
    """


def test_modify_file() -> None:
    """Commands can modify files."""


def test_error_code() -> None:
    """The error code of the first failure is propagated."""


def test_file_extension() -> None:
    """
    The file extension of the temporary file is appropriate for the
    language.
    """


def test_file_extension_unknown_language() -> None:
    """
    The file extension of the temporary file is txt for any unknown
    language.
    """


def test_file_given_multiple_times() -> None:
    """No error is shown when a file is given multiple times."""
