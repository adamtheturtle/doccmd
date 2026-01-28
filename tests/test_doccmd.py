"""Tests for `doccmd`."""

import os
import re
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
    It is possible to run a command against a code block in a
    document.
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
    """Giving the same language twice does not run the command twice."""
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
    """An error is shown when a file does not exist."""
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
    """No error is given if a file is passed in which is not UTF-8."""
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
    """An error is shown when a file cannot be decoded."""
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
    It is possible to run a command against multiple code blocks in a
    document.
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
    """Languages not specified are not run."""
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
    """It is possible to not pad the file."""
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
    """It is possible to run a command against multiple files."""
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
    It is possible to run a command against multiple files of multiple
    types
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

        ```{code-cell} python
        print("In MyST code-cell")
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
        print("In MyST code-cell")
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
    """Commands (outside of groups) can modify files when allowed."""
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
    """The exit code of the first failure is propagated."""
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
    The file extension of the temporary file is appropriate for the
    language.
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
    It is possible to specify the file extension for created temporary
    files.
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
    An error is shown when a given temporary file extension is given
    with no
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
    """It is possible to specify a prefix for the temporary file."""
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


@pytest.mark.parametrize(
    argnames=("template", "expected_pattern"),
    argvalues=[
        pytest.param(
            "{prefix}_{unique}{suffix}",
            r"^doccmd_[a-f0-9]{4}\.py$",
            id="minimal-template",
        ),
        pytest.param(
            "test_{prefix}_{source}_line{line}_{unique}{suffix}",
            r"^test_doccmd_example_rst_line1_[a-f0-9]{4}\.py$",
            id="all-placeholders",
        ),
    ],
)
def test_custom_template(
    tmp_path: Path,
    template: str,
    expected_pattern: str,
) -> None:
    """Custom templates produce file names matching expected patterns."""
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
        "--temporary-file-name-template",
        template,
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
    assert re.match(pattern=expected_pattern, string=output_path.name)


def test_invalid_template_placeholder(tmp_path: Path) -> None:
    """An error is raised for invalid placeholders in the template."""
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
        "--temporary-file-name-template",
        "{prefix}_{invalid}{suffix}",
        "--command",
        "echo",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    expected_output = (
        "Usage: doccmd [OPTIONS] [DOCUMENT_PATHS]...\n"
        "Try 'doccmd --help' for help.\n"
        "\n"
        "Error: Invalid value for '--temporary-file-name-template': "
        "Invalid placeholder in template: 'invalid'. "
        "Valid placeholders are: {line, prefix, source, suffix, unique}.\n"
    )
    assert result.output == expected_output


@pytest.mark.parametrize(
    argnames="template",
    argvalues=[
        pytest.param("{prefix}_{unique}", id="missing-suffix"),
        pytest.param("{prefix}_{{suffix}}", id="escaped-suffix"),
        pytest.param("{prefix}_{unique}.txt", id="literal-extension"),
    ],
)
def test_template_requires_suffix_placeholder(
    tmp_path: Path,
    template: str,
) -> None:
    """An error is raised if the template does not use {suffix}."""
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
        "--temporary-file-name-template",
        template,
        "--command",
        "echo",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    expected_output = (
        "Usage: doccmd [OPTIONS] [DOCUMENT_PATHS]...\n"
        "Try 'doccmd --help' for help.\n"
        "\n"
        "Error: Invalid value for '--temporary-file-name-template': "
        "Template must contain '{suffix}' placeholder "
        "for the file extension.\n"
    )
    assert result.output == expected_output


@pytest.mark.parametrize(
    argnames="template",
    argvalues=[
        pytest.param("{prefix}_{suffix", id="unclosed-brace"),
        pytest.param("{prefix.foo}{suffix}", id="attribute-access"),
        pytest.param("{line[0]}{suffix}", id="item-access"),
    ],
)
def test_template_malformed_raises_error(
    tmp_path: Path,
    template: str,
) -> None:
    """An error is raised for malformed templates."""
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
        "--temporary-file-name-template",
        template,
        "--command",
        "echo",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )
    assert result.exit_code != 0
    # The exact Python error message varies, so check for the prefix
    expected_prefix = (
        "Usage: doccmd [OPTIONS] [DOCUMENT_PATHS]...\n"
        "Try 'doccmd --help' for help.\n"
        "\n"
        "Error: Invalid value for '--temporary-file-name-template': "
        "Malformed template:"
    )
    assert result.output.startswith(expected_prefix)


def test_temporary_file_includes_source_name(tmp_path: Path) -> None:
    """The temporary file name includes the sanitized source file name."""
    runner = CliRunner()
    # Use a filename with characters that get sanitized (dots and dashes)
    rst_file = tmp_path / "my-example.test.rst"
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
    # "my-example.test.rst" becomes "my_example_test_rst" in the filename,
    # along with the line number (code block at line 1)
    assert "my_example_test_rst" in output_path.name
    assert "_l1__" in output_path.name


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
    """Files given multiple times are de-duplicated."""
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


@pytest.mark.parametrize(
    argnames="worker_flag",
    argvalues=["--example-workers", "--document-workers"],
)
def test_workers_requires_no_write_to_file(
    tmp_path: Path,
    worker_flag: str,
) -> None:
    """Using workers>1 without --no-write-to-file is rejected."""
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
            worker_flag,
            "2",
            str(object=rst_file),
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == PARALLELISM_EXIT_CODE
    assert "--no-write-to-file" in result.stderr


@pytest.mark.parametrize(
    argnames="worker_flag",
    argvalues=["--example-workers", "--document-workers"],
)
def test_workers_runs_commands(
    tmp_path: Path,
    worker_flag: str,
) -> None:
    """
    Commands run successfully when workers>1 and --no-write-to-file is
    given.
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
            worker_flag,
            "2",
            str(object=rst_file),
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert "From the first block" in result.stdout
    assert "From the second block" in result.stdout


@pytest.mark.parametrize(
    argnames="worker_flag",
    argvalues=["--example-workers", "--document-workers"],
)
def test_workers_zero_requires_no_write_when_auto_parallel(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    worker_flag: str,
) -> None:
    """
    Workers=0 auto-detects CPUs and still requires --no-write-to-file
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
            worker_flag,
            "0",
            str(object=rst_file),
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == PARALLELISM_EXIT_CODE
    assert "--no-write-to-file" in result.stderr


@pytest.mark.parametrize(
    argnames="worker_flag",
    argvalues=["--example-workers", "--document-workers"],
)
def test_workers_zero_allows_running_when_cpu_is_single(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    worker_flag: str,
) -> None:
    """
    Workers=0 falls back to sequential execution when only one CPU is
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
            worker_flag,
            "0",
            str(object=rst_file),
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert "Only one CPU" in result.stdout


def test_cpu_count_returns_none(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When os.cpu_count() returns None, workers default to 1."""
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


@pytest.mark.parametrize(
    argnames="worker_flag",
    argvalues=["--example-workers", "--document-workers"],
)
def test_parallel_execution_error(
    tmp_path: Path,
    worker_flag: str,
) -> None:
    """Errors during parallel execution are handled correctly."""
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
            worker_flag,
            "2",
            str(object=rst_file),
        ],
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code != 0
    assert f"Error running command '{non_existent_command}'" in result.stderr


def test_document_with_no_examples(tmp_path: Path) -> None:
    """Documents with no matching code blocks are handled correctly."""
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


@pytest.mark.parametrize(
    argnames=("worker_options", "num_blocks"),
    argvalues=[
        ([], 1),  # Single example, no workers
        (["--no-write-to-file", "--example-workers", "1"], 2),  # Sequential
        (
            ["--no-write-to-file", "--example-workers", "2"],
            1,
        ),  # Parallel fallback
    ],
    ids=[
        "single-no-workers",
        "sequential-multi-block",
        "parallel-single-block",
    ],
)
def test_execution_error_handling(
    tmp_path: Path,
    worker_options: list[str],
    num_blocks: int,
) -> None:
    """Errors are handled correctly across different execution modes."""
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"

    # Generate content with the specified number of blocks
    blocks = [f'print("Block {i}")' for i in range(1, num_blocks + 1)]
    block_text = "\n\n.. code-block:: python\n\n    ".join(blocks)
    content = f".. code-block:: python\n\n    {block_text}\n"

    rst_file.write_text(data=content, encoding="utf-8")
    non_existent_command = uuid.uuid4().hex
    result = runner.invoke(
        cli=main,
        args=[
            "--language",
            "python",
            "--command",
            non_existent_command,
            *worker_options,
            str(object=rst_file),
        ],
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code != 0
    assert f"Error running command '{non_existent_command}'" in result.stderr


@pytest.mark.parametrize(
    argnames=(
        "command",
        "should_succeed",
        "expected_stdout",
        "expected_stderr",
    ),
    argvalues=[
        ("cat", True, "Only one block", ""),
        (uuid.uuid4().hex, False, "", "Error running command"),
    ],
    ids=["success", "error"],
)
def test_single_example_with_parallel_workers(
    *,
    tmp_path: Path,
    command: str,
    should_succeed: bool,
    expected_stdout: str,
    expected_stderr: str,
) -> None:
    """
    Single example with example_workers>1 falls back to sequential
    execution.
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
            command,
            "--no-pad-file",
            "--no-write-to-file",
            "--example-workers",
            "2",
            str(object=rst_file),
        ],
        catch_exceptions=False,
        color=True,
    )

    assert (result.exit_code == 0) == should_succeed
    assert expected_stdout in result.stdout
    assert expected_stderr in result.stderr


def test_verbose_running(tmp_path: Path) -> None:
    """``--verbose`` shows what is running."""
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
        {fg.green}Running 'cat' on code block at {rst_file}:1{reset}
        """,
    )
    assert result.stdout == expected_output
    assert result.stderr == expected_stderr


def test_verbose_running_with_stderr(tmp_path: Path) -> None:
    """``--verbose`` shows what is running before any stderr output."""
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
        {fg.green}Running '{command}' on code block at {rst_file}:1{reset}
        error
        {fg.green}Running '{command}' on code block at {rst_file}:19{reset}
        error
        """,
    )
    assert result.stdout == expected_output
    assert result.stderr == expected_stderr


def test_main_entry_point() -> None:
    """It is possible to run the main entry point."""
    result = subprocess.run(
        args=[sys.executable, "-m", "doccmd"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert "Usage:" in result.stderr


def test_command_not_found(tmp_path: Path) -> None:
    """An error is shown when the command is not found."""
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
    """An error is shown when the command is a non-executable file."""
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
    It is possible to run a command against multiple code blocks in a
    document
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
    By default, the next code block after a 'skip doccmd: next' comment
    in a
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
    """An error is shown if a skip is given with no arguments."""
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
    """An error is shown if a skip is given with bad arguments."""
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
    The next code block after a custom skip marker comment in a rST
    document is
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
    By default, the next code block after a 'skip doccmd: next' comment
    in a
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
    The next code block after a custom skip marker comment in a MyST
    document
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
    All given skip markers, including the default one, are
    respected.
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
    """Skip start and end markers are respected."""
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
    """Duplicate skip markers are respected."""
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
    """No error is shown when the default skip marker is given."""
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
    It is possible to mark a code block as to be skipped by multiple
    markers.
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
    """Bad skip orders are flagged."""
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
    """No error is shown when an empty file is given."""
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
    """The line endings of the original file are used in the new file."""
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
    Code blocks in a supported markup language in a file with an
    extension
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
    """An error is shown when the file suffix is not known."""
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
    """ReStructuredText files with custom suffixes are recognized."""
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


def test_markdown_code_block_line_number(tmp_path: Path) -> None:
    """Line numbers in error messages for Markdown code blocks are correct.

    When a command reports an error with a line number from a padded
    temporary file, that line number should correspond to the correct
    line in the original Markdown source file.

    This is a regression test for a bug where Markdown code blocks
    had an off-by-one error in their reported line numbers. The padding
    was incorrect, causing error messages to point to the wrong line.

    For example, in a Markdown file:
        Line 1: Example
        Line 2: (empty)
        Line 3: ```python
        Line 4: syntax error here
        Line 5: ```

    An error on line 4 should be reported as line 4, not line 5.
    """
    runner = CliRunner()
    md_file = tmp_path / "example.md"
    # Line 1: "Example"
    # Line 2: empty
    # Line 3: ```python
    # Line 4: syntax error here
    # Line 5: ```
    content = textwrap.dedent(
        text="""\
        Example

        ```python
        syntax error here
        ```
        """,
    )
    md_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--command",
        f"{Path(sys.executable).as_posix()}",
        str(object=md_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code != 0
    # The syntax error is on line 4 of the original file.
    # The error message should report line 4, not line 5.
    assert "line 4" in result.stderr


def test_norg(tmp_path: Path) -> None:
    """It is possible to run a command against a Norg file."""
    runner = CliRunner()
    source_file = tmp_path / "example.norg"
    content = textwrap.dedent(
        text="""\
        * Heading

        @code python
        x = 1
        @end

        @code python
        x = 2
        @end

        @code python
        x = 3
        @end
        """,
    )
    source_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--no-pad-file",
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
        x = 1
        x = 2
        x = 3
        """,
    )
    assert result.stdout == expected_output
    assert result.stderr == ""


def test_norg_in_directory(tmp_path: Path) -> None:
    """Norg files in a directory are discovered and processed."""
    runner = CliRunner()
    norg_file = tmp_path / "example.norg"
    norg_content = textwrap.dedent(
        text="""\
        @code python
        norg_block
        @end
        """,
    )
    norg_file.write_text(data=norg_content, encoding="utf-8")

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
    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert "norg_block" in result.stdout


def test_custom_norg_extension(tmp_path: Path) -> None:
    """It is possible to use a custom extension for Norg files."""
    runner = CliRunner()
    source_file = tmp_path / "example.custom_norg"
    content = textwrap.dedent(
        text="""\
        @code python
        custom_extension_block
        @end
        """,
    )
    source_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--norg-extension",
        ".custom_norg",
        "--no-pad-file",
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
        custom_extension_block
        """,
    )
    assert result.stdout == expected_output
    assert result.stderr == ""


