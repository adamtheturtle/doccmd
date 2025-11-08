"""
Tests for `doccmd`.
"""

import os
import stat
import subprocess
import sys
import textwrap
import uuid
from collections.abc import Sequence
from pathlib import Path

import pytest
from ansi.colour import fg
from ansi.colour.base import Graphic
from ansi.colour.fx import reset
from click.testing import CliRunner
from pytest_regressions.file_regression import FileRegressionFixture

from doccmd import main

PARALLELISM_EXIT_CODE = 2  # CLI exit when parallel writes are disallowed


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
        color=True,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    file_regression.check(contents=result.output)


def test_run_command(tmp_path: Path) -> None:
    """
    It is possible to run a command against a code block in a document.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            x = 2 + 2
            assert x == 4
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--command",
        "cat",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
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
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            x = 2 + 2
            assert x == 4
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--language",
        "python",
        "--command",
        "cat",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
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
    runner = CliRunner()
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
        color=True,
    )
    assert result.exit_code != 0
    assert "Path 'non_existent_file.rst' does not exist" in result.stderr


def test_not_utf_8_file_given(tmp_path: Path) -> None:
    """
    No error is given if a file is passed in which is not UTF-8.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

           print("\xc0\x80")
        """,
    )
    rst_file.write_text(data=content, encoding="latin1")
    arguments = [
        "--language",
        "python",
        "--command",
        "cat",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    expected_output_bytes = b'print("\xc0\x80")'
    expected_stderr = ""
    assert result.stdout_bytes.strip() == expected_output_bytes
    assert result.stderr == expected_stderr


@pytest.mark.parametrize(
    argnames=("fail_on_parse_error_options", "expected_exit_code"),
    argvalues=[
        ([], 0),
        (["--fail-on-parse-error"], 1),
    ],
)
def test_unknown_encoding(
    tmp_path: Path,
    fail_on_parse_error_options: Sequence[str],
    expected_exit_code: int,
) -> None:
    """
    An error is shown when a file cannot be decoded.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    rst_file.write_bytes(data=Path(sys.executable).read_bytes())
    arguments = [
        *fail_on_parse_error_options,
        "--language",
        "python",
        "--command",
        "cat",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    expected_stderr = (
        f"{fg.red}Could not determine encoding for {rst_file}.{reset}\n"
    )
    assert result.exit_code == expected_exit_code
    assert result.stdout == ""
    assert result.stderr == expected_stderr


def test_multiple_code_blocks(tmp_path: Path) -> None:
    """
    It is possible to run a command against multiple code blocks in a document.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            x = 2 + 2
            assert x == 4

        .. code-block:: python

            y = 3 + 3
            assert y == 6
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--command",
        "cat",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
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
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            x = 2 + 2
            assert x == 4

        .. code-block:: javascript

            var y = 3 + 3;
            console.assert(y === 6);
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--command",
        "cat",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
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
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            x = 2 + 2
            assert x == 4
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--command",
        "cat",
        "--no-pad-file",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
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
    runner = CliRunner()
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
        str(object=rst_file1),
        str(object=rst_file2),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
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
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    md_file = tmp_path / "example.md"
    rst_content = textwrap.dedent(
        text="""\
        .. code-block:: python

            print("In reStructuredText code-block")

        .. code:: python

            print("In reStructuredText code")
        """,
    )
    md_content = textwrap.dedent(
        text="""\
        ```python
        print("In simple markdown code block")
        ```

        ```{code-block} python
        print("In MyST code-block")
        ```

        ```{code} python
        print("In MyST code")
        ```
        """,
    )
    rst_file.write_text(data=rst_content, encoding="utf-8")
    md_file.write_text(data=md_content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--command",
        "cat",
        "--no-pad-file",
        str(object=rst_file),
        str(object=md_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
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


@pytest.mark.parametrize(
    argnames=("write_to_file_options", "expected_content"),
    argvalues=[
        (
            [],
            textwrap.dedent(
                text="""\
                .. code-block:: python

                    foobar
                """,
            ),
        ),
        (
            ["--no-write-to-file"],
            textwrap.dedent(
                text="""\
                .. code-block:: python

                    a = 1
                    b = 1
                    c = 1
                """,
            ),
        ),
    ],
)
def test_modify_file(
    tmp_path: Path,
    write_to_file_options: Sequence[str],
    expected_content: str,
) -> None:
    """
    Commands (outside of groups) can modify files when allowed.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            a = 1
            b = 1
            c = 1
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    modify_code_script = textwrap.dedent(
        text="""\
        #!/usr/bin/env python

        import sys

        with open(sys.argv[1], "w") as file:
            file.write("foobar")
        """,
    )
    modify_code_file = tmp_path / "modify_code.py"
    modify_code_file.write_text(data=modify_code_script, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--command",
        f"python {modify_code_file.as_posix()}",
        *write_to_file_options,
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert rst_file.read_text(encoding="utf-8") == expected_content


def test_exit_code(tmp_path: Path) -> None:
    """
    The exit code of the first failure is propagated.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    exit_code = 25
    content = textwrap.dedent(
        text=f"""\
        .. code-block:: python

            import sys
            sys.exit({exit_code})
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--command",
        Path(sys.executable).as_posix(),
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == exit_code, (result.stdout, result.stderr)
    assert result.stdout == ""
    assert result.stderr == ""


@pytest.mark.parametrize(
    argnames=("language", "expected_extension"),
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
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text=f"""\
        .. code-block:: {language}

            x = 2 + 2
            assert x == 4
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        language,
        "--command",
        "echo",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    output = result.stdout
    output_path = Path(output.strip())
    assert output_path.suffix == expected_extension


def test_given_temporary_file_extension(tmp_path: Path) -> None:
    """
    It is possible to specify the file extension for created temporary files.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            x = 2 + 2
            assert x == 4
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--temporary-file-extension",
        ".foobar",
        "--command",
        "echo",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    output = result.stdout
    output_path = Path(output.strip())
    assert output_path.suffixes == [".foobar"]


def test_given_temporary_file_extension_no_leading_period(
    tmp_path: Path,
) -> None:
    """
    An error is shown when a given temporary file extension is given with no
    leading period.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            x = 2 + 2
            assert x == 4
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--temporary-file-extension",
        "foobar",
        "--command",
        "echo",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code != 0, (result.stdout, result.stderr)
    assert result.stdout == ""
    expected_stderr = textwrap.dedent(
        text="""\
        Usage: doccmd [OPTIONS] [DOCUMENT_PATHS]...
        Try 'doccmd --help' for help.

        Error: Invalid value for '--temporary-file-extension': 'foobar' does not start with a '.'.
        """,  # noqa: E501
    )
    assert result.stderr == expected_stderr


def test_given_prefix(tmp_path: Path) -> None:
    """
    It is possible to specify a prefix for the temporary file.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            x = 2 + 2
            assert x == 4
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--temporary-file-name-prefix",
        "myprefix",
        "--command",
        "echo",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
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
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. code-block:: unknown

            x = 2 + 2
            assert x == 4
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        "unknown",
        "--command",
        "echo",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    output = result.stdout
    output_path = Path(output.strip())
    assert output_path.suffix == ".txt"


def test_file_given_multiple_times(tmp_path: Path) -> None:
    """
    Files given multiple times are de-duplicated.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    other_rst_file = tmp_path / "other_example.rst"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            block
        """,
    )
    other_content = textwrap.dedent(
        text="""\
        .. code-block:: python

            other_block
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    other_rst_file.write_text(data=other_content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--command",
        "cat",
        str(object=rst_file),
        str(object=other_rst_file),
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
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


def test_example_workers_requires_no_write_to_file(tmp_path: Path) -> None:
    """
    Using --example-workers>1 without --no-write-to-file is rejected.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            print("Hello")
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    result = runner.invoke(
        cli=main,
        args=[
            "--language",
            "python",
            "--command",
            "cat",
            "--example-workers",
            "2",
            str(object=rst_file),
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == PARALLELISM_EXIT_CODE
    assert "--no-write-to-file" in result.stderr


def test_example_workers_runs_commands(tmp_path: Path) -> None:
    """
    Commands still run when example-workers>1 and --no-write-to-file is given.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            print("From the first block")

        .. code-block:: python

            print("From the second block")
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    result = runner.invoke(
        cli=main,
        args=[
            "--language",
            "python",
            "--command",
            "cat",
            "--no-pad-file",
            "--no-write-to-file",
            "--example-workers",
            "2",
            str(object=rst_file),
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert "From the first block" in result.stdout
    assert "From the second block" in result.stdout


def test_example_workers_zero_requires_no_write_when_auto_parallel(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Example-workers=0 auto-detects CPUs and still requires --no-write-to-file
    when >1.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            print("Hello")
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    monkeypatch.setattr(target=os, name="cpu_count", value=lambda: 4)
    result = runner.invoke(
        cli=main,
        args=[
            "--language",
            "python",
            "--command",
            "cat",
            "--example-workers",
            "0",
            str(object=rst_file),
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == PARALLELISM_EXIT_CODE
    assert "--no-write-to-file" in result.stderr


def test_example_workers_zero_allows_running_when_cpu_is_single(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Example-workers=0 falls back to sequential execution when only one CPU is
    detected.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            print("Only one CPU")
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    monkeypatch.setattr(target=os, name="cpu_count", value=lambda: 1)
    result = runner.invoke(
        cli=main,
        args=[
            "--language",
            "python",
            "--command",
            "cat",
            "--example-workers",
            "0",
            str(object=rst_file),
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert "Only one CPU" in result.stdout


def test_document_workers_requires_no_write_to_file(tmp_path: Path) -> None:
    """
    Using --document-workers>1 without --no-write-to-file is rejected.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            print("Hello")
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    result = runner.invoke(
        cli=main,
        args=[
            "--language",
            "python",
            "--command",
            "cat",
            "--document-workers",
            "2",
            str(object=rst_file),
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == PARALLELISM_EXIT_CODE
    assert "--no-write-to-file" in result.stderr


def test_document_workers_runs_commands(tmp_path: Path) -> None:
    """
    Commands run across multiple documents when document-workers>1.
    """
    runner = CliRunner()
    first_rst = tmp_path / "first.rst"
    second_rst = tmp_path / "second.rst"
    first_content = textwrap.dedent(
        text="""\
        .. code-block:: python

            print("From the first document")
        """,
    )
    second_content = textwrap.dedent(
        text="""\
        .. code-block:: python

            print("From the second document")
        """,
    )
    first_rst.write_text(data=first_content, encoding="utf-8")
    second_rst.write_text(data=second_content, encoding="utf-8")
    result = runner.invoke(
        cli=main,
        args=[
            "--language",
            "python",
            "--command",
            "cat",
            "--no-pad-file",
            "--no-write-to-file",
            "--document-workers",
            "2",
            str(object=first_rst),
            str(object=second_rst),
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert "From the first document" in result.stdout
    assert "From the second document" in result.stdout


def test_document_workers_zero_requires_no_write_when_auto_parallel(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Document-workers=0 auto-detects CPUs and still requires --no-write-to-file
    when >1.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            print("Hello")
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    monkeypatch.setattr(target=os, name="cpu_count", value=lambda: 4)
    result = runner.invoke(
        cli=main,
        args=[
            "--language",
            "python",
            "--command",
            "cat",
            "--document-workers",
            "0",
            str(object=rst_file),
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == PARALLELISM_EXIT_CODE
    assert "--no-write-to-file" in result.stderr


def test_document_workers_zero_allows_running_when_cpu_is_single(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Document-workers=0 runs sequentially when only one CPU is detected.
    """
    runner = CliRunner()
    first_rst = tmp_path / "first.rst"
    second_rst = tmp_path / "second.rst"
    first_content = textwrap.dedent(
        text="""\
        .. code-block:: python

            print("First")
        """,
    )
    second_content = textwrap.dedent(
        text="""\
        .. code-block:: python

            print("Second")
        """,
    )
    first_rst.write_text(data=first_content, encoding="utf-8")
    second_rst.write_text(data=second_content, encoding="utf-8")
    monkeypatch.setattr(target=os, name="cpu_count", value=lambda: 1)
    result = runner.invoke(
        cli=main,
        args=[
            "--language",
            "python",
            "--command",
            "cat",
            "--document-workers",
            "0",
            str(object=first_rst),
            str(object=second_rst),
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert "First" in result.stdout
    assert "Second" in result.stdout


def test_cpu_count_returns_none(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    When os.cpu_count() returns None, workers default to 1.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            print("CPU count is None")
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    monkeypatch.setattr(target=os, name="cpu_count", value=lambda: None)
    result = runner.invoke(
        cli=main,
        args=[
            "--language",
            "python",
            "--command",
            "cat",
            "--example-workers",
            "0",
            str(object=rst_file),
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert "CPU count is None" in result.stdout


def test_parallel_example_execution_error(tmp_path: Path) -> None:
    """
    Errors during parallel example execution are handled correctly.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            print("First block")

        .. code-block:: python

            print("Second block")

        .. code-block:: python

            print("Third block")
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    non_existent_command = uuid.uuid4().hex
    result = runner.invoke(
        cli=main,
        args=[
            "--language",
            "python",
            "--command",
            non_existent_command,
            "--no-write-to-file",
            "--example-workers",
            "2",
            str(object=rst_file),
        ],
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code != 0
    assert f"Error running command '{non_existent_command}'" in result.stderr


def test_parallel_document_execution_error(tmp_path: Path) -> None:
    """
    Errors during parallel document execution are handled correctly.
    """
    runner = CliRunner()
    first_rst = tmp_path / "first.rst"
    second_rst = tmp_path / "second.rst"
    first_content = textwrap.dedent(
        text="""\
        .. code-block:: python

            print("First document")
        """,
    )
    second_content = textwrap.dedent(
        text="""\
        .. code-block:: python

            print("Second document")
        """,
    )
    first_rst.write_text(data=first_content, encoding="utf-8")
    second_rst.write_text(data=second_content, encoding="utf-8")
    non_existent_command = uuid.uuid4().hex
    result = runner.invoke(
        cli=main,
        args=[
            "--language",
            "python",
            "--command",
            non_existent_command,
            "--no-write-to-file",
            "--document-workers",
            "2",
            str(object=first_rst),
            str(object=second_rst),
        ],
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code != 0
    assert f"Error running command '{non_existent_command}'" in result.stderr


def test_document_with_no_examples(tmp_path: Path) -> None:
    """
    Documents with no matching code blocks are handled correctly.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        This is a document with no code blocks.

        Just some text.
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    result = runner.invoke(
        cli=main,
        args=[
            "--language",
            "python",
            "--command",
            "cat",
            "--no-write-to-file",
            "--example-workers",
            "2",
            str(object=rst_file),
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert result.stdout == ""
    assert result.stderr == ""


def test_single_example_execution_error(tmp_path: Path) -> None:
    """
    Errors during single example execution are handled correctly.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            print("Single block")
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    non_existent_command = uuid.uuid4().hex
    result = runner.invoke(
        cli=main,
        args=[
            "--language",
            "python",
            "--command",
            non_existent_command,
            str(object=rst_file),
        ],
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code != 0
    assert f"Error running command '{non_existent_command}'" in result.stderr


def test_sequential_execution_error_with_multiple_examples(
    tmp_path: Path,
) -> None:
    """
    Errors during sequential execution of multiple examples are handled.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            print("First block")

        .. code-block:: python

            print("Second block")
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    non_existent_command = uuid.uuid4().hex
    result = runner.invoke(
        cli=main,
        args=[
            "--language",
            "python",
            "--command",
            non_existent_command,
            "--no-write-to-file",
            "--example-workers",
            "1",
            str(object=rst_file),
        ],
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code != 0
    assert f"Error running command '{non_existent_command}'" in result.stderr


def test_single_example_with_parallel_workers(tmp_path: Path) -> None:
    """
    Single example with example_workers>1 uses sequential path successfully.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            print("Only one block")
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    result = runner.invoke(
        cli=main,
        args=[
            "--language",
            "python",
            "--command",
            "cat",
            "--no-pad-file",
            "--no-write-to-file",
            "--example-workers",
            "2",
            str(object=rst_file),
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "Only one block" in result.stdout


def test_single_example_with_parallel_workers_error(tmp_path: Path) -> None:
    """
    Single example with example_workers>1 handles errors in sequential path.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            print("Only one block")
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    non_existent_command = uuid.uuid4().hex
    result = runner.invoke(
        cli=main,
        args=[
            "--language",
            "python",
            "--command",
            non_existent_command,
            "--no-write-to-file",
            "--example-workers",
            "2",
            str(object=rst_file),
        ],
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code != 0
    assert f"Error running command '{non_existent_command}'" in result.stderr


def test_verbose_running(tmp_path: Path) -> None:
    """
    ``--verbose`` shows what is running.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            x = 2 + 2
            assert x == 4

        .. skip doccmd[all]: next

        .. code-block:: python

            x = 3 + 3
            assert x == 6

        .. code-block:: shell

            echo 1
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--command",
        "cat",
        "--verbose",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    expected_output = textwrap.dedent(
        text="""\


        x = 2 + 2
        assert x == 4
        """,
    )
    expected_stderr = textwrap.dedent(
        text=f"""\
        {fg.green}Not using PTY for running commands.{reset}
        {fg.green}Running 'cat' on code block at {rst_file} line 1{reset}
        """,
    )
    assert result.stdout == expected_output
    assert result.stderr == expected_stderr


def test_verbose_running_with_stderr(tmp_path: Path) -> None:
    """
    ``--verbose`` shows what is running before any stderr output.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    # We include a group as well to ensure that the verbose output is shown
    # in the right place for groups.
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            x = 2 + 2
            assert x == 4

        .. skip doccmd[all]: next

        .. code-block:: python

            x = 3 + 3
            assert x == 6

        .. code-block:: shell

            echo 1

        .. group doccmd[all]: start

        .. code-block:: python

            block_group_1

        .. group doccmd[all]: end
        """,
    )
    command = (
        f"{Path(sys.executable).as_posix()} -c "
        "'import sys; sys.stderr.write(\"error\\n\")'"
    )
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--command",
        command,
        "--verbose",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    expected_output = ""
    expected_stderr = textwrap.dedent(
        text=f"""\
        {fg.green}Not using PTY for running commands.{reset}
        {fg.green}Running '{command}' on code block at {rst_file} line 1{reset}
        error
        {fg.green}Running '{command}' on code block at {rst_file} line 19{reset}
        error
        """,  # noqa: E501
    )
    assert result.stdout == expected_output
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
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    non_existent_command = uuid.uuid4().hex
    non_existent_command_with_args = f"{non_existent_command} --help"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            x = 2 + 2
            assert x == 4
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--command",
        non_existent_command_with_args,
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code != 0
    red_style_start = "\x1b[31m"
    expected_stderr = (
        f"{red_style_start}Error running command '{non_existent_command}':"
    )
    assert result.stderr.startswith(expected_stderr)


def test_not_executable(tmp_path: Path) -> None:
    """
    An error is shown when the command is a non-executable file.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    not_executable_command = tmp_path / "non_executable"
    not_executable_command.touch()
    not_executable_command_with_args = (
        f"{not_executable_command.as_posix()} --help"
    )
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            x = 2 + 2
            assert x == 4
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--command",
        not_executable_command_with_args,
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code != 0
    expected_stderr = (
        f"{fg.red}Error running command '{not_executable_command.as_posix()}':"
    )
    assert result.stderr.startswith(expected_stderr)


def test_multiple_languages(tmp_path: Path) -> None:
    """
    It is possible to run a command against multiple code blocks in a document
    with different languages.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            x = 2 + 2
            assert x == 4

        .. code-block:: javascript

            var y = 3 + 3;
            console.assert(y === 6);
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--no-pad-file",
        "--language",
        "python",
        "--language",
        "javascript",
        "--command",
        "cat",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
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
    By default, the next code block after a 'skip doccmd: next' comment in a
    rST document is not run.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

           block_1

        .. skip doccmd[all]: next

        .. code-block:: python

            block_2

        .. code-block:: python

            block_3
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--no-pad-file",
        "--language",
        "python",
        "--command",
        "cat",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
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


@pytest.mark.parametrize(
    argnames=("fail_on_parse_error_options", "expected_exit_code"),
    argvalues=[
        ([], 0),
        (["--fail-on-parse-error"], 1),
    ],
)
def test_skip_no_arguments(
    tmp_path: Path,
    fail_on_parse_error_options: Sequence[str],
    expected_exit_code: int,
) -> None:
    """
    An error is shown if a skip is given with no arguments.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. skip doccmd[all]:

        .. code-block:: python

            block_2
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        *fail_on_parse_error_options,
        "--no-pad-file",
        "--language",
        "python",
        "--command",
        "cat",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == expected_exit_code, (
        result.stdout,
        result.stderr,
    )
    expected_stderr = textwrap.dedent(
        text=f"""\
        {fg.red}Could not parse {rst_file}: missing arguments to skip doccmd[all]{reset}
        """,  # noqa: E501
    )

    assert result.stdout == ""
    assert result.stderr == expected_stderr


@pytest.mark.parametrize(
    argnames=("fail_on_parse_error_options", "expected_exit_code"),
    argvalues=[
        ([], 0),
        (["--fail-on-parse-error"], 1),
    ],
)
def test_skip_bad_arguments(
    tmp_path: Path,
    fail_on_parse_error_options: Sequence[str],
    expected_exit_code: int,
) -> None:
    """
    An error is shown if a skip is given with bad arguments.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. skip doccmd[all]: !!!

        .. code-block:: python

            block_2
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        *fail_on_parse_error_options,
        "--no-pad-file",
        "--language",
        "python",
        "--command",
        "cat",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == expected_exit_code, (
        result.stdout,
        result.stderr,
    )
    expected_stderr = textwrap.dedent(
        text=f"""\
        {fg.red}Could not parse {rst_file}: malformed arguments to skip doccmd[all]: '!!!'{reset}
        """,  # noqa: E501
    )

    assert result.stdout == ""
    assert result.stderr == expected_stderr


def test_custom_skip_markers_rst(tmp_path: Path) -> None:
    """
    The next code block after a custom skip marker comment in a rST document is
    not run.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    skip_marker = uuid.uuid4().hex
    content = textwrap.dedent(
        text=f"""\
        .. code-block:: python

            block_1

        .. skip doccmd[{skip_marker}]: next

        .. code-block:: python

            block_2

        .. code-block:: python

            block_3
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--no-pad-file",
        "--language",
        "python",
        "--skip-marker",
        skip_marker,
        "--command",
        "cat",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
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
    By default, the next code block after a 'skip doccmd: next' comment in a
    MyST document is not run.
    """
    runner = CliRunner()
    myst_file = tmp_path / "example.md"
    content = textwrap.dedent(
        text="""\
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
        """,
    )
    myst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--no-pad-file",
        "--language",
        "python",
        "--command",
        "cat",
        str(object=myst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
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
    runner = CliRunner()
    myst_file = tmp_path / "example.md"
    skip_marker = uuid.uuid4().hex
    content = textwrap.dedent(
        text=f"""\
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
        """,
    )
    myst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--no-pad-file",
        "--language",
        "python",
        "--skip-marker",
        skip_marker,
        "--command",
        "cat",
        str(object=myst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
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
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    skip_marker_1 = uuid.uuid4().hex
    skip_marker_2 = uuid.uuid4().hex
    content = textwrap.dedent(
        text=f"""\
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
        """,
    )
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
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
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
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    skip_marker_1 = uuid.uuid4().hex
    skip_marker_2 = uuid.uuid4().hex
    content = textwrap.dedent(
        text="""\
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
        """,
    )
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
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
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
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    skip_marker = uuid.uuid4().hex
    content = textwrap.dedent(
        text=f"""\
        .. code-block:: python

            block_1

        .. skip doccmd[{skip_marker}]: next

        .. code-block:: python

            block_2

        .. skip doccmd[{skip_marker}]: next

        .. code-block:: python

            block_3
        """,
    )
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
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
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
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    skip_marker = "all"
    content = textwrap.dedent(
        text=f"""\
        .. code-block:: python

            block_1

        .. skip doccmd[{skip_marker}]: next

        .. code-block:: python

            block_2

        .. skip doccmd[{skip_marker}]: next

        .. code-block:: python

            block_3
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--no-pad-file",
        "--language",
        "python",
        "--skip-marker",
        skip_marker,
        "--command",
        "cat",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    expected_output = textwrap.dedent(
        text="""\
        block_1
        """,
    )

    assert result.stdout == expected_output
    assert result.stderr == ""


def test_skip_multiple(tmp_path: Path) -> None:
    """
    It is possible to mark a code block as to be skipped by multiple markers.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    skip_marker_1 = uuid.uuid4().hex
    skip_marker_2 = uuid.uuid4().hex
    content = textwrap.dedent(
        text=f"""\
        .. code-block:: python

            block_1

        .. skip doccmd[{skip_marker_1}]: next
        .. skip doccmd[{skip_marker_2}]: next

        .. code-block:: python

            block_2
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--no-pad-file",
        "--language",
        "python",
        "--skip-marker",
        skip_marker_1,
        "--command",
        "cat",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    expected_output = textwrap.dedent(
        text="""\
        block_1
        """,
    )

    assert result.stdout == expected_output
    assert result.stderr == ""

    arguments = [
        "--no-pad-file",
        "--language",
        "python",
        "--skip-marker",
        skip_marker_2,
        "--command",
        "cat",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    expected_output = textwrap.dedent(
        text="""\
        block_1
        """,
    )

    assert result.stdout == expected_output
    assert result.stderr == ""


def test_bad_skips(tmp_path: Path) -> None:
    """
    Bad skip orders are flagged.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    skip_marker_1 = uuid.uuid4().hex
    content = textwrap.dedent(
        text=f"""\
        .. skip doccmd[{skip_marker_1}]: end

        .. code-block:: python

            block_2
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--no-pad-file",
        "--language",
        "python",
        "--skip-marker",
        skip_marker_1,
        "--command",
        "cat",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code != 0, (result.stdout, result.stderr)
    expected_stderr = textwrap.dedent(
        text=f"""\
        {fg.red}Error running command 'cat': 'skip doccmd[{skip_marker_1}]: end' must follow 'skip doccmd[{skip_marker_1}]: start'{reset}
        """,  # noqa: E501
    )

    assert result.stdout == ""
    assert result.stderr == expected_stderr


def test_empty_file(tmp_path: Path) -> None:
    """
    No error is shown when an empty file is given.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    rst_file.touch()
    arguments = [
        "--no-pad-file",
        "--language",
        "python",
        "--command",
        "cat",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert result.stdout == ""
    assert result.stderr == ""


@pytest.mark.parametrize(
    argnames=("source_newline", "expect_crlf", "expect_cr", "expect_lf"),
    argvalues=[
        ("\n", False, False, True),
        ("\r\n", True, True, True),
        ("\r", False, True, False),
    ],
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
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            block_1
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8", newline=source_newline)
    arguments = [
        "--no-pad-file",
        "--language",
        "python",
        "--command",
        "cat",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
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
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        ```python
        print("In simple markdown code block")
        ```

        ```{code-block} python
        print("In MyST code-block")
        ```
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--command",
        "cat",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
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
    runner = CliRunner()
    document_file = tmp_path / ("example" + extension)
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            x = 2 + 2
            assert x == 4
        """,
    )
    document_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--command",
        "cat",
        str(object=document_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
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


def test_custom_rst_file_suffixes(tmp_path: Path) -> None:
    """
    ReStructuredText files with custom suffixes are recognized.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.customrst"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            x = 1
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    rst_file_2 = tmp_path / "example.customrst2"
    content_2 = """\
    .. code-block:: python

        x = 2
    """
    rst_file_2.write_text(data=content_2, encoding="utf-8")
    arguments = [
        "--no-pad-file",
        "--language",
        "python",
        "--command",
        "cat",
        "--rst-extension",
        ".customrst",
        "--rst-extension",
        ".customrst2",
        str(object=rst_file),
        str(object=rst_file_2),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    expected_output = textwrap.dedent(
        text="""\
        x = 1
        x = 2
        """,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert result.stdout == expected_output
    assert result.stderr == ""


def test_custom_myst_file_suffixes(tmp_path: Path) -> None:
    """
    MyST files with custom suffixes are recognized.
    """
    runner = CliRunner()
    myst_file = tmp_path / "example.custommyst"
    content = textwrap.dedent(
        text="""\
        ```python
        x = 1
        ```
        """,
    )
    myst_file.write_text(data=content, encoding="utf-8")
    myst_file_2 = tmp_path / "example.custommyst2"
    content_2 = """\
    ```python
    x = 2
    ```
    """
    myst_file_2.write_text(data=content_2, encoding="utf-8")
    arguments = [
        "--no-pad-file",
        "--language",
        "python",
        "--command",
        "cat",
        "--myst-extension",
        ".custommyst",
        "--myst-extension",
        ".custommyst2",
        str(object=myst_file),
        str(object=myst_file_2),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    expected_output = textwrap.dedent(
        text="""\
        x = 1
        x = 2
        """,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert result.stdout == expected_output
    assert result.stderr == ""


@pytest.mark.parametrize(
    argnames=("options", "expected_output"),
    argvalues=[
        # We cannot test the actual behavior of using a pseudo-terminal,
        # as CI (e.g. GitHub Actions) does not support it.
        # Therefore we do not test the `--use-pty yes` option.
        (["--use-pty", "no"], "stdout is not a terminal."),
        # We are not really testing the detection mechanism.
        (["--use-pty", "detect"], "stdout is not a terminal."),
    ],
    ids=["use-pty-no", "use-pty-detect"],
)
def test_pty(
    tmp_path: Path,
    options: Sequence[str],
    expected_output: str,
) -> None:
    """
    Test options for using pseudo-terminal.
    """
    runner = CliRunner()
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
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            block_1
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        *options,
        "--no-pad-file",
        "--language",
        "python",
        "--command",
        f"{Path(sys.executable).as_posix()} {script.as_posix()}",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert result.stderr == ""
    assert result.stdout.strip() == expected_output


@pytest.mark.parametrize(
    argnames="option",
    argvalues=["--rst-extension", "--myst-extension"],
)
def test_source_given_extension_no_leading_period(
    tmp_path: Path,
    option: str,
) -> None:
    """
    An error is shown when a given source file extension is given with no
    leading period.
    """
    runner = CliRunner()
    source_file = tmp_path / "example.rst"
    content = "Hello world"
    source_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--command",
        "cat",
        option,
        "customrst",
        str(object=source_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code != 0, (result.stdout, result.stderr)
    expected_stderr = textwrap.dedent(
        text=f"""\
            Usage: doccmd [OPTIONS] [DOCUMENT_PATHS]...
            Try 'doccmd --help' for help.

            Error: Invalid value for '{option}': 'customrst' does not start with a '.'.
            """,  # noqa: E501
    )
    assert result.stdout == ""
    assert result.stderr == expected_stderr


def test_overlapping_extensions(tmp_path: Path) -> None:
    """
    An error is shown if there are overlapping extensions between --rst-
    extension and --myst-extension.
    """
    runner = CliRunner()
    source_file = tmp_path / "example.custom"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            x = 1
        """,
    )
    source_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--command",
        "cat",
        "--rst-extension",
        ".custom",
        "--myst-extension",
        ".custom",
        "--rst-extension",
        ".custom2",
        "--myst-extension",
        ".custom2",
        str(object=source_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code != 0, (result.stdout, result.stderr)
    expected_stderr = textwrap.dedent(
        text="""\
            Usage: doccmd [OPTIONS] [DOCUMENT_PATHS]...
            Try 'doccmd --help' for help.

            Error: Overlapping suffixes between MyST and reStructuredText: .custom, .custom2.
            """,  # noqa: E501
    )
    assert result.stdout == ""
    assert result.stderr == expected_stderr


def test_overlapping_extensions_dot(tmp_path: Path) -> None:
    """
    No error is shown if multiple extension types are '.'.
    """
    runner = CliRunner()
    source_file = tmp_path / "example.custom"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            x = 1
        """,
    )
    source_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--no-pad-file",
        "--command",
        "cat",
        "--rst-extension",
        ".",
        "--myst-extension",
        ".",
        "--rst-extension",
        ".custom",
        str(object=source_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    expected_output = textwrap.dedent(
        text="""\
        x = 1
        """,
    )
    assert result.stdout == expected_output
    assert result.stderr == ""


def test_markdown(tmp_path: Path) -> None:
    """
    It is possible to run a command against a Markdown file.
    """
    runner = CliRunner()
    source_file = tmp_path / "example.md"
    content = textwrap.dedent(
        text="""\
        % skip doccmd[all]: next

        ```python
            x = 1
        ```

        <!--- skip doccmd[all]: next -->

        ```python
            x = 2
        ```

        ```python
            x = 3
        ```
        """,
    )
    source_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--no-pad-file",
        "--command",
        "cat",
        "--rst-extension",
        ".",
        "--myst-extension",
        ".",
        "--markdown-extension",
        ".md",
        str(object=source_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    expected_output = textwrap.dedent(
        text="""\
        x = 1
        x = 3
        """,
    )
    # The first skip directive is not run as "%" is not a valid comment in
    # Markdown.
    #
    # The second skip directive is run as `<!--- skip doccmd[all]:
    # next -->` is a valid comment in Markdown.
    #
    # The code block after the second skip directive is run as it is
    # a valid Markdown code block.
    assert result.stdout == expected_output
    assert result.stderr == ""


def test_directory(tmp_path: Path) -> None:
    """
    All source files in a given directory are worked on.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    rst_content = textwrap.dedent(
        text="""\
        .. code-block:: python

            rst_1_block
        """,
    )
    rst_file.write_text(data=rst_content, encoding="utf-8")
    md_file = tmp_path / "example.md"
    md_content = textwrap.dedent(
        text="""\
        ```python
        md_1_block
        ```
        """,
    )
    md_file.write_text(data=md_content, encoding="utf-8")
    sub_directory = tmp_path / "subdir"
    sub_directory.mkdir()
    rst_file_in_sub_directory = sub_directory / "subdir_example.rst"
    subdir_rst_content = textwrap.dedent(
        text="""\
        .. code-block:: python

            rst_subdir_1_block
        """,
    )
    rst_file_in_sub_directory.write_text(
        data=subdir_rst_content,
        encoding="utf-8",
    )

    sub_directory_with_known_file_extension = sub_directory / "subdir.rst"
    sub_directory_with_known_file_extension.mkdir()

    arguments = [
        "--language",
        "python",
        "--no-pad-file",
        "--command",
        "cat",
        str(object=tmp_path),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == 0, result.stderr
    expected_output = textwrap.dedent(
        text="""\
        md_1_block
        rst_1_block
        rst_subdir_1_block
        """,
    )

    assert result.stdout == expected_output
    assert result.stderr == ""


def test_de_duplication_source_files_and_dirs(tmp_path: Path) -> None:
    """
    If a file is given which is within a directory that is also given, the file
    is de-duplicated.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    rst_content = textwrap.dedent(
        text="""\
        .. code-block:: python

            rst_1_block
        """,
    )
    rst_file.write_text(data=rst_content, encoding="utf-8")
    sub_directory = tmp_path / "subdir"
    sub_directory.mkdir()
    rst_file_in_sub_directory = sub_directory / "subdir_example.rst"
    subdir_rst_content = textwrap.dedent(
        text="""\
        .. code-block:: python

            rst_subdir_1_block
        """,
    )
    rst_file_in_sub_directory.write_text(
        data=subdir_rst_content,
        encoding="utf-8",
    )

    arguments = [
        "--language",
        "python",
        "--no-pad-file",
        "--command",
        "cat",
        str(object=tmp_path),
        str(object=sub_directory),
        str(object=rst_file_in_sub_directory),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == 0, result.stderr
    expected_output = textwrap.dedent(
        text="""\
        rst_1_block
        rst_subdir_1_block
        """,
    )

    assert result.stdout == expected_output
    assert result.stderr == ""


def test_max_depth(tmp_path: Path) -> None:
    """
    The --max-depth option limits the depth of directories to search for files.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    rst_content = textwrap.dedent(
        text="""\
        .. code-block:: python

            rst_1_block
        """,
    )
    rst_file.write_text(data=rst_content, encoding="utf-8")

    sub_directory = tmp_path / "subdir"
    sub_directory.mkdir()
    rst_file_in_sub_directory = sub_directory / "subdir_example.rst"
    subdir_rst_content = textwrap.dedent(
        text="""\
        .. code-block:: python

            rst_subdir_1_block
        """,
    )
    rst_file_in_sub_directory.write_text(
        data=subdir_rst_content,
        encoding="utf-8",
    )

    sub_sub_directory = sub_directory / "subsubdir"
    sub_sub_directory.mkdir()
    rst_file_in_sub_sub_directory = sub_sub_directory / "subsubdir_example.rst"
    subsubdir_rst_content = textwrap.dedent(
        text="""\
        .. code-block:: python

            rst_subsubdir_1_block
        """,
    )
    rst_file_in_sub_sub_directory.write_text(
        data=subsubdir_rst_content,
        encoding="utf-8",
    )

    arguments = [
        "--language",
        "python",
        "--no-pad-file",
        "--command",
        "cat",
        "--max-depth",
        "1",
        str(object=tmp_path),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == 0, result.stderr
    expected_output = textwrap.dedent(
        text="""\
        rst_1_block
        """,
    )

    assert result.stdout == expected_output
    assert result.stderr == ""

    arguments = [
        "--language",
        "python",
        "--no-pad-file",
        "--command",
        "cat",
        "--max-depth",
        "2",
        str(object=tmp_path),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == 0, result.stderr
    expected_output = textwrap.dedent(
        text="""\
        rst_1_block
        rst_subdir_1_block
        """,
    )

    assert result.stdout == expected_output
    assert result.stderr == ""

    arguments = [
        "--language",
        "python",
        "--no-pad-file",
        "--command",
        "cat",
        "--max-depth",
        "3",
        str(object=tmp_path),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == 0, result.stderr
    expected_output = textwrap.dedent(
        text="""\
        rst_1_block
        rst_subdir_1_block
        rst_subsubdir_1_block
        """,
    )

    assert result.stdout == expected_output
    assert result.stderr == ""


def test_exclude_files_from_recursed_directories(tmp_path: Path) -> None:
    """
    Files with names matching the exclude pattern are not processed when
    recursing directories.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    rst_content = textwrap.dedent(
        text="""\
        .. code-block:: python

            rst_1_block
        """,
    )
    rst_file.write_text(data=rst_content, encoding="utf-8")

    sub_directory = tmp_path / "subdir"
    sub_directory.mkdir()
    rst_file_in_sub_directory = sub_directory / "subdir_example.rst"
    subdir_rst_content = textwrap.dedent(
        text="""\
        .. code-block:: python

            rst_subdir_1_block
        """,
    )
    rst_file_in_sub_directory.write_text(
        data=subdir_rst_content,
        encoding="utf-8",
    )

    excluded_file = sub_directory / "exclude_me.rst"
    excluded_content = textwrap.dedent(
        text="""\
        .. code-block:: python

            excluded_block
        """,
    )
    excluded_file.write_text(data=excluded_content, encoding="utf-8")

    arguments = [
        "--language",
        "python",
        "--no-pad-file",
        "--command",
        "cat",
        "--exclude",
        "exclude_*e.*",
        str(object=tmp_path),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == 0, result.stderr
    expected_output = textwrap.dedent(
        text="""\
        rst_1_block
        rst_subdir_1_block
        """,
    )

    assert result.stdout == expected_output
    assert result.stderr == ""


def test_multiple_exclude_patterns(tmp_path: Path) -> None:
    """
    Files matching any of the exclude patterns are not processed when recursing
    directories.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    rst_content = textwrap.dedent(
        text="""\
        .. code-block:: python

            rst_1_block
        """,
    )
    rst_file.write_text(data=rst_content, encoding="utf-8")

    sub_directory = tmp_path / "subdir"
    sub_directory.mkdir()
    rst_file_in_sub_directory = sub_directory / "subdir_example.rst"
    subdir_rst_content = textwrap.dedent(
        text="""\
        .. code-block:: python

            rst_subdir_1_block
        """,
    )
    rst_file_in_sub_directory.write_text(
        data=subdir_rst_content,
        encoding="utf-8",
    )

    excluded_file_1 = sub_directory / "exclude_me.rst"
    excluded_content_1 = """\
    .. code-block:: python

        excluded_block_1
    """
    excluded_file_1.write_text(data=excluded_content_1, encoding="utf-8")

    excluded_file_2 = sub_directory / "ignore_me.rst"
    excluded_content_2 = """\
    .. code-block:: python

        excluded_block_2
    """
    excluded_file_2.write_text(data=excluded_content_2, encoding="utf-8")

    arguments = [
        "--language",
        "python",
        "--no-pad-file",
        "--command",
        "cat",
        "--exclude",
        "exclude_*e.*",
        "--exclude",
        "ignore_*e.*",
        str(object=tmp_path),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == 0, result.stderr
    expected_output = textwrap.dedent(
        text="""\
        rst_1_block
        rst_subdir_1_block
        """,
    )

    assert result.stdout == expected_output
    assert result.stderr == ""


@pytest.mark.parametrize(
    argnames=("fail_on_parse_error_options", "expected_exit_code"),
    argvalues=[
        ([], 0),
        (["--fail-on-parse-error"], 1),
    ],
)
def test_lexing_exception(
    tmp_path: Path,
    fail_on_parse_error_options: Sequence[str],
    expected_exit_code: int,
) -> None:
    """
    Lexing exceptions are handled when an invalid source file is given.
    """
    runner = CliRunner()
    source_file = tmp_path / "invalid_example.md"
    # Lexing error as there is a hyphen in the comment
    # or... because of the word code!
    invalid_content = textwrap.dedent(
        text="""\
        <!-- code -->
        """,
    )
    source_file.write_text(data=invalid_content, encoding="utf-8")
    arguments = [
        *fail_on_parse_error_options,
        "--language",
        "python",
        "--command",
        "cat",
        str(object=source_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == expected_exit_code, (
        result.stdout,
        result.stderr,
    )
    expected_stderr = textwrap.dedent(
        text=f"""\
        {fg.red}Could not parse {source_file}: Could not find end of '<!-- code -->\\n', starting at line 1, column 1, looking for '(?:(?<=\\n))?--+>' in {source_file}:
        ''{reset}
        """,  # noqa: E501
    )
    assert result.stderr == expected_stderr


@pytest.mark.parametrize(
    argnames="file_padding_options",
    argvalues=[
        [],
        ["--no-pad-file"],
    ],
)
@pytest.mark.parametrize(
    argnames=("group_marker", "group_marker_options"),
    argvalues=[
        ("all", []),
        ("custom-marker", ["--group-marker", "custom-marker"]),
    ],
)
@pytest.mark.parametrize(
    argnames=("group_padding_options", "expect_padding"),
    argvalues=[
        ([], True),
        (["--no-pad-groups"], False),
    ],
)
def test_group_blocks(
    *,
    tmp_path: Path,
    file_padding_options: Sequence[str],
    group_marker: str,
    group_marker_options: Sequence[str],
    group_padding_options: Sequence[str],
    expect_padding: bool,
) -> None:
    """It is possible to group some blocks together.

    Code blocks between a group start and end marker are concatenated
    and passed as a single input to the command.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    script = tmp_path / "print_underlined.py"
    content = textwrap.dedent(
        text=f"""\
        .. code-block:: python

            block_1

        .. group doccmd[{group_marker}]: start

        .. code-block:: python

            block_group_1

        .. code-block:: python

            block_group_2

        .. group doccmd[{group_marker}]: end

        .. code-block:: python

            block_3
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")

    print_underlined_script = textwrap.dedent(
        text="""\
        import sys
        import pathlib

        # We strip here so that we don't have to worry about
        # the file padding.
        print(pathlib.Path(sys.argv[1]).read_text().strip())
        print("-------")
        """,
    )
    script.write_text(data=print_underlined_script, encoding="utf-8")

    arguments = [
        *file_padding_options,
        *group_padding_options,
        *group_marker_options,
        "--language",
        "python",
        "--command",
        f"{Path(sys.executable).as_posix()} {script.as_posix()}",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    # The expected output is that the content outside the group remains
    # unchanged, while the contents inside the group are merged.
    if expect_padding:
        expected_output = textwrap.dedent(
            text="""\
            block_1
            -------
            block_group_1



            block_group_2
            -------
            block_3
            -------
            """,
        )
    else:
        expected_output = textwrap.dedent(
            text="""\
            block_1
            -------
            block_group_1

            block_group_2
            -------
            block_3
            -------
            """,
        )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert result.stdout == expected_output
    assert result.stderr == ""


@pytest.mark.parametrize(
    argnames=(
        "fail_on_group_write_options",
        "expected_exit_code",
        "message_colour",
    ),
    argvalues=[
        ([], 1, fg.red),
        (["--fail-on-group-write"], 1, fg.red),
        (["--no-fail-on-group-write"], 0, fg.yellow),
    ],
)
def test_modify_file_single_group_block(
    *,
    tmp_path: Path,
    fail_on_group_write_options: Sequence[str],
    expected_exit_code: int,
    message_colour: Graphic,
) -> None:
    """
    Commands in groups cannot modify files in single grouped blocks.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. group doccmd[all]: start

        .. code-block:: python

            a = 1
            b = 1
            c = 1

        .. group doccmd[all]: end
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    modify_code_script = textwrap.dedent(
        text="""\
        #!/usr/bin/env python

        import sys

        with open(sys.argv[1], "w") as file:
            file.write("foobar")
        """,
    )
    modify_code_file = tmp_path / "modify_code.py"
    modify_code_file.write_text(data=modify_code_script, encoding="utf-8")
    arguments = [
        *fail_on_group_write_options,
        "--language",
        "python",
        "--command",
        f"{Path(sys.executable).as_posix()} {modify_code_file.as_posix()}",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == expected_exit_code, (
        result.stdout,
        result.stderr,
    )
    new_content = rst_file.read_text(encoding="utf-8")
    expected_content = content
    assert new_content == expected_content

    expected_stderr = textwrap.dedent(
        text=f"""\
            {message_colour}Writing to a group is not supported.

            A command modified the contents of examples in the group ending on line 3 in {rst_file.as_posix()}.

            Diff:

            --- original

            +++ modified

            @@ -1,3 +1 @@

            -a = 1
            -b = 1
            -c = 1
            +foobar{reset}
            """,  # noqa: E501
    )
    assert result.stderr == expected_stderr


@pytest.mark.parametrize(
    argnames=(
        "fail_on_group_write_options",
        "expected_exit_code",
        "message_colour",
    ),
    argvalues=[
        ([], 1, fg.red),
        (["--fail-on-group-write"], 1, fg.red),
        (["--no-fail-on-group-write"], 0, fg.yellow),
    ],
)
def test_modify_file_multiple_group_blocks(
    *,
    tmp_path: Path,
    fail_on_group_write_options: Sequence[str],
    expected_exit_code: int,
    message_colour: Graphic,
) -> None:
    """
    Commands in groups cannot modify files in multiple grouped commands.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. group doccmd[all]: start

        .. code-block:: python

            a = 1
            b = 1

        .. code-block:: python

            c = 1

        .. group doccmd[all]: end
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    modify_code_script = textwrap.dedent(
        text="""\
        #!/usr/bin/env python

        import sys

        with open(sys.argv[1], "w") as file:
            file.write("foobar")
        """,
    )
    modify_code_file = tmp_path / "modify_code.py"
    modify_code_file.write_text(data=modify_code_script, encoding="utf-8")
    arguments = [
        *fail_on_group_write_options,
        "--language",
        "python",
        "--command",
        f"{Path(sys.executable).as_posix()} {modify_code_file.as_posix()}",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == expected_exit_code, (
        result.stdout,
        result.stderr,
    )
    new_content = rst_file.read_text(encoding="utf-8")
    expected_content = content
    assert new_content == expected_content

    expected_stderr = textwrap.dedent(
        text=f"""\
            {message_colour}Writing to a group is not supported.

            A command modified the contents of examples in the group ending on line 3 in {rst_file.as_posix()}.

            Diff:

            --- original

            +++ modified

            @@ -1,6 +1 @@

            -a = 1
            -b = 1
            -
            -
            -
            -c = 1
            +foobar{reset}
            """,  # noqa: E501
    )
    assert result.stderr == expected_stderr


def test_jinja2(*, tmp_path: Path) -> None:
    """
    It is possible to run commands against sphinx-jinja2 blocks.
    """
    runner = CliRunner()
    source_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. jinja::

            {% set x = 1 %}
            {{ x }}

            .. Nested code block

            .. code-block:: python

               x = 2
               print(x)
        """,
    )
    source_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--sphinx-jinja2",
        "--command",
        "cat",
        str(object=source_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    expected_output = textwrap.dedent(
        text="""\


        {% set x = 1 %}
        {{ x }}

        .. Nested code block

        .. code-block:: python

           x = 2
           print(x)
        """
    )
    assert result.stdout == expected_output
    assert result.stderr == ""


def test_empty_language_given(*, tmp_path: Path) -> None:
    """
    An error is shown when an empty language is given.
    """
    runner = CliRunner()
    source_file = tmp_path / "example.rst"
    content = ""
    source_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--command",
        "cat",
        "--language",
        "",
        str(object=source_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code != 0, (result.stdout, result.stderr)
    expected_stderr = textwrap.dedent(
        text="""\
            Usage: doccmd [OPTIONS] [DOCUMENT_PATHS]...
            Try 'doccmd --help' for help.

            Error: Invalid value for '-l' / '--language': This value cannot be empty.
            """,  # noqa: E501
    )
    assert result.stdout == ""
    assert result.stderr == expected_stderr


def test_continue_on_error_multiple_files(tmp_path: Path) -> None:
    """With --continue-on-error, execution continues across files when errors
    occur.

    The tool collects all errors and exits with the highest error code.
    """
    runner = CliRunner()
    highest_exit_code = 42
    lowest_exit_code = 7

    rst_file1 = tmp_path / "example1.rst"
    content1 = textwrap.dedent(
        text=f"""\
        .. code-block:: python

            import sys
            sys.exit({highest_exit_code})
        """,
    )
    rst_file1.write_text(data=content1, encoding="utf-8")

    rst_file2 = tmp_path / "example2.rst"
    content2 = textwrap.dedent(
        text="""\
        .. code-block:: python

            x = 2 + 2
            assert x == 4
        """,
    )
    rst_file2.write_text(data=content2, encoding="utf-8")

    rst_file3 = tmp_path / "example3.rst"
    content3 = textwrap.dedent(
        text=f"""\
        .. code-block:: python

            import sys
            sys.exit({lowest_exit_code})
        """,
    )
    rst_file3.write_text(data=content3, encoding="utf-8")

    arguments = [
        "--language",
        "python",
        "--command",
        Path(sys.executable).as_posix(),
        "--continue-on-error",
        str(object=rst_file1),
        str(object=rst_file2),
        str(object=rst_file3),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == highest_exit_code, (
        result.stdout,
        result.stderr,
    )


def test_continue_on_error_encoding_error(tmp_path: Path) -> None:
    """
    With --continue-on-error and --fail-on-parse-error, encoding errors are
    collected and execution continues.
    """
    runner = CliRunner()

    rst_file1 = tmp_path / "bad_encoding.rst"
    rst_file1.write_bytes(data=Path(sys.executable).read_bytes())

    rst_file2 = tmp_path / "valid.rst"
    content2 = textwrap.dedent(
        text="""\
        .. code-block:: python

            x = 1 + 1
        """,
    )
    rst_file2.write_text(data=content2, encoding="utf-8")

    arguments = [
        "--fail-on-parse-error",
        "--continue-on-error",
        "--language",
        "python",
        "--command",
        "cat",
        str(object=rst_file1),
        str(object=rst_file2),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == 1, (result.stdout, result.stderr)
    expected_stderr = (
        f"{fg.red}Could not determine encoding for {rst_file1}.{reset}\n"
    )
    assert result.stderr == expected_stderr


def test_continue_on_error_parse_error(tmp_path: Path) -> None:
    """
    With --continue-on-error and --fail-on-parse-error, parse errors are
    collected and execution continues.
    """
    runner = CliRunner()

    source_file1 = tmp_path / "invalid_example.md"
    invalid_content = textwrap.dedent(
        text="""\
        <!-- code -->
        """,
    )
    source_file1.write_text(data=invalid_content, encoding="utf-8")

    source_file2 = tmp_path / "valid.rst"
    content2 = textwrap.dedent(
        text="""\
        .. code-block:: python

            x = 1 + 1
        """,
    )
    source_file2.write_text(data=content2, encoding="utf-8")

    arguments = [
        "--fail-on-parse-error",
        "--continue-on-error",
        "--language",
        "python",
        "--command",
        "cat",
        str(object=source_file1),
        str(object=source_file2),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == 1, (result.stdout, result.stderr)
    expected_stderr = textwrap.dedent(
        text=f"""\
        {fg.red}Could not parse {source_file1}: Could not find end of '<!-- code -->\\n', starting at line 1, column 1, looking for '(?:(?<=\\n))?--+>' in {source_file1}:
        ''{reset}
        """,  # noqa: E501
    )
    assert result.stderr == expected_stderr


def test_continue_on_error_group_write_error(tmp_path: Path) -> None:
    """
    With --continue-on-error and --fail-on-group-write, group write errors are
    collected and execution continues.
    """
    runner = CliRunner()

    rst_file1 = tmp_path / "group_modified.rst"
    content1 = textwrap.dedent(
        text="""\
        .. group doccmd[all]: start

        .. code-block:: python

            print("Hello")

        .. group doccmd[all]: end
        """,
    )
    rst_file1.write_text(data=content1, encoding="utf-8")

    rst_file2 = tmp_path / "valid.rst"
    content2 = textwrap.dedent(
        text="""\
        .. code-block:: python

            x = 1 + 1
        """,
    )
    rst_file2.write_text(data=content2, encoding="utf-8")

    modify_code_script = textwrap.dedent(
        text="""\
        #!/usr/bin/env python

        import sys

        with open(sys.argv[1], "w") as file:
            file.write("modified")
        """,
    )
    modify_code_file = tmp_path / "modify_code.py"
    modify_code_file.write_text(data=modify_code_script, encoding="utf-8")

    arguments = [
        "--fail-on-group-write",
        "--continue-on-error",
        "--language",
        "python",
        "--command",
        f"{Path(sys.executable).as_posix()} {modify_code_file.as_posix()}",
        str(object=rst_file1),
        str(object=rst_file2),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == 1, (result.stdout, result.stderr)


def test_continue_on_error_command_not_found(tmp_path: Path) -> None:
    """With --continue-on-error, OSError (command not found) is collected and
    execution continues.

    This covers the case where _EvaluateError is raised with a reason.
    """
    runner = CliRunner()

    rst_file1 = tmp_path / "bad_command.rst"
    non_existent_command = uuid.uuid4().hex
    content1 = textwrap.dedent(
        text="""\
        .. code-block:: python

            x = 1 + 1
        """,
    )
    rst_file1.write_text(data=content1, encoding="utf-8")

    rst_file2 = tmp_path / "valid.rst"
    content2 = textwrap.dedent(
        text="""\
        .. code-block:: python

            y = 2 + 2
        """,
    )
    rst_file2.write_text(data=content2, encoding="utf-8")

    arguments = [
        "--continue-on-error",
        "--language",
        "python",
        "--command",
        non_existent_command,
        str(object=rst_file1),
        str(object=rst_file2),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code != 0, (result.stdout, result.stderr)
    assert f"Error running command '{non_existent_command}'" in result.stderr


def test_continue_on_error_vs_default_behavior(tmp_path: Path) -> None:
    """Without --continue-on-error, execution stops at first error.

    With --continue-on-error, it continues.
    """
    runner = CliRunner()
    exit_code_42 = 42
    exit_code_7 = 7

    rst_file1 = tmp_path / "example1.rst"
    content1 = textwrap.dedent(
        text=f"""\
        .. code-block:: python

            import sys
            sys.exit({exit_code_42})
        """,
    )
    rst_file1.write_text(data=content1, encoding="utf-8")

    rst_file2 = tmp_path / "example2.rst"
    content2 = textwrap.dedent(
        text=f"""\
        .. code-block:: python

            import sys
            sys.exit({exit_code_7})
        """,
    )
    rst_file2.write_text(data=content2, encoding="utf-8")

    arguments_without_continue = [
        "--language",
        "python",
        "--command",
        Path(sys.executable).as_posix(),
        str(object=rst_file1),
        str(object=rst_file2),
    ]
    result_without_continue = runner.invoke(
        cli=main,
        args=arguments_without_continue,
        catch_exceptions=False,
        color=True,
    )
    assert result_without_continue.exit_code == exit_code_42, (
        result_without_continue.stdout,
        result_without_continue.stderr,
    )

    arguments_with_continue = [
        "--language",
        "python",
        "--command",
        Path(sys.executable).as_posix(),
        "--continue-on-error",
        str(object=rst_file1),
        str(object=rst_file2),
    ]
    result_with_continue = runner.invoke(
        cli=main,
        args=arguments_with_continue,
        catch_exceptions=False,
        color=True,
    )
    assert result_with_continue.exit_code == exit_code_42, (
        result_with_continue.stdout,
        result_with_continue.stderr,
    )


def test_value_error_without_continue_on_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    ValueError causes immediate exit when not using --continue-on-error.
    """
    from sybil.example import Example

    def mock_evaluate(self: Example) -> None:
        msg = "Mock error for testing"
        raise ValueError(msg)

    monkeypatch.setattr(Example, "evaluate", mock_evaluate)

    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            x = 2 + 2
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--command",
        "echo test",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == 1
    expected_stderr = f"{fg.red}Error running command 'echo':"
    assert result.stderr.startswith(expected_stderr)


def test_value_error_with_continue_on_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    ValueError is collected when using --continue-on-error.
    """
    from sybil.example import Example

    def mock_evaluate(self: Example) -> None:
        msg = "Mock error for testing"
        raise ValueError(msg)

    monkeypatch.setattr(Example, "evaluate", mock_evaluate)

    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            x = 2 + 2
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--command",
        "echo test",
        "--continue-on-error",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == 1
    expected_stderr = f"{fg.red}Error running command 'echo':"
    assert result.stderr.startswith(expected_stderr)
