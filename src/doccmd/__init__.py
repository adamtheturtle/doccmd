"""
CLI to run commands on the given files.
"""

import platform
import shlex
import subprocess
import sys
from collections.abc import Iterable, Sequence
from enum import Enum, auto, unique
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import TYPE_CHECKING

import click
from beartype import beartype
from pygments.lexers import get_all_lexers
from sybil import Sybil
from sybil.evaluators.skip import Skipper
from sybil_extras.evaluators.shell_evaluator import ShellCommandEvaluator

from ._languages import UnknownMarkupLanguageError, get_markup_language

if TYPE_CHECKING:
    from sybil.typing import Parser

try:
    __version__ = version(__name__)
except PackageNotFoundError:  # pragma: no cover
    # When pkg_resources and git tags are not available,
    # for example in a PyInstaller binary,
    # we write the file ``_setuptools_scm_version.py`` on ``pip install``.
    from ._setuptools_scm_version import __version__


@unique
class _UsePty(Enum):
    """
    Choices for the use of a pseudo-terminal.
    """

    YES = auto()
    NO = auto()
    DETECT = auto()

    def use_pty(self) -> bool:
        """
        Whether to use a pseudo-terminal.
        """
        if self is _UsePty.DETECT:
            return sys.stdout.isatty() and platform.system() != "Windows"
        return self is _UsePty.YES


@beartype
def _log_info(message: str) -> None:
    """
    Log an info message.
    """
    styled_message = click.style(text=message, fg="yellow")
    click.echo(message=styled_message, err=False)


@beartype
def _log_warning(message: str) -> None:
    """
    Log a warning message.
    """
    styled_message = click.style(text=message, fg="yellow")
    click.echo(message=styled_message, err=True)


@beartype
def _log_error(message: str) -> None:
    """
    Log an error message.
    """
    styled_message = click.style(text=message, fg="red")
    click.echo(message=styled_message, err=True)


@beartype
def _detect_newline(file_path: Path) -> str | None:
    """
    Detect the newline character used in the given file.
    """
    content_bytes = file_path.read_bytes()
    for newline in (b"\r\n", b"\n", b"\r"):
        if newline in content_bytes:
            return newline.decode(encoding="utf-8")
    return None


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
def _get_skip_directives(skip_markers: Iterable[str]) -> Sequence[str]:
    """
    Skip directives based on the provided skip markers.
    """
    skip_directives: Sequence[str] = []

    for skip_marker in skip_markers:
        skip_directive = rf"skip doccmd\[{skip_marker}\]"
        skip_directives = [*skip_directives, skip_directive]
    return skip_directives


@beartype
def _get_temporary_file_extension(
    language: str,
    given_file_extension: str | None,
) -> str:
    """
    Get the file suffix, either from input or based on the language.
    """
    if given_file_extension is None:
        language_to_suffix = _map_languages_to_suffix()
        given_file_extension = language_to_suffix.get(language.lower(), ".txt")

    if not given_file_extension.startswith("."):
        given_file_extension = f".{given_file_extension}"

    return given_file_extension


@beartype
def _run_args_against_docs(
    *,
    document_path: Path,
    args: Sequence[str | Path],
    code_block_language: str,
    temporary_file_extension: str | None,
    temporary_file_name_prefix: str | None,
    pad_temporary_file: bool,
    verbose: bool,
    skip_markers: Iterable[str],
    use_pty: bool,
) -> None:
    """
    Run commands on the given file.
    """
    markup_language = get_markup_language(file_path=document_path)
    temporary_file_extension = _get_temporary_file_extension(
        language=code_block_language,
        given_file_extension=temporary_file_extension,
    )
    newline = _detect_newline(file_path=document_path)

    evaluator = ShellCommandEvaluator(
        args=args,
        tempfile_suffixes=(temporary_file_extension,),
        pad_file=pad_temporary_file,
        write_to_file=True,
        tempfile_name_prefix=temporary_file_name_prefix or "",
        newline=newline,
        use_pty=use_pty,
    )

    skip_markers = {*skip_markers, "all"}
    skip_directives = _get_skip_directives(skip_markers=skip_markers)
    skip_parsers = [
        markup_language.skip_parser_cls(directive=skip_directive)
        for skip_directive in skip_directives
    ]
    code_block_parsers = [
        markup_language.code_block_parser_cls(
            language=code_block_language,
            evaluator=evaluator,
        )
    ]

    parsers: Sequence[Parser] = [*code_block_parsers, *skip_parsers]
    sybil = Sybil(parsers=parsers)
    try:
        document = sybil.parse(path=document_path)
    except UnicodeError:
        if verbose:
            unicode_error_message = (
                f"Skipping '{document_path}' because it is not UTF-8 encoded."
            )
            _log_warning(message=unicode_error_message)
        return
    for example in document.examples():
        if (
            verbose
            and not isinstance(example.region.evaluator, Skipper)
            and not any(
                skip_parser.skipper.state_for(example=example).remove
                for skip_parser in skip_parsers
            )
        ):
            command_str = shlex.join(
                split_command=[str(item) for item in args],
            )
            running_command_message = (
                f"Running '{command_str}' on code block at "
                f"{document_path} line {example.line}"
            )
            _log_info(message=running_command_message)
        try:
            example.evaluate()
        except subprocess.CalledProcessError as exc:
            sys.exit(exc.returncode)
        except OSError as exc:
            os_error_message = f"Error running command '{args[0]}': {exc}"
            _log_error(message=os_error_message)
            sys.exit(exc.errno)


