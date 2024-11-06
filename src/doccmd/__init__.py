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
from typing import TYPE_CHECKING, TypeVar, overload

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

T = TypeVar("T")


@beartype
def _deduplicate(
    ctx: click.Context,
    param: click.Parameter,
    sequence: Sequence[T],
) -> Sequence[T]:
    """
    De-duplicate a sequence while keeping the order.
    """
    assert ctx
    assert param
    return tuple(dict.fromkeys(sequence).keys())


@overload
def _validate_file_extension(
    ctx: click.Context,
    param: click.Parameter,
    value: str,
) -> str: ...


@overload
def _validate_file_extension(
    ctx: click.Context,
    param: click.Parameter,
    value: None,
) -> None: ...


@beartype
def _validate_file_extension(
    ctx: click.Context,
    param: click.Parameter,
    value: str | None,
) -> str | None:
    """
    Validate that the input string starts with a dot.
    """
    if value is None:
        return value

    if not value.startswith("."):
        message = f"'{value}' does not start with a '.'."
        raise click.BadParameter(message=message, ctx=ctx, param=param)
    return value


@beartype
def _validate_file_extensions(
    ctx: click.Context,
    param: click.Parameter,
    values: Sequence[str],
) -> Sequence[str]:
    """
    Validate that the input strings start with a dot.
    """
    # This is not necessary but it saves us later working with
    # duplicate values.
    values = _deduplicate(ctx=ctx, param=param, sequence=values)
    # We could just return `values` as we know that `_validate_file_extension`
    # does not modify the given value, but to be safe, we use the returned
    # values.
    return tuple(
        _validate_file_extension(ctx=ctx, param=param, value=value)
        for value in values
    )


@beartype
def _get_file_paths(
    *,
    document_paths: Sequence[Path],
    file_suffixes: Sequence[str],
    max_depth: int,
    exclude_patterns: Sequence[str],
) -> Sequence[Path]:
    """
    Get the file paths from the given document paths (files and directories).
    """
    file_paths: dict[Path, bool] = {}
    for path in document_paths:
        if path.is_file():
            file_paths[path] = True
        else:
            for file_suffix in file_suffixes:
                new_file_paths = (
                    path_part
                    for path_part in path.rglob(f"*{file_suffix}")
                    if len(path_part.relative_to(path).parts) <= max_depth
                )
                for new_file_path in new_file_paths:
                    if new_file_path.is_file() and not any(
                        new_file_path.match(path_pattern=pattern)
                        for pattern in exclude_patterns
                    ):
                        file_paths[new_file_path] = True
    return tuple(file_paths.keys())


@beartype
def _validate_file_suffix_overlaps(
    *,
    myst_suffixes: Iterable[str],
    rst_suffixes: Iterable[str],
) -> None:
    """
    Validate that the given file suffixes do not overlap.
    """
    myst_set = set(myst_suffixes)
    rst_set = set(rst_suffixes)
    overlap = myst_set & rst_set
    # Allow the dot to overlap, as it is a common way to specify
    # "no extensions".
    overlap_ignoring_dot = overlap - {"."}
    if overlap_ignoring_dot:
        message = (
            "Overlapping extensions between --rst-extension "
            "and --myst-extension: "
            f"{', '.join(sorted(overlap_ignoring_dot))}."
        )
        raise click.UsageError(message=message)


def _validate_files_are_known_markup_types(
    *,
    file_paths: Iterable[Path],
    myst_suffixes: Iterable[str],
    rst_suffixes: Iterable[str],
) -> None:
    """
    Validate that the given files are known markup types.
    """
    try:
        for file_path in file_paths:
            get_markup_language(
                file_path=file_path,
                myst_suffixes=myst_suffixes,
                rst_suffixes=rst_suffixes,
            )
    except UnknownMarkupLanguageError as exc:
        raise click.UsageError(message=str(exc)) from exc


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
    styled_message = click.style(text=message, fg="green")
    click.echo(message=styled_message, err=True)


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
    myst_suffixes: Iterable[str],
    rst_suffixes: Iterable[str],
) -> None:
    """
    Run commands on the given file.
    """
    markup_language = get_markup_language(
        file_path=document_path,
        myst_suffixes=myst_suffixes,
        rst_suffixes=rst_suffixes,
    )
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
    callback=_deduplicate,
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
    callback=_validate_file_extension,
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
    callback=_deduplicate,
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
    type=click.Path(exists=True, path_type=Path, dir_okay=True),
    nargs=-1,
    callback=_deduplicate,
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
@click.option(
    "--rst-extension",
    "rst_suffixes",
    type=str,
    help=(
        "Files with this extension (suffix) to treat as reStructuredText. "
        "Give this multiple times to look for multiple extensions. "
        "To avoid considering any files, "
        "including the default, "
        "as reStructuredText files, use `--rst-extension=.`."
    ),
    multiple=True,
    default=(".rst",),
    show_default=True,
    callback=_validate_file_extensions,
)
@click.option(
    "--myst-extension",
    "myst_suffixes",
    type=str,
    help=(
        "Files with this extension (suffix) to treat as MyST. "
        "Give this multiple times to look for multiple extensions. "
        "To avoid considering any files, "
        "including the default, "
        "as MyST files, use `--myst-extension=.`."
    ),
    multiple=True,
    default=(".md",),
    show_default=True,
    callback=_validate_file_extensions,
)
@click.option(
    "--max-depth",
    type=click.IntRange(min=1),
    default=sys.maxsize,
    show_default=False,
    help="Maximum depth to search for files in directories.",
)
@click.option(
    "--exclude",
    "exclude_patterns",
    type=str,
    multiple=True,
    help=(
        "A glob-style pattern that matches file paths to ignore while "
        "recursively discovering files in directories. "
        "This option can be used multiple times. "
        "Use forward slashes on all platforms."
    ),
)
@beartype
def main(
    *,
    languages: Sequence[str],
    command: str,
    document_paths: Sequence[Path],
    temporary_file_extension: str | None,
    temporary_file_name_prefix: str | None,
    pad_file: bool,
    verbose: bool,
    skip_markers: Sequence[str],
    use_pty_option: _UsePty,
    rst_suffixes: Sequence[str],
    myst_suffixes: Sequence[str],
    max_depth: int,
    exclude_patterns: Sequence[str],
) -> None:
    """Run commands against code blocks in the given documentation files.

    This works with Markdown and reStructuredText files.
    """
    args = shlex.split(s=command)
    use_pty = use_pty_option.use_pty()

    _validate_file_suffix_overlaps(
        myst_suffixes=myst_suffixes,
        rst_suffixes=rst_suffixes,
    )

    file_paths = _get_file_paths(
        document_paths=document_paths,
        file_suffixes=[*myst_suffixes, *rst_suffixes],
        max_depth=max_depth,
        exclude_patterns=exclude_patterns,
    )

    _validate_files_are_known_markup_types(
        file_paths=file_paths,
        myst_suffixes=myst_suffixes,
        rst_suffixes=rst_suffixes,
    )

    if verbose:
        _log_info(
            message="Using PTY for running commands."
            if use_pty
            else "Not using PTY for running commands."
        )

    for file_path in file_paths:
        for language in languages:
            _run_args_against_docs(
                args=args,
                document_path=file_path,
                code_block_language=language,
                pad_temporary_file=pad_file,
                verbose=verbose,
                temporary_file_extension=temporary_file_extension,
                temporary_file_name_prefix=temporary_file_name_prefix,
                skip_markers=skip_markers,
                use_pty=use_pty,
                myst_suffixes=myst_suffixes,
                rst_suffixes=rst_suffixes,
            )
