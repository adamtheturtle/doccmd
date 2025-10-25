"""
CLI to run commands on the given files.
"""

import difflib
import platform
import shlex
import subprocess
import sys
import textwrap
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum, auto, unique
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import TypeVar, overload

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
    MARKDOWN,
    MYST,
    RESTRUCTUREDTEXT,
    MarkupLanguage,
)

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
    ctx: click.Context | None,
    param: click.Parameter | None,
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
    ctx: click.Context | None,
    param: click.Parameter | None,
    value: str,
) -> str: ...


@overload
def _validate_file_extension(
    ctx: click.Context | None,
    param: click.Parameter | None,
    value: None,
) -> None: ...


@beartype
def _validate_file_extension(
    ctx: click.Context | None,
    param: click.Parameter | None,
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
def _validate_given_files_have_known_suffixes(
    *,
    given_files: Iterable[Path],
    known_suffixes: Iterable[str],
) -> None:
    """
    Validate that the given files have known suffixes.
    """
    given_files_unknown_suffix = [
        document_path
        for document_path in given_files
        if document_path.suffix not in known_suffixes
    ]

    for given_file_unknown_suffix in given_files_unknown_suffix:
        message = f"Markup language not known for {given_file_unknown_suffix}."
        raise click.UsageError(message=message)


@beartype
def _validate_no_empty_string(
    ctx: click.Context | None,
    param: click.Parameter | None,
    value: str,
) -> str:
    """
    Validate that the input strings are not empty.
    """
    if not value:
        msg = "This value cannot be empty."
        raise click.BadParameter(message=msg, ctx=ctx, param=param)
    return value


_ClickCallback = Callable[[click.Context | None, click.Parameter | None, T], T]


@beartype
def _sequence_validator(
    validator: _ClickCallback[T],
) -> _ClickCallback[Sequence[T]]:
    """
    Wrap a single-value validator to apply it to a sequence of values.
    """

    def callback(
        ctx: click.Context | None,
        param: click.Parameter | None,
        value: Sequence[T],
    ) -> Sequence[T]:
        """
        Apply the validators to the value.
        """
        return_values: tuple[T, ...] = ()
        for item in value:
            returned_value = validator(ctx, param, item)
            return_values = (*return_values, returned_value)
        return return_values

    return callback


@beartype
def _click_multi_callback(
    callbacks: Sequence[_ClickCallback[T]],
) -> _ClickCallback[T]:
    """
    Create a Click-compatible callback that applies a sequence of callbacks to
    an option value.
    """

    def callback(
        ctx: click.Context | None,
        param: click.Parameter | None,
        value: T,
    ) -> T:
        """
        Apply the validators to the value.
        """
        for callback in callbacks:
            value = callback(ctx, param, value)
        return value

    return callback


_validate_file_extensions: _ClickCallback[Sequence[str]] = (
    _click_multi_callback(
        callbacks=[
            _deduplicate,
            _sequence_validator(validator=_validate_file_extension),
        ]
    )
)


@beartype
def _get_file_paths(
    *,
    document_paths: Sequence[Path],
    file_suffixes: Iterable[str],
    max_depth: int,
    exclude_patterns: Iterable[str],
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

    def __str__(self) -> str:  # pragma: no cover
        """String representation of the enum value.

        This is used by ``sphinx-click`` to render the default as an argument.
        """
        return self.name.lower()

    def __repr__(self) -> str:  # pragma: no cover
        """String representation of the enum value.

        This is used by ``sphinx-click`` to render the options as an argument.
        """
        return self.name.lower()

    def use_pty(self) -> bool:
        """
        Whether to use a pseudo-terminal.
        """
        if self is _UsePty.DETECT:
            return sys.stdout.isatty() and platform.system() != "Windows"
        return {
            _UsePty.YES: True,
            _UsePty.NO: False,
        }[self]


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
def _get_skip_directives(markers: Iterable[str]) -> Iterable[str]:
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


@beartype
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
class _GroupModifiedError(Exception):
    """
    Error raised when there was an attempt to modify a code block in a group.
    """

    def __init__(
        self,
        *,
        example: Example,
        modified_example_content: str,
    ) -> None:
        """
        Initialize the error.
        """
        self._example = example
        self._modified_example_content = modified_example_content

    def __str__(self) -> str:
        """
        Get the string representation of the error.
        """
        unified_diff = difflib.unified_diff(
            a=str(object=self._example.parsed).lstrip().splitlines(),
            b=self._modified_example_content.lstrip().splitlines(),
            fromfile="original",
            tofile="modified",
        )
        message = textwrap.dedent(
            text=f"""\
            Writing to a group is not supported.

            A command modified the contents of examples in the group ending on line {self._example.line} in {Path(self._example.path).as_posix()}.

            Diff:

            """,  # noqa: E501
        )

        message += "\n".join(unified_diff)
        return message


@dataclass
class _CollectedError:
    """
    Error collected during continue-on-error mode.
    """

    message: str
    exit_code: int


@beartype
def _raise_group_modified(
    *,
    example: Example,
    modified_example_content: str,
) -> None:
    """
    Raise an error when there was an attempt to modify a code block in a group.
    """
    raise _GroupModifiedError(
        example=example,
        modified_example_content=modified_example_content,
    )


@beartype
def _get_encoding(*, document_path: Path) -> str | None:
    """
    Get the encoding of the file.
    """
    content_bytes = document_path.read_bytes()
    charset_matches = charset_normalizer.from_bytes(sequences=content_bytes)
    best_match = charset_matches.best()
    if best_match is None:
        return None
    return best_match.encoding


@beartype
def _get_sybil(
    *,
    encoding: str,
    args: Sequence[str | Path],
    code_block_languages: Sequence[str],
    temporary_file_extension: str,
    temporary_file_name_prefix: str,
    pad_temporary_file: bool,
    pad_groups: bool,
    skip_directives: Iterable[str],
    group_directives: Iterable[str],
    use_pty: bool,
    markup_language: MarkupLanguage,
    log_command_evaluators: Sequence[_LogCommandEvaluator],
    newline: str | None,
    parse_sphinx_jinja2: bool,
) -> Sybil:
    """
    Get a Sybil for running commands on the given file.
    """
    tempfile_suffixes = (temporary_file_extension,)

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
        on_modify=_raise_group_modified,
    )

    evaluator = MultiEvaluator(
        evaluators=[*log_command_evaluators, shell_command_evaluator],
    )
    group_evaluator = MultiEvaluator(
        evaluators=[*log_command_evaluators, shell_command_group_evaluator],
    )

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
        for code_block_language in code_block_languages
    ]

    group_parsers = [
        markup_language.group_parser_cls(
            directive=group_directive,
            evaluator=group_evaluator,
            pad_groups=pad_groups,
        )
        for group_directive in group_directives
    ]

    sphinx_jinja2_parsers = (
        [
            markup_language.sphinx_jinja_parser_cls(
                evaluator=evaluator,
            )
        ]
        if markup_language.sphinx_jinja_parser_cls and parse_sphinx_jinja2
        else []
    )

    return Sybil(
        parsers=(
            *code_block_parsers,
            *sphinx_jinja2_parsers,
            *skip_parsers,
            *group_parsers,
        ),
        encoding=encoding,
    )