@click.command(name="doccmd")
@click.option(
    "languages",
    "-l",
    "--language",
    type=str,
    required=True,
    help=(
        "Run `command` against code blocks for this language. "
        "Give multiple times for multiple languages."
    ),
    multiple=True,
)
@click.option("command", "-c", "--command", type=str, required=True)
@click.option(
    "temporary_file_extension",
    "--temporary-file-extension",
    type=str,
    required=False,
    help=(
        "The file extension to give to the temporary file made from the code "
        "block. By default, the file extension is inferred from the language, "
        "or it is '.txt' if the language is not recognized."
    ),
)
@click.option(
    "temporary_file_name_prefix",
    "--temporary-file-name-prefix",
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
    "skip_markers",
    "--skip-marker",
    type=str,
    default=None,
    show_default=True,
    required=False,
    help=(
        """\
        The marker used to identify code blocks to be skipped.
        \b
        By default, code blocks which come just after a comment matching 'skip
        doccmd[all]: next' are skipped (e.g. `.. skip doccmd[all]: next` in
        reStructuredText, `<!--- skip doccmd[all]: next -->` in Markdown, or
        `% skip doccmd[all]: next` in MyST).
        \b
        When using this option, those, and code blocks which come just after a
        comment including the given marker are ignored. For example, if the
        given marker is 'type-check', code blocks which come just after a
        comment matching 'skip doccmd[type-check]: next' are also skipped.
        \b
        This marker is matched using a regular expression.
        """
    ),
    multiple=True,
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
    "document_paths",
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
@click.option(
    "--use-pty",
    "use_pty_option",
    is_flag=True,
    type=_UsePty,
    flag_value=_UsePty.YES,
    default=False,
    show_default="--detect-use-pty",
    help=(
        "Use a pseudo-terminal for running commands. "
        "This can be useful e.g. to get color output, but can also break "
        "in some environments. "
        "Not supported on Windows."
    ),
)
@click.option(
    "--no-use-pty",
    "use_pty_option",
    is_flag=True,
    type=_UsePty,
    flag_value=_UsePty.NO,
    default=False,
    show_default="--detect-use-pty",
    help=(
        "Do not use a pseudo-terminal for running commands. "
        "This is useful when ``doccmd`` detects that it is running in a "
        "TTY outside of Windows but the environment does not support PTYs."
    ),
)
@click.option(
    "--detect-use-pty",
    "use_pty_option",
    is_flag=True,
    type=_UsePty,
    flag_value=_UsePty.DETECT,
    default=True,
    show_default="True",
    help=(
        "Automatically determine whether to use a pseudo-terminal for running "
        "commands."
    ),
)
@beartype
def main(
    *,
    languages: Iterable[str],
    command: str,
    document_paths: Iterable[Path],
    temporary_file_extension: str | None,
    temporary_file_name_prefix: str | None,
    pad_file: bool,
    verbose: bool,
    skip_markers: Iterable[str],
    use_pty_option: _UsePty,
) -> None:
    """Run commands against code blocks in the given documentation files.

    This works with Markdown and reStructuredText files.
    """
    args = shlex.split(s=command)
    # De-duplicate some choices, keeping the order.
    languages = dict.fromkeys(languages).keys()
    skip_markers = dict.fromkeys(skip_markers).keys()
    document_paths = dict.fromkeys(document_paths).keys()
    use_pty = use_pty_option.use_pty()
    if verbose:
        _log_error(
            message="Using PTY for running commands."
            if use_pty
            else "Not using PTY for running commands."
        )

    try:
        for document_path in document_paths:
            get_markup_language(file_path=document_path)
    except UnknownMarkupLanguageError as exc:
        raise click.UsageError(message=str(exc)) from exc

    for document_path in document_paths:
        for language in languages:
            _run_args_against_docs(
                args=args,
                document_path=document_path,
                code_block_language=language,
                pad_temporary_file=pad_file,
                verbose=verbose,
                temporary_file_extension=temporary_file_extension,
                temporary_file_name_prefix=temporary_file_name_prefix,
                skip_markers=skip_markers,
                use_pty=use_pty,
            )
