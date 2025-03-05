"""
CLI to run commands on the given files.
"""

import difflib
import platform
import shlex
import subprocess
import sys
import textwrap
from collections.abc import Iterable, Mapping, Sequence
from enum import Enum, auto, unique
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar, overload

import charset_normalizer
import click
from beartype import beartype
from pygments.lexers import get_all_lexers
from sybil import Sybil
from sybil.document import Document
from sybil.example import Example
from sybil.parsers.abstract.lexers import LexingException
from sybil_extras.evaluators.multi import MultiEvaluator
from sybil_extras.evaluators.shell_evaluator import ShellCommandEvaluator

from ._languages import (
    Markdown,
    MarkupLanguage,
    MyST,
    ReStructuredText,
)

if TYPE_CHECKING:
    from sybil.typing import Evaluator, Parser

try:
    __version__ = version(distribution_name=__name__)
except PackageNotFoundError:  # pragma: no cover
    # When pkg_resources and git tags are not available,
    # for example in a PyInstaller binary,
    # we write the file ``_setuptools_scm_version.py`` on ``pip install``.
    from ._setuptools_scm_version import __version__

T = TypeVar("T")


@beartype
class _LogCommandEvaluator:
    """
    Log a command before running it.
    """

    def __init__(
        self,
        *,
        args: Sequence[str | Path],
    ) -> None:
        """Initialize the evaluator.

        Args:
            args: The shell command to run.
        """
        self._args = args

    def __call__(self, example: Example) -> None:
        """
        Log the command before running it.
        """
        command_str = shlex.join(
            split_command=[str(object=item) for item in self._args],
        )
        running_command_message = (
            f"Running '{command_str}' on code block at "
            f"{example.path} line {example.line}"
        )
        _log_info(message=running_command_message)


@beartype
def _deduplicate(
    ctx: click.Context,
    param: click.Parameter,
    sequence: Sequence[T],
) -> Sequence[T]:
    """
    De-duplicate a sequence while keeping the order.
    """
    # We "use" the parameters to avoid vulture complaining.
    del ctx
    del param

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
                    for path_part in path.rglob(pattern=f"*{file_suffix}")
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
    suffix_groups: Mapping[MarkupLanguage, Iterable[str]],
) -> None:
    """
    Validate that the given file suffixes do not overlap.
    """
    for markup_language, suffixes in suffix_groups.items():
        for other_markup_language, other_suffixes in suffix_groups.items():
            if markup_language is other_markup_language:
                continue
            overlapping_suffixes = {*suffixes} & {*other_suffixes}
            # Allow the dot to overlap, as it is a common way to specify
            # "no extensions".
            overlapping_suffixes_ignoring_dot = overlapping_suffixes - {"."}

            if overlapping_suffixes_ignoring_dot:
                message = (
                    f"Overlapping suffixes between {markup_language.name} and "
                    f"{other_markup_language.name}: "
                    f"{', '.join(sorted(overlapping_suffixes_ignoring_dot))}."
                )
                raise click.UsageError(message=message)


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
    Log an error message.
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
def _detect_newline(content_bytes: bytes) -> bytes | None:
    """
    Detect the newline character used in the content.
    """
    for newline in (b"\r\n", b"\n", b"\r"):
        if newline in content_bytes:
            return newline
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
def _get_group_directives(markers: Iterable[str]) -> Sequence[str]:
    """
    Group directives based on the provided markers.
    """
    directives: Sequence[str] = []

    for marker in markers:
        directive = rf"group doccmd[{marker}]"
        directives = [*directives, directive]
    return directives