@pytest.mark.parametrize(
    argnames=("group_padding_options", "expect_padding"),
    argvalues=[
        pytest.param(["--pad-groups"], True, id="pad-groups"),
        pytest.param(["--no-pad-groups"], False, id="no-pad-groups"),
    ],
)
def test_group_mdx_by_attribute(
    *,
    tmp_path: Path,
    group_padding_options: Sequence[str],
    expect_padding: bool,
) -> None:
    """MDX code blocks with matching attribute values are grouped together.

    Blocks with the same attribute value are combined into a single
    temporary file and passed to the command once, rather than being
    processed individually.
    """
    runner = CliRunner()
    mdx_file = tmp_path / "example.mdx"
    script = tmp_path / "print_underlined.py"
    content = textwrap.dedent(
        text="""\
        ```python group="example1"
        block_1
        ```

        ```python group="example2"
        block_2
        ```

        ```python group="example1"
        block_3
        ```

        ```python
        block_no_group
        ```
        """,
    )
    mdx_file.write_text(data=content, encoding="utf-8")

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
        "--no-pad-file",
        *group_padding_options,
        "--group-mdx-by-attribute",
        "group",
        "--language",
        "python",
        "--command",
        f"{Path(sys.executable).as_posix()} {script.as_posix()}",
        str(object=mdx_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )

    # Blocks with same "group" attribute value are grouped together
    # block_1 and block_3 have group="example1", so they are grouped
    # block_2 has group="example2", so it is separate
    # block_no_group has no group attribute, so it is processed normally
    if expect_padding:
        expected_output = textwrap.dedent(
            text="""\
            block_1







            block_3
            -------
            block_2
            -------
            block_no_group
            -------
            """,
        )
    else:
        expected_output = textwrap.dedent(
            text="""\
            block_1

            block_3
            -------
            block_2
            -------
            block_no_group
            -------
            """,
        )

    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert result.stdout == expected_output


