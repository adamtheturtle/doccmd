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
from sybil.parsers.markdown import CodeBlockParser as MarkdownCodeBlockParser
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
    *,
    pad_file: bool,
) -> None:
    """Run commands on the given file."""
    language_to_suffix = _map_languages_to_suffix()
    suffix = language_to_suffix.get(language.lower(), ".txt")
    evaluator = ShellCommandEvaluator(
        args=args,
        tempfile_suffix=suffix,
        pad_file=pad_file,
        write_to_file=True,
    )

    rest_parser = RestCodeBlockParser(language=language, evaluator=evaluator)
    markdown_parser = MarkdownCodeBlockParser(
        language=language,
        evaluator=evaluator,
    )
    sybil = Sybil(parsers=[rest_parser, markdown_parser])
    document = sybil.parse(path=file_path)
    for example in document:
        try:
            example.evaluate()
        except subprocess.CalledProcessError as exc:
            sys.exit(exc.returncode)


@beartype
@click.command()
@click.option(
    "language",
    "-l",
    "--language",
    type=str,
    required=True,
    help="Run `command` against code blocks for this language.",
)
@click.option("command", "--command", type=str, required=True)
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
    type=click.Path(exists=True, path_type=Path),
    nargs=-1,
)
@click.version_option(version=__version__)
def main(
    language: str,
    command: str,
    file_paths: Iterable[Path],
    *,
    pad_file: bool,
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
        )