@beartype
def _get_skip_directives(markers: Iterable[str]) -> Sequence[str]:
    """
    Skip directives based on the provided markers.
    """
    directives: Sequence[str] = []

    for marker in markers:
        directive = rf"skip doccmd[{marker}]"
        directives = [*directives, directive]
    return directives


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
def _evaluate_document(
    *,
    document: Document,
    args: Sequence[str | Path],
) -> None:
    """Evaluate the document.

    Raises:
        _EvaluateError: An example in the document could not be evaluated.
    """
    try:
        for example in document.examples():
            example.evaluate()
    except ValueError as exc:
        raise _EvaluateError(
            command_args=args,
            reason=str(object=exc),
            exit_code=1,
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise _EvaluateError(
            command_args=args,
            reason=None,
            exit_code=exc.returncode,
        ) from exc
    except OSError as exc:
        raise _EvaluateError(
            command_args=args,
            reason=str(object=exc),
            exit_code=exc.errno,
        ) from exc


class _ParseError(Exception):
    """
    Error raised when a file could not be parsed.
    """

    @beartype
    def __init__(self, path: Path, reason: str) -> None:
        """
        Initialize the error.
        """
        message = f"Could not parse {path}: {reason}"
        super().__init__(message)


class _EvaluateError(Exception):
    """
    Error raised when an example could not be evaluated.
    """

    @beartype
    def __init__(
        self,
        command_args: Sequence[str | Path],
        reason: str | None,
        exit_code: int | None,
    ) -> None:
        """
        Initialize the error.
        """
        self.exit_code = exit_code
        self.reason = reason
        self.command_args = command_args
        super().__init__()


@beartype
def _parse_file(
    *,
    sybil: Sybil,
    path: Path,
) -> Document:
    """Parse the file.

    Raises:
        _ParseError: The file could not be parsed.
    """
    try:
        return sybil.parse(path=path)
    except (LexingException, ValueError) as exc:
        reason = str(object=exc)
        raise _ParseError(path=path, reason=reason) from exc


@beartype
def _warn_write_to_code_block_in_group(
    *,
    example: Example,
    modified_example_content: str,
) -> None:
    """
    Warn that writing to a group is not supported.
    """
    unified_diff = difflib.unified_diff(
        a=str(object=example.parsed).lstrip().splitlines(),
        b=modified_example_content.lstrip().splitlines(),
        fromfile="original",
        tofile="modified",
    )
    message = textwrap.dedent(
        text=f"""\
        Writing to a group is not supported.

        A command modified the contents of examples in the group ending on line {example.line} in {Path(example.path).as_posix()}.

        Diff:

        """,  # noqa: E501
    )

    message += "\n".join(unified_diff)
    _log_warning(message=message)


@beartype
def _run_args_against_docs(
    *,
    document_path: Path,
    args: Sequence[str | Path],
    code_block_language: str,
    temporary_file_extension: str | None,
    temporary_file_name_prefix: str | None,
    pad_temporary_file: bool,
    pad_groups: bool,
    verbose: bool,
    skip_markers: Iterable[str],
    group_markers: Iterable[str],
    use_pty: bool,
    markup_language: MarkupLanguage,
) -> None:
    """Run commands on the given file.

    Raises:
        _ParseError: The file could not be parsed.
    """
    temporary_file_extension = _get_temporary_file_extension(
        language=code_block_language,
        given_file_extension=temporary_file_extension,
    )
    content_bytes = document_path.read_bytes()

    charset_matches = charset_normalizer.from_bytes(sequences=content_bytes)
    best_match = charset_matches.best()
    if best_match is None:
        raise _ParseError(
            path=document_path,
            reason="Could not detect encoding.",
        )

    encoding = best_match.encoding
    newline_bytes = _detect_newline(content_bytes=content_bytes)
    newline = (
        newline_bytes.decode(encoding=encoding) if newline_bytes else None
    )

    tempfile_suffixes = (temporary_file_extension,)
    temporary_file_name_prefix = temporary_file_name_prefix or ""

    shell_command_evaluator = ShellCommandEvaluator(
        args=args,
        tempfile_suffixes=tempfile_suffixes,
        pad_file=pad_temporary_file,
        write_to_file=True,
        tempfile_name_prefix=temporary_file_name_prefix,
        newline=newline,
        use_pty=use_pty,
        encoding=encoding,
    )

    shell_command_group_evaluator = ShellCommandEvaluator(
        args=args,
        tempfile_suffixes=tempfile_suffixes,
        pad_file=pad_temporary_file,
        # We do not write to file for grouped code blocks.
        write_to_file=False,
        tempfile_name_prefix=temporary_file_name_prefix,
        newline=newline,
        use_pty=use_pty,
        encoding=encoding,
        on_modify=_warn_write_to_code_block_in_group,
    )

    evaluators: Sequence[Evaluator] = [shell_command_evaluator]
    group_evaluators: Sequence[Evaluator] = [shell_command_group_evaluator]
    if verbose:
        log_command_evaluator = _LogCommandEvaluator(args=args)
        evaluators = [*evaluators, log_command_evaluator]
        group_evaluators = [*group_evaluators, log_command_evaluator]

    evaluator = MultiEvaluator(evaluators=evaluators)
    group_evaluator = MultiEvaluator(evaluators=group_evaluators)

    skip_markers = {*skip_markers, "all"}
    skip_directives = _get_skip_directives(markers=skip_markers)
    skip_parsers = [
        markup_language.skip_parser_cls(
            directive=skip_directive,
        )
        for skip_directive in skip_directives
    ]
    code_block_parsers = [
        markup_language.code_block_parser_cls(
            language=code_block_language,
            evaluator=evaluator,
        )
    ]

    group_markers = {*group_markers, "all"}
    group_directives = _get_group_directives(markers=group_markers)
    group_parsers = [
        markup_language.group_parser_cls(
            directive=group_directive,
            evaluator=group_evaluator,
            pad_groups=pad_groups,
        )
        for group_directive in group_directives
    ]
    parsers: Sequence[Parser] = [
        *code_block_parsers,
        *skip_parsers,
        *group_parsers,
    ]
    sybil = Sybil(parsers=parsers, encoding=encoding)

    document = _parse_file(sybil=sybil, path=document_path)

    try:
        _evaluate_document(document=document, args=args)
    except _EvaluateError as exc:
        if exc.reason:
            message = (
                f"Error running command '{exc.command_args[0]}': {exc.reason}"
            )
            _log_error(message=message)
        sys.exit(exc.exit_code)


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

        By default, code blocks which come just after a comment matching 'skip
        doccmd[all]: next' are skipped (e.g. `.. skip doccmd[all]: next` in
        reStructuredText, `<!--- skip doccmd[all]: next -->` in Markdown, or
        `% skip doccmd[all]: next` in MyST).

        When using this option, those, and code blocks which come just after a
        comment including the given marker are ignored. For example, if the
        given marker is 'type-check', code blocks which come just after a
        comment matching 'skip doccmd[type-check]: next' are also skipped.

        To skip a code block for each of multiple markers, for example to skip
        a code block for the ``type-check`` and ``lint`` markers but not all
        markers, add multiple ``skip doccmd`` comments above the code block.
        """
    ),
    multiple=True,
    callback=_deduplicate,
)
@click.option(
    "group_markers",
    "--group-marker",
    type=str,
    default=None,
    show_default=True,
    required=False,
    help=(
        """\
        The marker used to identify code blocks to be grouped.

        By default, code blocks which come just between comments matching
        'group doccmd[all]: start' and 'group doccmd[all]: end' are grouped
        (e.g. `.. group doccmd[all]: start` in reStructuredText, `<!--- group
        doccmd[all]: start -->` in Markdown, or `% group doccmd[all]: start` in
        MyST).

        When using this option, those, and code blocks which are grouped by
        a comment including the given marker are ignored. For example, if the
        given marker is 'type-check', code blocks which come within comments
        matching 'group doccmd[type-check]: start' and
        'group doccmd[type-check]: end' are also skipped.

        Error messages for grouped code blocks may include lines which do not
        match the document, so code formatters will not work on them.
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
@click.option(
    "--pad-groups/--no-pad-groups",
    is_flag=True,
    default=True,
    show_default=True,
    help=(
        "Maintain line spacing between groups from the source file in the "
        "temporary file. "
        "This is useful for matching line numbers from the output to "
        "the relevant location in the document. "
        "Use --no-pad-groups for formatters - "
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
        "Treat files with this extension (suffix) as reStructuredText. "
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
        "Treat files with this extension (suffix) as MyST. "
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
    "--markdown-extension",
    "markdown_suffixes",
    type=str,
    help=(
        "Files with this extension (suffix) to treat as Markdown. "
        "Give this multiple times to look for multiple extensions. "
        "By default, `.md` is treated as MyST, not Markdown."
    ),
    multiple=True,
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
@click.option(
    "--fail-on-parse-error/--no-fail-on-parse-error",
    "fail_on_parse_error",
    default=False,
    show_default=True,
    type=bool,
    help=(
        "Whether to fail (with exit code 1) if a given file cannot be parsed."
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
    pad_groups: bool,
    verbose: bool,
    skip_markers: Sequence[str],
    group_markers: Sequence[str],
    use_pty_option: _UsePty,
    rst_suffixes: Sequence[str],
    myst_suffixes: Sequence[str],
    markdown_suffixes: Sequence[str],
    max_depth: int,
    exclude_patterns: Sequence[str],
    fail_on_parse_error: bool,
) -> None:
    """Run commands against code blocks in the given documentation files.

    This works with Markdown and reStructuredText files.
    """
    args = shlex.split(s=command)
    use_pty = use_pty_option.use_pty()

    suffix_groups: Mapping[MarkupLanguage, Sequence[str]] = {
        MyST: myst_suffixes,
        ReStructuredText: rst_suffixes,
        Markdown: markdown_suffixes,
    }

    _validate_file_suffix_overlaps(suffix_groups=suffix_groups)

    file_paths = _get_file_paths(
        document_paths=document_paths,
        file_suffixes=[
            suffix
            for suffixes in suffix_groups.values()
            for suffix in suffixes
        ],
        max_depth=max_depth,
        exclude_patterns=exclude_patterns,
    )

    suffix_map = {
        value: key for key, values in suffix_groups.items() for value in values
    }

    for document_path in document_paths:
        if document_path.is_file() and document_path.suffix not in suffix_map:
            message = f"Markup language not known for {document_path}."
            raise click.UsageError(message=message)

    if verbose:
        _log_info(
            message="Using PTY for running commands."
            if use_pty
            else "Not using PTY for running commands."
        )

    for file_path in file_paths:
        for code_block_language in languages:
            markup_language = suffix_map[file_path.suffix]
            try:
                _run_args_against_docs(
                    args=args,
                    document_path=file_path,
                    code_block_language=code_block_language,
                    pad_temporary_file=pad_file,
                    pad_groups=pad_groups,
                    verbose=verbose,
                    temporary_file_extension=temporary_file_extension,
                    temporary_file_name_prefix=temporary_file_name_prefix,
                    skip_markers=skip_markers,
                    group_markers=group_markers,
                    use_pty=use_pty,
                    markup_language=markup_language,
                )
            except _ParseError as exc:
                _log_error(message=str(object=exc))
                if fail_on_parse_error:
                    sys.exit(1)
