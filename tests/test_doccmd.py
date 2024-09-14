"""Tests for `doccmd`."""

import sys
import textwrap
from pathlib import Path

import pytest
from click.testing import CliRunner
from pytest_regressions.file_regression import FileRegressionFixture

from doccmd import main


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


def test_multiple_files(tmp_path: Path) -> None:
    """It is possible to run a command against multiple files."""
    runner = CliRunner(mix_stderr=False)
    rst_file1 = tmp_path / "example1.rst"
    rst_file2 = tmp_path / "example2.rst"
    content1 = """\
    .. code-block:: python

        x = 2 + 2
        assert x == 4
    """
    content2 = """\
    .. code-block:: python

        y = 3 + 3
        assert y == 6
    """
    rst_file1.write_text(data=content1, encoding="utf-8")
    rst_file2.write_text(data=content2, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--command",
        "cat",
        str(rst_file1),
        str(rst_file2),
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


        y = 3 + 3
        assert y == 6
        """,
    )

    assert result.stdout == expected_output
    assert result.stderr == ""


def test_multiple_files_multiple_types(tmp_path: Path) -> None:
    """
    It is possible to run a command against multiple files of multiple
    types (Markdown and rST).
    """
    runner = CliRunner(mix_stderr=False)
    rst_file = tmp_path / "example.rst"
    md_file = tmp_path / "example.md"
    rst_content = """\
    .. code-block:: python

       print("In reStructuredText code-block")

    .. code:: python

       print("In reStructuredText code")
    """
    md_content = """\
    ```python
    print("In simple markdown code block")
    ```

    ```{code-block} python
    print("In MyST code-block")
    ```

    ```{code} python
    print("In MyST code")
    ```
    """
    rst_file.write_text(data=rst_content, encoding="utf-8")
    md_file.write_text(data=md_content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--command",
        "cat",
        "--no-pad-file",
        str(rst_file),
        str(md_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    expected_output = textwrap.dedent(
        text="""\
        print("In reStructuredText code-block")
        print("In reStructuredText code")
        print("In simple markdown code block")
        print("In MyST code-block")
        print("In MyST code")
        """,
    )

    assert result.stdout == expected_output
    assert result.stderr == ""


def test_modify_file(tmp_path: Path) -> None:
    """Commands can modify files."""
    runner = CliRunner(mix_stderr=False)
    rst_file = tmp_path / "example.rst"
    content = """\
    .. code-block:: python

        a = 1
        b = 1
        c = 1
    """
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--command",
        "truncate -s 9",
        str(rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    modified_content = rst_file.read_text(encoding="utf-8")
    expected_modified_content = """\
    .. code-block:: python

        a = 1
        b
    """
    assert modified_content == expected_modified_content


def test_exit_code(tmp_path: Path) -> None:
    """The exit code of the first failure is propagated."""
    runner = CliRunner(mix_stderr=False)
    rst_file = tmp_path / "example.rst"
    exit_code = 25
    content = f"""\
    .. code-block:: python

        import sys
        sys.exit({exit_code})
    """
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--command",
        sys.executable,
        str(rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code == exit_code


@pytest.mark.parametrize(
    argnames=["language", "expected_extension"],
    argvalues=[
        ("python", ".py"),
        ("javascript", ".js"),
    ],
)
def test_file_extension(
    tmp_path: Path,
    language: str,
    expected_extension: str,
) -> None:
    """
    The file extension of the temporary file is appropriate for the
    language.
    """
    runner = CliRunner(mix_stderr=False)
    rst_file = tmp_path / "example.rst"
    content = f"""\
    .. code-block:: {language}

        x = 2 + 2
        assert x == 4
    """
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = ["--language", language, "--command", "echo", str(rst_file)]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    output = result.stdout
    output_path = Path(output.strip())
    assert output_path.suffix == expected_extension


@pytest.mark.parametrize(argnames="extension", argvalues=["foobar", ".foobar"])
def test_given_file_extension(tmp_path: Path, extension: str) -> None:
    """It is possible to specify the file extension."""
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
        "--file-suffix",
        extension,
        "--command",
        "echo",
        str(rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    output = result.stdout
    output_path = Path(output.strip())
    assert output_path.suffixes == [".foobar"]


def test_given_prefix(tmp_path: Path) -> None:
    """It is possible to specify a prefix for the temporary file."""
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
        "--file-name-prefix",
        "myprefix",
        "--command",
        "echo",
        str(rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    output = result.stdout
    output_path = Path(output.strip())
    assert output_path.name.startswith("myprefix_")


def test_file_extension_unknown_language(tmp_path: Path) -> None:
    """
    The file extension of the temporary file is `.txt` for any unknown
    language.
    """
    runner = CliRunner(mix_stderr=False)
    rst_file = tmp_path / "example.rst"
    content = """\
    .. code-block:: unknown

        x = 2 + 2
        assert x == 4
    """
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = ["--language", "unknown", "--command", "echo", str(rst_file)]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    output = result.stdout
    output_path = Path(output.strip())
    assert output_path.suffix == ".txt"


def test_file_given_multiple_times(tmp_path: Path) -> None:
    """No error is shown when a file is given multiple times."""
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
        str(rst_file),
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


        x = 2 + 2
        assert x == 4
        """,
    )

    assert result.stdout == expected_output
    assert result.stderr == ""


def test_verbose(tmp_path: Path) -> None:
    """Verbose output is shown."""
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
        "--verbose",
        str(rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    expected_output = textwrap.dedent(
        text=f"""\
        Running 'cat' on code block at {rst_file} line 1


        x = 2 + 2
        assert x == 4
        """,
    )
    assert result.stdout == expected_output


def test_lowercase_file_name(tmp_path: Path) -> None:
    """It is possible to convert the file name to lowercase."""
    runner = CliRunner(mix_stderr=False)
    rst_file = tmp_path / "Example.RST"
    content = """\
    .. code-block:: python

        x = 2 + 2
        assert x == 4
    """
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--file-name-prefix",
        "UPPERCASE_PREFIX",
        "--command",
        "echo",
        "--lowercase-file-name",
        str(rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    output = result.stdout
    output_path = Path(output.strip())
    assert output_path.name.startswith("UPPERCASE_PREFIX_example_rst")