@click.command(name="doccmd")
@click.option(
    "languages",
    "-l",
    "--language",
    type=str,
    required=False,
    help=(
        "Run `command` against code blocks for this language. "
        "Give multiple times for multiple languages. "
        "If this is not given, no code blocks are run, unless "
        "`--sphinx-jinja2` is given."
    ),
    multiple=True,
    callback=_click_multi_callback(
        callbacks=[
            _deduplicate,
            _sequence_validator(validator=_validate_no_empty_string),
        ]
    ),
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
    type=click.Choice(choices=_UsePty, case_sensitive=False),
    default=_UsePty.DETECT,
    show_default=True,
    help=(
        "Whether to use a pseudo-terminal for running commands. "
        "Using a PTY can be useful for getting color output from commands, "
        "but can also break in some environments. "
        "\n\n"
        "'yes': Always use PTY (not supported on Windows). "
        "\n\n"
        "'no': Never use PTY - useful when doccmd detects that it is running "
        "in a TTY outside of Windows but the environment does not support "
        "PTYs. "
        "\n\n"
        "'detect': Automatically determine based on environment (default)."
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
@click.option(
    "--fail-on-group-write/--no-fail-on-group-write",
    "fail_on_group_write",
    default=True,
    show_default=True,
    type=bool,
    help=(
        "Whether to fail (with exit code 1) if a command (e.g. a formatter) "
        "tries to change code within a grouped code block. "
        "``doccmd`` does not support writing to grouped code blocks."
    ),
)
@click.option(
    "--sphinx-jinja2/--no-sphinx-jinja2",
    "sphinx_jinja2",
    default=False,
    show_default=True,
    help=(
        "Whether to parse `sphinx-jinja2` blocks. "
        "This is useful for evaluating code blocks with Jinja2 "
        "templates used in Sphinx documentation. "
        "This is supported for MyST and reStructuredText files only."
    ),
)
@click.option(
    "--continue-on-error/--no-continue-on-error",
    "continue_on_error",
    default=False,
    show_default=True,
    type=bool,
    help=(
        "Continue executing across all files even when errors occur. "
        "Collects and displays all errors found, then returns a non-zero "
        "exit code if any command invocation failed. "
        "Useful for seeing all linting errors in large projects."
    ),
)
@beartype
def main(
    *,
    languages: Sequence[str],
    command: str,
    document_paths: Sequence[Path],
    temporary_file_extension: str | None,
    temporary_file_name_prefix: str,
    pad_file: bool,
    pad_groups: bool,
    verbose: bool,
    skip_markers: Iterable[str],
    group_markers: Iterable[str],
    use_pty_option: _UsePty,
    rst_suffixes: Sequence[str],
    myst_suffixes: Sequence[str],
    markdown_suffixes: Sequence[str],
    max_depth: int,
    exclude_patterns: Sequence[str],
    fail_on_parse_error: bool,
    fail_on_group_write: bool,
    sphinx_jinja2: bool,
    continue_on_error: bool,
) -> None:
    """Run commands against code blocks in the given documentation files.

    This works with Markdown and reStructuredText files.
    """
    args = shlex.split(s=command)
    use_pty = use_pty_option.use_pty()

    suffix_groups: Mapping[MarkupLanguage, Sequence[str]] = {
        MYST: myst_suffixes,
        RESTRUCTUREDTEXT: rst_suffixes,
        MARKDOWN: markdown_suffixes,
    }

    _validate_file_suffix_overlaps(suffix_groups=suffix_groups)

    suffix_map = {
        value: key for key, values in suffix_groups.items() for value in values
    }

    _validate_given_files_have_known_suffixes(
        given_files=[
            document_path
            for document_path in document_paths
            if document_path.is_file()
        ],
        known_suffixes=suffix_map.keys(),
    )

    file_paths = _get_file_paths(
        document_paths=document_paths,
        file_suffixes=suffix_map.keys(),
        max_depth=max_depth,
        exclude_patterns=exclude_patterns,
    )

    log_command_evaluators = []
    if verbose:
        _log_info(
            message="Using PTY for running commands."
            if use_pty
            else "Not using PTY for running commands."
        )
        log_command_evaluators = [_LogCommandEvaluator(args=args)]

    skip_markers = {*skip_markers, "all"}
    skip_directives = _get_skip_directives(markers=skip_markers)

    group_markers = {*group_markers, "all"}
    group_directives = _get_group_directives(markers=group_markers)

    given_temporary_file_extension = temporary_file_extension

    collected_errors: list[_CollectedError] = []

    for file_path in file_paths:
        markup_language = suffix_map[file_path.suffix]
        encoding = _get_encoding(document_path=file_path)
        if encoding is None:
            could_not_determine_encoding_msg = (
                f"Could not determine encoding for {file_path}."
            )
            _log_error(message=could_not_determine_encoding_msg)
            if fail_on_parse_error:
                if continue_on_error:
                    collected_errors.append(
                        _CollectedError(
                            message=could_not_determine_encoding_msg,
                            exit_code=1,
                        )
                    )
                    continue
                sys.exit(1)
            continue

        content_bytes = file_path.read_bytes()
        newline_bytes = _detect_newline(content_bytes=content_bytes)
        newline = (
            newline_bytes.decode(encoding=encoding) if newline_bytes else None
        )
        sybils: Sequence[Sybil] = []
        for code_block_language in languages:
            temporary_file_extension = _get_temporary_file_extension(
                language=code_block_language,
                given_file_extension=given_temporary_file_extension,
            )
            sybil = _get_sybil(
                args=args,
                code_block_languages=[code_block_language],
                pad_temporary_file=pad_file,
                pad_groups=pad_groups,
                temporary_file_extension=temporary_file_extension,
                temporary_file_name_prefix=temporary_file_name_prefix,
                skip_directives=skip_directives,
                group_directives=group_directives,
                use_pty=use_pty,
                markup_language=markup_language,
                encoding=encoding,
                log_command_evaluators=log_command_evaluators,
                newline=newline,
                parse_sphinx_jinja2=False,
            )
            sybils = [*sybils, sybil]

        if sphinx_jinja2:
            temporary_file_extension = (
                given_temporary_file_extension or ".jinja"
            )
            sybil = _get_sybil(
                args=args,
                code_block_languages=[],
                pad_temporary_file=pad_file,
                pad_groups=pad_groups,
                temporary_file_extension=temporary_file_extension,
                temporary_file_name_prefix=temporary_file_name_prefix,
                skip_directives=skip_directives,
                group_directives=group_directives,
                use_pty=use_pty,
                markup_language=markup_language,
                encoding=encoding,
                log_command_evaluators=log_command_evaluators,
                newline=newline,
                parse_sphinx_jinja2=True,
            )
            sybils = [*sybils, sybil]

        for sybil in sybils:
            try:
                document = sybil.parse(path=file_path)
            except (LexingException, ValueError) as exc:
                message = f"Could not parse {file_path}: {exc}"
                _log_error(message=message)
                if fail_on_parse_error:
                    if continue_on_error:
                        collected_errors.append(
                            _CollectedError(message=message, exit_code=1)
                        )
                        continue
                    sys.exit(1)
                continue

            try:
                _evaluate_document(document=document, args=args)
            except _GroupModifiedError as exc:
                if fail_on_group_write:
                    error_message = str(object=exc)
                    _log_error(message=error_message)
                    if continue_on_error:
                        collected_errors.append(
                            _CollectedError(message=error_message, exit_code=1)
                        )
                        continue
                    sys.exit(1)
                _log_warning(message=str(object=exc))
            except _EvaluateError as exc:
                error_msg: str | None = None
                if exc.reason:
                    error_msg = (
                        f"Error running command '{exc.command_args[0]}': "
                        f"{exc.reason}"
                    )
                    _log_error(message=error_msg)

                if continue_on_error:
                    if error_msg:
                        collected_errors.append(
                            _CollectedError(
                                message=error_msg,
                                exit_code=exc.exit_code
                                if exc.exit_code
                                else 1,
                            )
                        )
                    else:
                        collected_errors.append(
                            _CollectedError(
                                message="Command failed",
                                exit_code=exc.exit_code
                                if exc.exit_code
                                else 1,
                            )
                        )
                else:
                    sys.exit(exc.exit_code)

    if collected_errors:
        max_exit_code = max(error.exit_code for error in collected_errors)
        sys.exit(max_exit_code)