def test_group_mdx_by_attribute_no_matches(
    *,
    tmp_path: Path,
) -> None:
    """Code blocks without the grouping attribute are processed
    individually.

    This ensures the grouping feature degrades gracefully when blocks
    don't have the specified attribute.
    """
    runner = CliRunner()
    mdx_file = tmp_path / "example.mdx"
    content = textwrap.dedent(
        text="""\
        ```python
        block_1
        ```

        ```python
        block_2
        ```
        """,
    )
    mdx_file.write_text(data=content, encoding="utf-8")

    arguments = [
        "--no-pad-file",
        "--group-mdx-by-attribute",
        "group",
        "--language",
        "python",
        "--command",
        "cat",
        str(object=mdx_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )

    expected_output = textwrap.dedent(
        text="""\
        block_1
        block_2
        """,
    )

    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert result.stdout == expected_output


def test_group_mdx_by_attribute_custom_attribute_name(
    *,
    tmp_path: Path,
) -> None:
    """Any attribute name can be used for grouping.

    This flexibility allows grouping by attributes like 'file',
    'session', or any other custom attribute in MDX code blocks.
    """
    runner = CliRunner()
    mdx_file = tmp_path / "example.mdx"
    script = tmp_path / "print_underlined.py"
    content = textwrap.dedent(
        text="""\
        ```python file="example1.py"
        block_1
        ```

        ```python file="example1.py"
        block_2
        ```

        ```python file="example2.py"
        block_3
        ```
        """,
    )
    mdx_file.write_text(data=content, encoding="utf-8")

    print_underlined_script = textwrap.dedent(
        text="""\
        import sys
        import pathlib

        print(pathlib.Path(sys.argv[1]).read_text().strip())
        print("-------")
        """,
    )
    script.write_text(data=print_underlined_script, encoding="utf-8")

    arguments = [
        "--no-pad-file",
        "--no-pad-groups",
        "--group-mdx-by-attribute",
        "file",
        "--language",
        "python",
        "--command",
        f"{Path(sys.executable).as_posix()} {script.as_posix()}",
        str(object=mdx_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )

    # Blocks with file="example1.py" are grouped together
    expected_output = textwrap.dedent(
        text="""\
        block_1

        block_2
        -------
        block_3
        -------
        """,
    )

    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert result.stdout == expected_output


def test_group_mdx_by_attribute_only_mdx_files(
    *,
    tmp_path: Path,
) -> None:
    """Attribute-based grouping only applies to MDX files.

    RST and other file formats are processed normally even when
    attribute grouping is enabled.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    mdx_file = tmp_path / "example.mdx"

    rst_content = textwrap.dedent(
        text="""\
        .. code-block:: python

            rst_block
        """,
    )
    rst_file.write_text(data=rst_content, encoding="utf-8")

    mdx_content = textwrap.dedent(
        text="""\
        ```python group="example1"
        mdx_block_1
        ```

        ```python group="example1"
        mdx_block_2
        ```
        """,
    )
    mdx_file.write_text(data=mdx_content, encoding="utf-8")

    script = tmp_path / "print_underlined.py"
    print_underlined_script = textwrap.dedent(
        text="""\
        import sys
        import pathlib

        print(pathlib.Path(sys.argv[1]).read_text().strip())
        print("-------")
        """,
    )
    script.write_text(data=print_underlined_script, encoding="utf-8")

    arguments = [
        "--no-pad-file",
        "--no-pad-groups",
        "--group-mdx-by-attribute",
        "group",
        "--language",
        "python",
        "--command",
        f"{Path(sys.executable).as_posix()} {script.as_posix()}",
        str(object=rst_file),
        str(object=mdx_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )

    # RST block is processed normally, MDX blocks are grouped
    expected_output = textwrap.dedent(
        text="""\
        rst_block
        -------
        mdx_block_1

        mdx_block_2
        -------
        """,
    )

    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert result.stdout == expected_output


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
def test_group_mdx_by_attribute_modify_file(
    *,
    tmp_path: Path,
    fail_on_group_write_options: Sequence[str],
    expected_exit_code: int,
    message_colour: Graphic,
) -> None:
    """File modifications are blocked for grouped MDX code blocks.

    Since grouped blocks are combined into a single temporary file,
    writing back to the original source would be ambiguous. The tool
    detects this and reports which group was modified.
    """
    runner = CliRunner()
    mdx_file = tmp_path / "example.mdx"
    content = textwrap.dedent(
        text="""\
        ```python group="example1"
        a = 1
        b = 1
        c = 1
        ```
        """,
    )
    mdx_file.write_text(data=content, encoding="utf-8")
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
        "--group-mdx-by-attribute",
        "group",
        "--language",
        "python",
        "--command",
        f"{Path(sys.executable).as_posix()} {modify_code_file.as_posix()}",
        str(object=mdx_file),
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
    new_content = mdx_file.read_text(encoding="utf-8")
    expected_content = content
    assert new_content == expected_content

    expected_stderr = textwrap.dedent(
        text=f"""\
            {message_colour}Writing to a group is not supported.

            A command modified the contents of examples in the group ending on line 1 in {mdx_file.as_posix()}.

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


def test_group_mdx_by_attribute_no_default_markers_in_mdx(
    *,
    tmp_path: Path,
) -> None:
    """Default group markers are not applied to MDX files with attribute
    grouping.

    When using ``--group-mdx-by-attribute``, the default "all" marker should
    not be added to the default_group_markers set. This means MDX files
    should not process 'group doccmd[all]' directives, as attribute
    grouping is mutually exclusive with marker-based grouping. Blocks
    within those directives should be processed normally based on their
    attributes.
    """
    runner = CliRunner()
    mdx_file = tmp_path / "example.mdx"
    content = textwrap.dedent(
        text="""\
        <!--- group doccmd[all]: start -->

        ```python
        block_without_attribute
        ```

        ```python group="example1"
        block_1
        ```

        <!--- group doccmd[all]: end -->

        ```python group="example1"
        block_2
        ```
        """,
    )
    mdx_file.write_text(data=content, encoding="utf-8")

    script = tmp_path / "print_underlined.py"
    print_underlined_script = textwrap.dedent(
        text="""\
        import sys
        import pathlib

        print(pathlib.Path(sys.argv[1]).read_text().strip())
        print("-------")
        """,
    )
    script.write_text(data=print_underlined_script, encoding="utf-8")

    arguments = [
        "--no-pad-file",
        "--no-pad-groups",
        "--group-mdx-by-attribute",
        "group",
        "--language",
        "python",
        "--command",
        f"{Path(sys.executable).as_posix()} {script.as_posix()}",
        str(object=mdx_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )

    # The 'group doccmd[all]' directive should be ignored in MDX files.
    # Blocks are processed based on their attributes:
    # - block_without_attribute is processed individually (no group attribute)
    # - block_1 and block_2 are grouped together (both have group="example1")
    expected_output = textwrap.dedent(
        text="""\
        block_without_attribute
        -------
        block_1

        block_2
        -------
        """,
    )

    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert result.stdout == expected_output


def test_group_mdx_by_attribute_default_markers_in_rst(
    *,
    tmp_path: Path,
) -> None:
    """Default group markers still work in RST files with MDX attribute
    grouping.

    When using ``--group-mdx-by-attribute``, non-MDX files (like RST) should
    still support the default 'group doccmd[all]' directive. The default
    marker should only be excluded for MDX files, not for all file
    types.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    mdx_file = tmp_path / "example.mdx"

    rst_content = textwrap.dedent(
        text="""\
        .. group doccmd[all]: start

        .. code-block:: python

            rst_group_block_1

        .. code-block:: python

            rst_group_block_2

        .. group doccmd[all]: end

        .. code-block:: python

            rst_single_block
        """,
    )
    rst_file.write_text(data=rst_content, encoding="utf-8")

    mdx_content = textwrap.dedent(
        text="""\
        ```python group="example1"
        mdx_block_1
        ```

        ```python group="example1"
        mdx_block_2
        ```
        """,
    )
    mdx_file.write_text(data=mdx_content, encoding="utf-8")

    script = tmp_path / "print_underlined.py"
    print_underlined_script = textwrap.dedent(
        text="""\
        import sys
        import pathlib

        print(pathlib.Path(sys.argv[1]).read_text().strip())
        print("-------")
        """,
    )
    script.write_text(data=print_underlined_script, encoding="utf-8")

    arguments = [
        "--no-pad-file",
        "--no-pad-groups",
        "--group-mdx-by-attribute",
        "group",
        "--language",
        "python",
        "--command",
        f"{Path(sys.executable).as_posix()} {script.as_posix()}",
        str(object=rst_file),
        str(object=mdx_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )

    # RST file should have its 'group doccmd[all]' directive respected,
    # grouping the two blocks together. MDX blocks should be grouped
    # by their attribute value.
    expected_output = textwrap.dedent(
        text="""\
        rst_group_block_1

        rst_group_block_2
        -------
        rst_single_block
        -------
        mdx_block_1

        mdx_block_2
        -------
        """,
    )

    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert result.stdout == expected_output


@pytest.mark.parametrize(
    argnames=("fail_on_parse_error_options", "expected_exit_code"),
    argvalues=[
        ([], 0),
        (["--fail-on-parse-error"], 1),
    ],
)
def test_group_start_without_end(
    tmp_path: Path,
    fail_on_parse_error_options: Sequence[str],
    expected_exit_code: int,
) -> None:
    """Error if a group is started but not ended."""
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. group doccmd[all]: start

        .. code-block:: python

            print("Hello")
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")

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
    assert result.exit_code == expected_exit_code, (
        result.stdout,
        result.stderr,
    )
    expected_error = (
        f"{fg.red}Could not parse {rst_file}: "
        "'group doccmd[all]: start' must be followed by "
        f"'group doccmd[all]: end'{reset}"
    )
    assert result.stderr == expected_error + "\n"


def test_group_nested_start_without_end(tmp_path: Path) -> None:
    """Error if nested group start directives are not properly closed."""
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    content = textwrap.dedent(
        text="""\
        .. group doccmd[all]: start

        .. code-block:: python

            print("First")

        .. group doccmd[all]: start

        .. code-block:: python

            print("Second")

        .. group doccmd[all]: end
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")

    arguments = [
        "--fail-on-parse-error",
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
    assert result.exit_code == 1, (
        result.stdout,
        result.stderr,
    )
    expected_error = (
        f"{fg.red}Could not parse {rst_file}: "
        "'group doccmd[all]: start' must be followed by "
        f"'group doccmd[all]: end'{reset}"
    )
    assert result.stderr == expected_error + "\n"


def test_group_file_with_manual_group_directive(
    *,
    tmp_path: Path,
) -> None:
    """Test that manual group directives don't conflict with --group-file.

    When --group-file is enabled, manual group directives (like 'group
    doccmd[all]: start/end') should be ignored to avoid conflicts. This
    test verifies that files with manual group directives can still be
    processed correctly when --group-file is enabled.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    script = tmp_path / "print_underlined.py"
    content = textwrap.dedent(
        text="""\
        .. group doccmd[all]: start

        .. code-block:: python

            block_1

        .. code-block:: python

            block_2

        .. group doccmd[all]: end

        .. code-block:: python

            block_3
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")

    print_underlined_script = textwrap.dedent(
        text="""\
        import sys
        import pathlib

        print(pathlib.Path(sys.argv[1]).read_text().strip())
        print("-------")
        """,
    )
    script.write_text(data=print_underlined_script, encoding="utf-8")

    arguments = [
        "--no-pad-file",
        "--no-pad-groups",
        "--group-file",
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

    # All blocks should be grouped at the file level, ignoring manual
    # directives
    expected_output = textwrap.dedent(
        text="""\
        block_1

        block_2

        block_3
        -------
        """,
    )

    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert result.stdout == expected_output


def test_group_file_with_sphinx_jinja2_no_language(
    *,
    tmp_path: Path,
) -> None:
    """Test --group-file with --sphinx-jinja2 but no --language.

    When --group-file is enabled with --sphinx-jinja2 but without any
    --language options, GroupAllParser should not be created since there
    are no code block languages to process. The sphinx-jinja2 blocks should
    still be processed individually (not grouped) since they use a different
    parser.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    script = tmp_path / "print_underlined.py"
    content = textwrap.dedent(
        text="""\
        Some text.

        .. jinja::

            {% set x = 1 %}
            {{ x }}

        More text.

        .. jinja::

            {% set y = 2 %}
            {{ y }}
        """,
    )
    rst_file.write_text(data=content, encoding="utf-8")

    print_underlined_script = textwrap.dedent(
        text="""\
        import sys
        import pathlib

        print(pathlib.Path(sys.argv[1]).read_text().strip())
        print("-------")
        """,
    )
    script.write_text(data=print_underlined_script, encoding="utf-8")

    arguments = [
        "--no-pad-file",
        "--no-pad-groups",
        "--group-file",
        "--sphinx-jinja2",
        "--command",
        f"{Path(sys.executable).as_posix()} {script.as_posix()}",
        str(object=rst_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
    )

    # Jinja2 blocks should be processed individually, not grouped
    # because --group-file only groups code blocks of specified languages
    expected_output = textwrap.dedent(
        text="""\
        {% set x = 1 %}
        {{ x }}
        -------
        {% set y = 2 %}
        {{ y }}
        -------
        """,
    )

    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert result.stdout == expected_output


def test_custom_myst_file_suffixes(tmp_path: Path) -> None:
    """MyST files with custom suffixes are recognized."""
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
    """Test options for using pseudo-terminal."""
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
    argvalues=[
        "--rst-extension",
        "--myst-extension",
        "--markdown-extension",
        "--mdx-extension",
        "--djot-extension",
    ],
)
def test_source_given_extension_no_leading_period(
    tmp_path: Path,
    option: str,
) -> None:
    """
    An error is shown when a given source file extension is given with
    no
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


def test_overlapping_markdown_mdx_extensions(tmp_path: Path) -> None:
    """
    An error is shown if there are overlapping extensions for Markdown
    and MDX.
    """
    runner = CliRunner()
    source_file = tmp_path / "example.shared"
    content = textwrap.dedent(
        text="""\
        ```python
        y = 1
        ```
        """,
    )
    source_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--command",
        "cat",
        "--markdown-extension",
        ".shared",
        "--mdx-extension",
        ".shared",
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

            Error: Overlapping suffixes between Markdown and MDX: .shared.
            """,
    )
    assert result.stdout == ""
    assert result.stderr == expected_stderr


def test_overlapping_markdown_djot_extensions(tmp_path: Path) -> None:
    """
    An error is shown if there are overlapping extensions for Markdown
    and
    Djot.
    """
    runner = CliRunner()
    source_file = tmp_path / "example.shared"
    content = textwrap.dedent(
        text="""\
        ```python
        y = 1
        ```
        """,
    )
    source_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--command",
        "cat",
        "--markdown-extension",
        ".shared",
        "--djot-extension",
        ".shared",
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

            Error: Overlapping suffixes between Markdown and Djot: .shared.
            """,
    )
    assert result.stdout == ""
    assert result.stderr == expected_stderr


def test_overlapping_extensions_dot(tmp_path: Path) -> None:
    """No error is shown if multiple extension types are '.'."""
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
    """It is possible to run a command against a Markdown file."""
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


def test_djot(tmp_path: Path) -> None:
    """It is possible to run a command against a Djot file."""
    runner = CliRunner()
    source_file = tmp_path / "example.djot"
    content = textwrap.dedent(
        text="""\
        {% skip doccmd[all]: next %}

        ```python
            x = 1
        ```

        {% skip doccmd[all]: next %}

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
        x = 3
        """,
    )
    assert result.stdout == expected_output
    assert result.stderr == ""


def test_djot_implicit_code_block_closure(tmp_path: Path) -> None:
    """Djot code blocks are correctly parsed when implicitly closed."""
    runner = CliRunner()
    source_file = tmp_path / "example.djot"
    # Code block inside a blockquote without an explicit closing fence
    content = textwrap.dedent(
        text="""\
        > ```python
        > code in a
        > block quote

        Paragraph.
        """,
    )
    source_file.write_text(data=content, encoding="utf-8")
    arguments = [
        "--language",
        "python",
        "--no-pad-file",
        "--no-write-to-file",
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
    # The code block should be parsed correctly despite lacking a closing fence
    expected_output = textwrap.dedent(
        text="""\
        code in a
        block quote
        """,
    )
    assert result.stdout == expected_output
    assert result.stderr == ""


def test_mdx(tmp_path: Path) -> None:
    """It is possible to run a command against an MDX file."""
    runner = CliRunner()
    source_file = tmp_path / "example.mdx"
    content = textwrap.dedent(
        text="""\
        <!--- skip doccmd[all]: next -->

        ```python
            y = 1
        ```

        ```python
            y = 2
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
        y = 2
        """,
    )
    assert result.stdout == expected_output
    assert result.stderr == ""


def test_mdx_parametrized_code_blocks(tmp_path: Path) -> None:
    """
    MDX code blocks with parameters (like title) are correctly
    parsed.
    """
    runner = CliRunner()
    source_file = tmp_path / "example.mdx"
    content = textwrap.dedent(
        text="""\
        ```python showLineNumbers title="world.py"
        print("hello from python")
        ```

        ```js title="script.js"
        console.log("javascript");
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
        print("hello from python")
        """,
    )
    assert result.stdout == expected_output
    assert result.stderr == ""


def test_directory(tmp_path: Path) -> None:
    """All source files in a given directory are worked on."""
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
    If a file is given which is within a directory that is also given,
    the file
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
    The --max-depth option limits the depth of directories to search for
    files.
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
    Files matching any of the exclude patterns are not processed when
    recursing
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
    Lexing exceptions are handled when an invalid source file is
    given.
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
    """Commands in groups cannot modify files in single grouped blocks."""
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
    """Commands in groups cannot modify files in multiple grouped commands."""
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
    """It is possible to run commands against sphinx-jinja2 blocks."""
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
    """An error is shown when an empty language is given."""
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
    """With --continue-on-error, execution continues across files when
    errors
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
    With --continue-on-error and --fail-on-parse-error, encoding errors
    are
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
    With --continue-on-error and --fail-on-group-write, group write
    errors are
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
    """With --continue-on-error, OSError (command not found) is collected
    and
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


@pytest.mark.parametrize(
    argnames=("group_file_options", "expect_grouped"),
    argvalues=[
        pytest.param(["--group-file"], True, id="group-file"),
        pytest.param(["--no-group-file"], False, id="no-group-file"),
    ],
)
@pytest.mark.parametrize(
    argnames=("group_padding_options", "expect_padding"),
    argvalues=[
        pytest.param(["--pad-groups"], True, id="pad-groups"),
        pytest.param(["--no-pad-groups"], False, id="no-pad-groups"),
    ],
)
def test_group_file(
    *,
    tmp_path: Path,
    group_file_options: Sequence[str],
    expect_grouped: bool,
    group_padding_options: Sequence[str],
    expect_padding: bool,
) -> None:
    """Test --group-file option groups all code blocks in a file.

    When --group-file is enabled, all code blocks of the same language
    in a file are automatically grouped together without requiring
    explicit group directives.
    """
    runner = CliRunner()
    rst_file = tmp_path / "example.rst"
    script = tmp_path / "print_underlined.py"
    content = textwrap.dedent(
        text="""\
        .. code-block:: python

            block_1

        .. code-block:: python

            block_2

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
        "--no-pad-file",
        *group_padding_options,
        *group_file_options,
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

    if expect_grouped:
        # All blocks should be grouped together
        if expect_padding:
            expected_output = textwrap.dedent(
                text="""\
                block_1



                block_2



                block_3
                -------
                """,
            )
        else:
            expected_output = textwrap.dedent(
                text="""\
                block_1

                block_2

                block_3
                -------
                """,
            )
    else:
        # Each block should be processed separately
        expected_output = textwrap.dedent(
            text="""\
            block_1
            -------
            block_2
            -------
            block_3
            -------
            """,
        )

    assert result.exit_code == 0, (result.stdout, result.stderr)
    assert result.stdout == expected_output


def test_respect_gitignore_default(tmp_path: Path) -> None:
    """
    By default, files matching .gitignore patterns are not processed
    when
    recursively discovering files in directories.
    """
    runner = CliRunner()

    # Initialize a git repository
    subprocess.run(
        args=["git", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    # Create a .gitignore file
    gitignore_file = tmp_path / ".gitignore"
    gitignore_file.write_text(data="ignored/\n", encoding="utf-8")

    # Create a non-ignored file
    included_file = tmp_path / "included.rst"
    included_content = textwrap.dedent(
        text="""\
        .. code-block:: python

            included_block
        """,
    )
    included_file.write_text(data=included_content, encoding="utf-8")

    # Create an ignored directory with a file
    ignored_dir = tmp_path / "ignored"
    ignored_dir.mkdir()
    ignored_file = ignored_dir / "ignored.rst"
    ignored_content = textwrap.dedent(
        text="""\
        .. code-block:: python

            ignored_block
        """,
    )
    ignored_file.write_text(data=ignored_content, encoding="utf-8")

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
    # Only the included file should be processed
    expected_output = "included_block\n"
    assert result.stdout == expected_output
    assert result.stderr == ""


def test_no_respect_gitignore(tmp_path: Path) -> None:
    """
    When --no-respect-gitignore is given, files matching .gitignore
    patterns
    are processed when recursively discovering files in directories.
    """
    runner = CliRunner()

    # Initialize a git repository
    subprocess.run(
        args=["git", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    # Create a .gitignore file
    gitignore_file = tmp_path / ".gitignore"
    gitignore_file.write_text(data="ignored/\n", encoding="utf-8")

    # Create a non-ignored file
    included_file = tmp_path / "included.rst"
    included_content = textwrap.dedent(
        text="""\
        .. code-block:: python

            included_block
        """,
    )
    included_file.write_text(data=included_content, encoding="utf-8")

    # Create an ignored directory with a file
    ignored_dir = tmp_path / "ignored"
    ignored_dir.mkdir()
    ignored_file = ignored_dir / "ignored.rst"
    ignored_content = textwrap.dedent(
        text="""\
        .. code-block:: python

            ignored_block
        """,
    )
    ignored_file.write_text(data=ignored_content, encoding="utf-8")

    arguments = [
        "--language",
        "python",
        "--no-pad-file",
        "--no-respect-gitignore",
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
    # Both files should be processed (order may vary)
    assert "included_block" in result.stdout
    assert "ignored_block" in result.stdout
    assert result.stderr == ""


def test_respect_gitignore_direct_file_not_affected(tmp_path: Path) -> None:
    """
    Files passed directly are not affected by .gitignore filtering,
    even when --respect-gitignore is enabled.
    """
    runner = CliRunner()

    # Initialize a git repository
    subprocess.run(
        args=["git", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    # Create a .gitignore file
    gitignore_file = tmp_path / ".gitignore"
    gitignore_file.write_text(data="ignored/\n", encoding="utf-8")

    # Create an ignored directory with a file
    ignored_dir = tmp_path / "ignored"
    ignored_dir.mkdir()
    ignored_file = ignored_dir / "ignored.rst"
    ignored_content = textwrap.dedent(
        text="""\
        .. code-block:: python

            ignored_but_direct_block
        """,
    )
    ignored_file.write_text(data=ignored_content, encoding="utf-8")

    # Pass the ignored file directly
    arguments = [
        "--language",
        "python",
        "--no-pad-file",
        "--command",
        "cat",
        str(object=ignored_file),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == 0, result.stderr
    # The directly passed file should be processed
    expected_output = "ignored_but_direct_block\n"
    assert result.stdout == expected_output
    assert result.stderr == ""


def test_respect_gitignore_no_git_repo(tmp_path: Path) -> None:
    """When no git repository is found, all files are processed."""
    runner = CliRunner()

    # Create a file (no git repo)
    rst_file = tmp_path / "example.rst"
    rst_content = textwrap.dedent(
        text="""\
        .. code-block:: python

            block_in_non_git
        """,
    )
    rst_file.write_text(data=rst_content, encoding="utf-8")

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
    expected_output = "block_in_non_git\n"
    assert result.stdout == expected_output
    assert result.stderr == ""


def test_respect_gitignore_nested_gitignore(tmp_path: Path) -> None:
    """Nested .gitignore files are respected."""
    runner = CliRunner()

    # Initialize a git repository
    subprocess.run(
        args=["git", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    # Create a root file
    root_file = tmp_path / "root.rst"
    root_content = textwrap.dedent(
        text="""\
        .. code-block:: python

            root_block
        """,
    )
    root_file.write_text(data=root_content, encoding="utf-8")

    # Create a subdirectory with its own .gitignore
    sub_dir = tmp_path / "subdir"
    sub_dir.mkdir()

    sub_gitignore = sub_dir / ".gitignore"
    # Include a comment and empty line to exercise those code paths
    sub_gitignore.write_text(
        data="# This is a comment\n\nlocal_ignored.rst\n",
        encoding="utf-8",
    )

    # Create a file that should be ignored by the nested .gitignore
    ignored_file = sub_dir / "local_ignored.rst"
    ignored_content = textwrap.dedent(
        text="""\
        .. code-block:: python

            locally_ignored_block
        """,
    )
    ignored_file.write_text(data=ignored_content, encoding="utf-8")

    # Create a file that should not be ignored
    included_file = sub_dir / "included.rst"
    included_content = textwrap.dedent(
        text="""\
        .. code-block:: python

            subdir_included_block
        """,
    )
    included_file.write_text(data=included_content, encoding="utf-8")

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
    # The locally ignored file should not be processed
    assert "locally_ignored_block" not in result.stdout
    # The other files should be processed
    assert "root_block" in result.stdout
    assert "subdir_included_block" in result.stdout
    assert result.stderr == ""


def test_respect_gitignore_caching(tmp_path: Path) -> None:
    """
    When the same directory is passed via different paths that resolve
    to the same location, the gitignore spec is cached and reused.
    """
    runner = CliRunner()

    # Initialize a git repository
    subprocess.run(
        args=["git", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    # Create a .gitignore file
    gitignore_file = tmp_path / ".gitignore"
    gitignore_file.write_text(data="ignored/\n", encoding="utf-8")

    # Create a file to process
    rst_file = tmp_path / "example.rst"
    rst_content = textwrap.dedent(
        text="""\
        .. code-block:: python

            cached_test_block
        """,
    )
    rst_file.write_text(data=rst_content, encoding="utf-8")

    # Create a symlink to the same directory to exercise the caching code path
    symlink_path = tmp_path.parent / "symlink_to_dir"
    symlink_path.symlink_to(target=tmp_path)

    arguments = [
        "--language",
        "python",
        "--no-pad-file",
        "--command",
        "cat",
        str(object=tmp_path),
        str(object=symlink_path),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == 0, result.stderr
    # The file should be processed (de-duplicated at the file level)
    assert "cached_test_block" in result.stdout
    assert result.stderr == ""


def test_respect_gitignore_symlink_outside_repo(tmp_path: Path) -> None:
    """
    Symlinks pointing outside the git repository are processed normally,
    even when --respect-gitignore is enabled.
    """
    runner = CliRunner()

    # Create a git repository
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    subprocess.run(
        args=["git", "init"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )

    # Create a .gitignore file
    gitignore_file = repo_dir / ".gitignore"
    gitignore_file.write_text(data="ignored/\n", encoding="utf-8")

    # Create a directory outside the repo with a file
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    outside_file = outside_dir / "outside.rst"
    outside_content = textwrap.dedent(
        text="""\
        .. code-block:: python

            outside_block
        """,
    )
    outside_file.write_text(data=outside_content, encoding="utf-8")

    # Create a symlink inside the repo pointing to the file outside
    symlink_in_repo = repo_dir / "link_to_outside.rst"
    symlink_in_repo.symlink_to(target=outside_file)

    arguments = [
        "--language",
        "python",
        "--no-pad-file",
        "--command",
        "cat",
        str(object=repo_dir),
    ]
    result = runner.invoke(
        cli=main,
        args=arguments,
        catch_exceptions=False,
        color=True,
    )
    assert result.exit_code == 0, result.stderr
    # The symlinked file outside the repo should be processed
    assert "outside_block" in result.stdout
    assert result.stderr == ""
