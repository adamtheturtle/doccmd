"""CLI to run commands on the given files."""

import shlex
import subprocess
import sys
from collections.abc import Iterable, Sequence
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import click
from beartype import beartype
from pygments.lexers import get_all_lexers
from sybil import Sybil
from sybil.parsers.myst import CodeBlockParser as MystCodeBlockParser
from sybil.parsers.rest import CodeBlockParser as RestCodeBlockParser
from sybil_extras.evaluators.shell_evaluator import ShellCommandEvaluator

try:
    __version__ = version(__name__)
except PackageNotFoundError:  # pragma: no cover
    # When pkg_resources and git tags are not available,
    # for example in a PyInstaller binary,
    # we write the file ``_setuptools_scm_version.py`` on ``pip install``.
    from ._setuptools_scm_version import __version__


@beartype
def _map_languages_to_suffix() -> dict[str, str]:
    """
    Map programming languages to their corresponding file extension.
    """
    language_extension_map: dict[str, str] = {}

    for lexer in get_all_lexers():
        language_name = lexer[0]
        file_extensions = lexer[2]
        if file_extensions:
            canonical_file_extension = file_extensions[0]
            if canonical_file_extension.startswith("*."):
                canonical_file_suffix = canonical_file_extension[1:]
                language_extension_map[language_name.lower()] = (
                    canonical_file_suffix
                )

    return language_extension_map


@beartype
def _run_args_against_docs(
    file_path: Path,
    args: Sequence[str | Path],
    language: str,
    file_suffix: str | None,
    file_name_prefix: str | None,
    *,
    pad_file: bool,
    verbose: bool,
) -> None:
    """Run commands on the given file."""
    if file_suffix is None:
        language_to_suffix = _map_languages_to_suffix()
        file_suffix = language_to_suffix.get(language.lower(), ".txt")

    if not file_suffix.startswith("."):
        file_suffix = f".{file_suffix}"

    suffixes = (file_suffix,)

    evaluator = ShellCommandEvaluator(
        args=args,
        tempfile_suffixes=suffixes,
        pad_file=pad_file,
        write_to_file=True,
        tempfile_name_prefix=file_name_prefix or "",
    )

    rest_parser = RestCodeBlockParser(language=language, evaluator=evaluator)
    myst_parser = MystCodeBlockParser(
        language=language,
        evaluator=evaluator,
    )
    sybil = Sybil(parsers=[rest_parser, myst_parser])
    document = sybil.parse(path=file_path)
    for example in document.examples():
        if verbose:
            command_str = shlex.join(
                split_command=[str(item) for item in args],
            )
            message = (
                f"Running '{command_str}' on code block at "
                f"{file_path} line {example.line}"
            )
            styled_message = click.style(text=message, fg="yellow")
            click.echo(message=styled_message)
        try:
            example.evaluate()
        except subprocess.CalledProcessError as exc:
            sys.exit(exc.returncode)


@beartype
@click.command(name="doccmd")
@click.option(
    "language",
    "-l",
    "--language",
    type=str,
    required=True,
    help="Run `command` against code blocks for this language.",
)
@click.option("command", "-c", "--command", type=str, required=True)
@click.option(
    "file_suffix",
    "--file-suffix",
    type=str,
    required=False,
    help=(
        "The file extension to give to the temporary file made from the code "
        "block. By default, the file extension is inferred from the language, "
        "or it is '.txt' if the language is not recognized."
    ),
)
@click.option(
    "file_name_prefix",
    "--file-name-prefix",
    type=str,
    default="doccmd",
    show_default=True,
    required=True,
    help=(
        "The prefix to give to the temporary file made from the code block. "
        "This is useful for distinguishing files created by this tool "
        "from other files, e.g. for ignoring in linter configurations."
    ),
)
@click.option(
    "--pad-file/--no-pad-file",
    is_flag=True,
    default=True,
    show_default=True,
    help=(
        "Run the command against a temporary file padded with newlines. "
        "This is useful for matching line numbers from the output to "
        "the relevant location in the document. "
        "Use --no-pad-file for formatters - "
        "they generally need to look at the file without padding."
    ),
)
@click.argument(
    "file_paths",
    type=click.Path(exists=True, path_type=Path, dir_okay=False),
    nargs=-1,
)
@click.version_option(version=__version__)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Enable verbose output.",
)
def main(
    language: str,
    command: str,
    file_paths: Iterable[Path],
    file_suffix: str | None,
    file_name_prefix: str | None,
    *,
    pad_file: bool,
    verbose: bool,
) -> None:
    """
    Run commands against code blocks in the given documentation files.

    This works with Markdown and reStructuredText files.
    """
    args = shlex.split(s=command)
    for file_path in file_paths:
        _run_args_against_docs(
            args=args,
            file_path=file_path,
            language=language,
            pad_file=pad_file,
            verbose=verbose,
            file_suffix=file_suffix,
            file_name_prefix=file_name_prefix,
        )
