"""
Tests for `doccmd`.
"""

import stat
import subprocess
import sys
import textwrap
import uuid
from collections.abc import Sequence
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
    assert result.exit_code == 0, (result.stdout, result.stderr)
    file_regression.check(contents=result.output)


def test_run_command(tmp_path: Path) -> None:
    """
    It is possible to run a command against a code block in a document.
    """
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
    assert result.exit_code == 0, (result.stdout, result.stderr)
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


def test_double_language(tmp_path: Path) -> None:
    """
    Giving the same language twice does not run the command twice.
    """
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
        "--language",
        "python",
        "--command",
        "cat",
        str(rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
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
    """
    An error is shown when a file does not exist.
    """
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
    assert "File 'non_existent_file.rst' does not exist" in result.stderr


def test_not_utf_8_file_given(tmp_path: Path) -> None:
    """
    No error is given if a file is passed in which is not UTF-8.
    """
    runner = CliRunner(mix_stderr=False)
    rst_file = tmp_path / "example.rst"
    content = """\
    .. code-block:: python

       print("\xc0\x80")
    """
    rst_file.write_text(data=content, encoding="latin1")
    arguments = ["--language", "python", "--command", "cat", str(rst_file)]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    expected_output = ""
    assert result.stdout == expected_output
    assert result.stderr == ""


def test_multiple_code_blocks(tmp_path: Path) -> None:
    """
    It is possible to run a command against multiple code blocks in a document.
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
    assert result.exit_code == 0, (result.stdout, result.stderr)
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
    """
    Languages not specified are not run.
    """
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
    assert result.exit_code == 0, (result.stdout, result.stderr)
    expected_output = textwrap.dedent(
        text="""\


        x = 2 + 2
        assert x == 4
        """,
    )

    assert result.stdout == expected_output
    assert result.stderr == ""


def test_run_command_no_pad_file(tmp_path: Path) -> None:
    """
    It is possible to not pad the file.
    """
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
    assert result.exit_code == 0, (result.stdout, result.stderr)
    expected_output = textwrap.dedent(
        text="""\
        x = 2 + 2
        assert x == 4
        """,
    )

    assert result.stdout == expected_output
    assert result.stderr == ""


def test_multiple_files(tmp_path: Path) -> None:
    """
    It is possible to run a command against multiple files.
    """
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
    assert result.exit_code == 0, (result.stdout, result.stderr)
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
    It is possible to run a command against multiple files of multiple types
    (Markdown and rST).
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
    assert result.exit_code == 0, (result.stdout, result.stderr)
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
    """
    Commands can modify files.
    """
    runner = CliRunner(mix_stderr=False)
    rst_file = tmp_path / "example.rst"
    content = """\
    .. code-block:: python

        a = 1
        b = 1
        c = 1
    """
    rst_file.write_text(data=content, encoding="utf-8")
    modify_code_script = textwrap.dedent(
        """\
        #!/usr/bin/env python

        import sys

        with open(sys.argv[1], "w") as file:
            file.write("foobar")
        """
    )
    modify_code_file = tmp_path / "modify_code.py"
    modify_code_file.write_text(data=modify_code_script, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--command",
        f"python {modify_code_file.as_posix()}",
        str(rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    modified_content = rst_file.read_text(encoding="utf-8")
    expected_modified_content = """\
    .. code-block:: python

        foobar
    """
    assert modified_content == expected_modified_content


def test_exit_code(tmp_path: Path) -> None:
    """
    The exit code of the first failure is propagated.
    """
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
        Path(sys.executable).as_posix(),
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
    The file extension of the temporary file is appropriate for the language.
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
    assert result.exit_code == 0, (result.stdout, result.stderr)
    output = result.stdout
    output_path = Path(output.strip())
    assert output_path.suffix == expected_extension


@pytest.mark.parametrize(argnames="extension", argvalues=["foobar", ".foobar"])
def test_given_file_extension(tmp_path: Path, extension: str) -> None:
    """
    It is possible to specify the file extension.
    """
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
        "--temporary-file-extension",
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
    assert result.exit_code == 0, (result.stdout, result.stderr)
    output = result.stdout
    output_path = Path(output.strip())
    assert output_path.suffixes == [".foobar"]


def test_given_prefix(tmp_path: Path) -> None:
    """
    It is possible to specify a prefix for the temporary file.
    """
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
        "--temporary-file-name-prefix",
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
    assert result.exit_code == 0, (result.stdout, result.stderr)
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
    assert result.exit_code == 0, (result.stdout, result.stderr)
    output = result.stdout
    output_path = Path(output.strip())
    assert output_path.suffix == ".txt"


def test_file_given_multiple_times(tmp_path: Path) -> None:
    """
    Files given multiple times are de-duplicated.
    """
    runner = CliRunner(mix_stderr=False)
    rst_file = tmp_path / "example.rst"
    other_rst_file = tmp_path / "other_example.rst"
    content = """\
    .. code-block:: python

        block
    """
    other_content = """\
    .. code-block:: python

        other_block
    """
    rst_file.write_text(data=content, encoding="utf-8")
    other_rst_file.write_text(data=other_content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--command",
        "cat",
        str(rst_file),
        str(other_rst_file),
        str(rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    expected_output = textwrap.dedent(
        text="""\


        block


        other_block
        """,
    )

    assert result.stdout == expected_output
    assert result.stderr == ""


def test_verbose_running(tmp_path: Path) -> None:
    """
    Verbose output is shown showing what is running.
    """
    runner = CliRunner(mix_stderr=False)
    rst_file = tmp_path / "example.rst"
    content = """\
    .. code-block:: python

        x = 2 + 2
        assert x == 4

    .. skip doccmd[all]: next

    .. code-block:: python

        x = 3 + 3
        assert x == 6

    .. code-block:: shell

        echo 1
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
    assert result.exit_code == 0, (result.stdout, result.stderr)
    expected_output = textwrap.dedent(
        text=f"""\
        Running 'cat' on code block at {rst_file} line 1


        x = 2 + 2
        assert x == 4
        """,
    )
    assert result.stdout == expected_output


def test_verbose_not_utf_8(tmp_path: Path) -> None:
    """
    Verbose output shows what files are being skipped because they are not
    UTF-8.
    """
    runner = CliRunner(mix_stderr=False)
    rst_file = tmp_path / "example.rst"
    content = """\
    .. code-block:: python

       print("\xc0\x80")
    """
    rst_file.write_text(data=content, encoding="latin1")
    arguments = [
        "--verbose",
        "--language",
        "python",
        "--command",
        "cat",
        str(rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    expected_output = ""
    assert result.stdout == expected_output
    # The first line here is not relevant, but we test the entire
    # verbose output to ensure that it is as expected.
    expected_stderr = textwrap.dedent(
        text=f"""\
            Not using PTY for running commands.
            Skipping '{rst_file}' because it is not UTF-8 encoded.
            """,
    )
    assert result.stderr == expected_stderr


def test_directory_passed_in(tmp_path: Path) -> None:
    """
    An error is shown when a directory is passed in instead of a file.
    """
    runner = CliRunner(mix_stderr=False)
    directory = tmp_path / "example_dir"
    directory.mkdir()
    arguments = [
        "--language",
        "python",
        "--command",
        "cat",
        str(directory),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    expected_stderr = textwrap.dedent(
        text=(
            f"""\
            Usage: doccmd [OPTIONS] [DOCUMENT_PATHS]...
            Try 'doccmd --help' for help.

            Error: Invalid value for '[DOCUMENT_PATHS]...': File '{directory}' is a directory.
            """  # noqa: E501
        ),
    )
    assert result.stderr == expected_stderr


def test_main_entry_point() -> None:
    """
    It is possible to run the main entry point.
    """
    result = subprocess.run(
        args=[sys.executable, "-m", "doccmd"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert "Usage:" in result.stderr


def test_command_not_found(tmp_path: Path) -> None:
    """
    An error is shown when the command is not found.
    """
    runner = CliRunner(mix_stderr=False)
    rst_file = tmp_path / "example.rst"
    non_existent_command = uuid.uuid4().hex
    non_existent_command_with_args = f"{non_existent_command} --help"
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
        non_existent_command_with_args,
        str(rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    expected_error = f"Error running command '{non_existent_command}':"
    assert result.stderr.startswith(expected_error)


def test_not_executable(tmp_path: Path) -> None:
    """
    An error is shown when the command is a non-executable file.
    """
    runner = CliRunner(mix_stderr=False)
    rst_file = tmp_path / "example.rst"
    not_executable_command = tmp_path / "non_executable"
    not_executable_command.touch()
    not_executable_command_with_args = (
        f"{not_executable_command.as_posix()} --help"
    )
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
        not_executable_command_with_args,
        str(rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    expected_error = "Error running command:"
    expected_error = (
        f"Error running command '{not_executable_command.as_posix()}':"
    )
    assert result.stderr.startswith(expected_error)


def test_multiple_languages(tmp_path: Path) -> None:
    """
    It is possible to run a command against multiple code blocks in a document
    with different languages.
    """
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
    arguments = [
        "--no-pad-file",
        "--language",
        "python",
        "--language",
        "javascript",
        "--command",
        "cat",
        str(rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    expected_output = textwrap.dedent(
        text="""\
        x = 2 + 2
        assert x == 4
        var y = 3 + 3;
        console.assert(y === 6);
        """,
    )

    assert result.stdout == expected_output
    assert result.stderr == ""


def test_default_skip_rst(tmp_path: Path) -> None:
    """
    By default, the next code block after a 'doccmd skip: next' comment in a
    rST document is not run.
    """
    runner = CliRunner(mix_stderr=False)
    rst_file = tmp_path / "example.rst"
    content = """\
    .. code-block:: python

       block_1

    .. skip doccmd[all]: next

    .. code-block:: python

        block_2

    .. code-block:: python

        block_3
    """
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--no-pad-file",
        "--language",
        "python",
        "--command",
        "cat",
        str(rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    expected_output = textwrap.dedent(
        text="""\
        block_1
        block_3
        """,
    )

    assert result.stdout == expected_output
    assert result.stderr == ""


def test_custom_skip_markers_rst(tmp_path: Path) -> None:
    """
    The next code block after a custom skip marker comment in a rST document is
    not run.
    """
    runner = CliRunner(mix_stderr=False)
    rst_file = tmp_path / "example.rst"
    skip_marker = uuid.uuid4().hex
    content = f"""\
    .. code-block:: python

       block_1

    .. skip doccmd[{skip_marker}]: next

    .. code-block:: python

        block_2

    .. code-block:: python

        block_3
    """
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--no-pad-file",
        "--language",
        "python",
        "--skip-marker",
        skip_marker,
        "--command",
        "cat",
        str(rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    expected_output = textwrap.dedent(
        text="""\
        block_1
        block_3
        """,
    )

    assert result.stdout == expected_output
    assert result.stderr == ""


def test_default_skip_myst(tmp_path: Path) -> None:
    """
    By default, the next code block after a 'doccmd skip: next' comment in a
    MyST document is not run.
    """
    runner = CliRunner(mix_stderr=False)
    myst_file = tmp_path / "example.md"
    content = """\
    Example

    ```python
    block_1
    ```

    <!--- skip doccmd[all]: next -->

    ```python
    block_2
    ```

    ```python
    block_3
    ```

    % skip doccmd[all]: next

    ```python
    block_4
    ```
    """
    myst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--no-pad-file",
        "--language",
        "python",
        "--command",
        "cat",
        str(myst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    expected_output = textwrap.dedent(
        text="""\
        block_1
        block_3
        """,
    )

    assert result.stdout == expected_output
    assert result.stderr == ""


def test_custom_skip_markers_myst(tmp_path: Path) -> None:
    """
    The next code block after a custom skip marker comment in a MyST document
    is not run.
    """
    runner = CliRunner(mix_stderr=False)
    myst_file = tmp_path / "example.md"
    skip_marker = uuid.uuid4().hex
    content = f"""\
    Example

    ```python
    block_1
    ```

    <!--- skip doccmd[{skip_marker}]: next -->

    ```python
    block_2
    ```

    ```python
    block_3
    ```

    % skip doccmd[{skip_marker}]: next

    ```python
    block_4
    ```
    """
    myst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--no-pad-file",
        "--language",
        "python",
        "--skip-marker",
        skip_marker,
        "--command",
        "cat",
        str(myst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    expected_output = textwrap.dedent(
        text="""\
        block_1
        block_3
        """,
    )

    assert result.stdout == expected_output
    assert result.stderr == ""


def test_multiple_skip_markers(tmp_path: Path) -> None:
    """
    All given skip markers, including the default one, are respected.
    """
    runner = CliRunner(mix_stderr=False)
    rst_file = tmp_path / "example.rst"
    skip_marker_1 = uuid.uuid4().hex
    skip_marker_2 = uuid.uuid4().hex
    content = f"""\
    .. code-block:: python

       block_1

    .. skip doccmd[{skip_marker_1}]: next

    .. code-block:: python

        block_2

    .. skip doccmd[{skip_marker_2}]: next

    .. code-block:: python

        block_3

    .. skip doccmd[all]: next

    .. code-block:: python

        block_4
    """
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--no-pad-file",
        "--language",
        "python",
        "--skip-marker",
        skip_marker_1,
        "--skip-marker",
        skip_marker_2,
        "--command",
        "cat",
        str(rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    expected_output = textwrap.dedent(
        text="""\
        block_1
        """,
    )

    assert result.stdout == expected_output
    assert result.stderr == ""


def test_skip_start_end(tmp_path: Path) -> None:
    """
    Skip start and end markers are respected.
    """
    runner = CliRunner(mix_stderr=False)
    rst_file = tmp_path / "example.rst"
    skip_marker_1 = uuid.uuid4().hex
    skip_marker_2 = uuid.uuid4().hex
    content = """\
    .. code-block:: python

       block_1

    .. skip doccmd[all]: start

    .. code-block:: python

        block_2

    .. code-block:: python

        block_3

    .. skip doccmd[all]: end

    .. code-block:: python

        block_4
    """
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--no-pad-file",
        "--language",
        "python",
        "--skip-marker",
        skip_marker_1,
        "--skip-marker",
        skip_marker_2,
        "--command",
        "cat",
        str(rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    expected_output = textwrap.dedent(
        text="""\
        block_1
        block_4
        """,
    )

    assert result.stdout == expected_output
    assert result.stderr == ""


def test_duplicate_skip_marker(tmp_path: Path) -> None:
    """
    Duplicate skip markers are respected.
    """
    runner = CliRunner(mix_stderr=False)
    rst_file = tmp_path / "example.rst"
    skip_marker = uuid.uuid4().hex
    content = f"""\
    .. code-block:: python

       block_1

    .. skip doccmd[{skip_marker}]: next

    .. code-block:: python

        block_2

    .. skip doccmd[{skip_marker}]: next

    .. code-block:: python

        block_3
    """
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--no-pad-file",
        "--language",
        "python",
        "--skip-marker",
        skip_marker,
        "--skip-marker",
        skip_marker,
        "--command",
        "cat",
        str(rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    expected_output = textwrap.dedent(
        text="""\
        block_1
        """,
    )

    assert result.stdout == expected_output
    assert result.stderr == ""


def test_default_skip_marker_given(tmp_path: Path) -> None:
    """
    No error is shown when the default skip marker is given.
    """
    runner = CliRunner(mix_stderr=False)
    rst_file = tmp_path / "example.rst"
    skip_marker = "all"
    content = f"""\
    .. code-block:: python

       block_1

    .. skip doccmd[{skip_marker}]: next

    .. code-block:: python

        block_2

    .. skip doccmd[{skip_marker}]: next

    .. code-block:: python

        block_3
    """
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--no-pad-file",
        "--language",
        "python",
        "--skip-marker",
        skip_marker,
        "--command",
        "cat",
        str(rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    expected_output = textwrap.dedent(
        text="""\
        block_1
        """,
    )

    assert result.stdout == expected_output
    assert result.stderr == ""


def test_empty_file(tmp_path: Path) -> None:
    """
    No error is shown when an empty file is given.
    """
    runner = CliRunner(mix_stderr=False)
    rst_file = tmp_path / "example.rst"
    rst_file.touch()
    arguments = [
        "--no-pad-file",
        "--language",
        "python",
        "--command",
        "cat",
        str(rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert result.stdout == ""
    assert result.stderr == ""


@pytest.mark.parametrize(
    argnames=("source_newline", "expect_crlf", "expect_cr", "expect_lf"),
    argvalues=(
        ["\n", False, False, True],
        ["\r\n", True, True, True],
        ["\r", False, True, False],
    ),
)
def test_detect_line_endings(
    *,
    tmp_path: Path,
    source_newline: str,
    expect_crlf: bool,
    expect_cr: bool,
    expect_lf: bool,
) -> None:
    """
    The line endings of the original file are used in the new file.
    """
    runner = CliRunner(mix_stderr=False)
    rst_file = tmp_path / "example.rst"
    content = """\
    .. code-block:: python

       block_1
    """
    rst_file.write_text(data=content, encoding="utf-8", newline=source_newline)
    arguments = [
        "--no-pad-file",
        "--language",
        "python",
        "--command",
        "cat",
        str(rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert result.stderr == ""
    assert bool(b"\r\n" in result.stdout_bytes) == expect_crlf
    assert bool(b"\r" in result.stdout_bytes) == expect_cr
    assert bool(b"\n" in result.stdout_bytes) == expect_lf


def test_one_supported_markup_in_another_extension(tmp_path: Path) -> None:
    """
    Code blocks in a supported markup language in a file with an extension
    which matches another extension are not run.
    """
    runner = CliRunner(mix_stderr=False)
    rst_file = tmp_path / "example.rst"
    content = """\
    ```python
    print("In simple markdown code block")
    ```

    ```{code-block} python
    print("In MyST code-block")
    ```
    """
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = ["--language", "python", "--command", "cat", str(rst_file)]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    # Empty because the Markdown-style code block is not run in.
    expected_output = ""
    assert result.stdout == expected_output
    assert result.stderr == ""


@pytest.mark.parametrize(argnames="extension", argvalues=[".unknown", ""])
def test_unknown_file_suffix(extension: str, tmp_path: Path) -> None:
    """
    An error is shown when the file suffix is not known.
    """
    runner = CliRunner(mix_stderr=False)
    document_file = tmp_path / ("example" + extension)
    content = """\
    .. code-block:: python

        x = 2 + 2
        assert x == 4
    """
    document_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--command",
        "cat",
        str(document_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code != 0, (result.stdout, result.stderr)
    expected_stderr = textwrap.dedent(
        text=f"""\
            Usage: doccmd [OPTIONS] [DOCUMENT_PATHS]...
            Try 'doccmd --help' for help.

            Error: Markup language not known for {document_file}.
            """,
    )

    assert result.stdout == ""
    assert result.stderr == expected_stderr


@pytest.mark.parametrize(
    argnames=["options", "expected_output"],
    argvalues=[
        # We cannot test the actual behavior of using a pseudo-terminal,
        # as CI (e.g. GitHub Actions) does not support it.
        # Therefore we do not test the `--use-pty` option.
        (["--no-use-pty"], "stdout is not a terminal."),
        # We are not really testing the detection mechanism.
        (["--detect-use-pty"], "stdout is not a terminal."),
    ],
    ids=["no-use-pty", "detect-use-pty"],
)
def test_pty(
    tmp_path: Path,
    options: Sequence[str],
    expected_output: str,
) -> None:
    """
    Test options for using pseudo-terminal.
    """
    runner = CliRunner(mix_stderr=False)
    rst_file = tmp_path / "example.rst"
    tty_test = textwrap.dedent(
        text="""\
        import sys

        if sys.stdout.isatty():
            print("stdout is a terminal.")
        else:
            print("stdout is not a terminal.")
        """,
    )
    script = tmp_path / "my_script.py"
    script.write_text(data=tty_test)
    script.chmod(mode=stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    content = """\
    .. code-block:: python

       block_1
    """
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        *options,
        "--no-pad-file",
        "--language",
        "python",
        "--command",
        f"{Path(sys.executable).as_posix()} {script.as_posix()}",
        str(rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert result.stderr == ""
    assert result.stdout.strip() == expected_output
