"""CLI to run commands on the given files."""

import difflib
import os
import platform
import shlex
import subprocess
import sys
import textwrap
from collections.abc import Callable, Iterable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from enum import Enum, auto, unique
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import TypeVar
from uuid import uuid4

import charset_normalizer
import click
import cloup
from beartype import beartype
from click_compose import (
    deduplicate as _deduplicate,
)
from click_compose import (
    multi_callback,
    sequence_validator,
)
from dulwich.errors import NotGitRepository
from dulwich.ignore import IgnoreFilterManager
from dulwich.repo import Repo
from pygments.lexers import get_all_lexers
from sybil import Sybil
from sybil.document import Document
from sybil.example import Example
from sybil.parsers.abstract.lexers import LexingException
from sybil_extras.evaluators.multi import MultiEvaluator
from sybil_extras.evaluators.shell_evaluator import ShellCommandEvaluator
from sybil_extras.languages import (
    DJOT,
    MARKDOWN,
    MDX,
    MYST,
    NORG,
    RESTRUCTUREDTEXT,
    MarkupLanguage,
)
from sybil_extras.parsers.mdx.attribute_grouped_source import (
    AttributeGroupedSourceParser as MdxAttributeGroupedSourceParser,
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
class _TempFilePathMaker:
    """Create temporary file paths for examples."""

    def __init__(
        self,
        *,
        prefix: str,
        suffix: str,
        template: str,
    ) -> None:
        """Initialize with the prefix, suffix, and template.

        Args:
            prefix: The prefix for the temporary file name.
            suffix: The suffix (extension) for the temporary file.
            template: The template for the temporary file name.
        """
        self._prefix = prefix
        self._suffix = suffix
        self._template = template

    def __call__(
        self,
        *,
        example: Example,
    ) -> Path:
        """Create a temporary file path for an example.

        Args:
            example: The example to create a temporary file for.

        Returns:
            A path to the temporary file.
        """
        source_path = Path(example.path)
        # Sanitize the source filename (replace dots and dashes with _)
        # Use .name (not .stem) to include the extension in the sanitized name
        sanitized_source = source_path.name.replace(".", "_").replace("-", "_")
        unique_id = uuid4().hex[:4]
        filename = self._template.format(
            prefix=self._prefix,
            source=sanitized_source,
            line=example.line,
            unique=unique_id,
            suffix=self._suffix,
        )
        return source_path.parent / filename


@beartype
class _LogCommandEvaluator:
    """Log a command before running it."""

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
        """Log the command before running it."""
        command_str = shlex.join(
            split_command=[str(object=item) for item in self._args],
        )
        running_command_message = (
            f"Running '{command_str}' on code block at "
            f"{example.path}:{example.line}"
        )
        _log_info(message=running_command_message)


@beartype
def _validate_file_extension(
    ctx: click.Context | None,
    param: click.Parameter | None,
    value: str,
) -> str:
    """Validate that the input string starts with a dot."""
    if not value.startswith("."):
        message = f"'{value}' does not start with a '.'."
        raise click.BadParameter(message=message, ctx=ctx, param=param)
    return value


@beartype
def _validate_file_extension_or_none(
    ctx: click.Context | None,
    param: click.Parameter | None,
    value: str | None,
) -> str | None:
    """Validate that the input string starts with a dot."""
    if value is None:
        return value
    return _validate_file_extension(ctx=ctx, param=param, value=value)


@beartype
def _validate_template(
    ctx: click.Context | None,
    param: click.Parameter | None,
    value: str,
) -> str:
    """Validate that the template is valid and contains required
    placeholders.
    """
    # Use a unique marker for suffix that won't appear in user templates
    suffix_marker = f".{uuid4().hex}"
    placeholder_values = {
        "prefix": "test",
        "source": "test",
        "line": 1,
        "unique": "test",
        "suffix": suffix_marker,
    }
    # Try to format the template to catch invalid placeholders
    try:
        formatted = value.format(**placeholder_values)
    except KeyError as exc:
        valid_names = ", ".join(sorted(placeholder_values.keys()))
        message = (
            f"Invalid placeholder in template: {exc}. "
            f"Valid placeholders are: {{{valid_names}}}."
        )
        raise click.BadParameter(
            message=message,
            ctx=ctx,
            param=param,
        ) from exc
    except (ValueError, IndexError, TypeError, AttributeError) as exc:
        message = f"Malformed template: {exc}"
        raise click.BadParameter(
            message=message,
            ctx=ctx,
            param=param,
        ) from exc

    # Verify suffix placeholder is actually used (not escaped as {{suffix}})
    if suffix_marker not in formatted:
        message = (
            "Template must contain '{suffix}' placeholder "
            "for the file extension."
        )
        raise click.BadParameter(message=message, ctx=ctx, param=param)

    return value


@beartype
def _validate_given_files_have_known_suffixes(
    *,
    given_files: Iterable[Path],
    known_suffixes: Iterable[str],
) -> None:
    """Validate that the given files have known suffixes."""
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
    """Validate that the input strings are not empty."""
    if not value:
        msg = "This value cannot be empty."
        raise click.BadParameter(message=msg, ctx=ctx, param=param)
    return value


_ClickCallback = Callable[[click.Context | None, click.Parameter | None, T], T]


_validate_file_extensions: _ClickCallback[Sequence[str]] = multi_callback(
    callbacks=[
        _deduplicate,
        sequence_validator(validator=_validate_file_extension),
    ]
)


@beartype
def _get_file_paths(
    *,
    document_paths: Sequence[Path],
    file_suffixes: Iterable[str],
    max_depth: int,
    exclude_patterns: Iterable[str],
    respect_gitignore: bool,
) -> Sequence[Path]:
    """
    Get the file paths from the given document paths (files and
    directories).
    """
    file_paths: dict[Path, bool] = {}

    # Cache ignore managers keyed by repo path to avoid recomputing
    # for multiple subdirectories in the same repository
    ignore_managers: dict[Path, IgnoreFilterManager] = {}

    for path in document_paths:
        if path.is_file():
            file_paths[path] = True
            continue

        # Get ignore manager for this directory if respecting gitignore
        ignore_manager: IgnoreFilterManager | None = None
        repo_path: Path | None = None
        if respect_gitignore:
            # Check cache first to avoid creating new IgnoreFilterManager
            # objects for directories in the same repository
            try:
                repo = Repo.discover(start=str(object=path.resolve()))
                repo_path = Path(repo.path).resolve()
                if repo_path in ignore_managers:
                    ignore_manager = ignore_managers[repo_path]
                else:
                    ignore_manager = IgnoreFilterManager.from_repo(repo=repo)
                    ignore_managers[repo_path] = ignore_manager
            except NotGitRepository:
                pass

        for file_suffix in file_suffixes:
            new_file_paths = (
                path_part
                for path_part in path.rglob(pattern=f"*{file_suffix}")
                if len(path_part.relative_to(path).parts) <= max_depth
            )
            for new_file_path in new_file_paths:
                if not new_file_path.is_file():
                    continue

                # Check exclude patterns
                if any(
                    new_file_path.match(path_pattern=pattern)
                    for pattern in exclude_patterns
                ):
                    continue

                # Check gitignore if enabled
                if ignore_manager is not None and repo_path is not None:
                    resolved_file = new_file_path.resolve()
                    # Skip gitignore check for symlinks pointing outside the
                    # git repository
                    if not resolved_file.is_relative_to(repo_path):
                        file_paths[new_file_path] = True
                        continue
                    relative_path = resolved_file.relative_to(repo_path)
                    relative_path_str = str(object=relative_path)
                    if ignore_manager.is_ignored(path=relative_path_str):
                        continue

                file_paths[new_file_path] = True

    return tuple(file_paths.keys())


@beartype
def _validate_file_suffix_overlaps(
    *,
    suffix_groups: Mapping[MarkupLanguage, Iterable[str]],
) -> None:
    """Validate that the given file suffixes do not overlap."""
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
    """Choices for the use of a pseudo-terminal."""

    YES = auto()
    NO = auto()
    DETECT = auto()

    def __str__(self) -> str:  # pragma: no cover
        """String representation of the value.

        This is used by ``sphinx-click`` to render the default when used as a
        ``click.Choices`` choice.
        """
        return self.name.lower()

    def __repr__(self) -> str:  # pragma: no cover
        """String representation of the value.

        This is used by ``sphinx-click`` to render the option when used as a
        ``click.Choices`` choice.
        """
        return self.name.lower()

    def use_pty(self) -> bool:
        """Whether to use a pseudo-terminal."""
        if self is _UsePty.DETECT:
            return sys.stdout.isatty() and platform.system() != "Windows"
        return {
            _UsePty.YES: True,
            _UsePty.NO: False,
        }[self]


@beartype
def _log_info(message: str) -> None:
    """Log an info message."""
    styled_message = click.style(text=message, fg="green")
    click.echo(message=styled_message, err=True)


@beartype
def _log_warning(message: str) -> None:
    """Log an error message."""
    styled_message = click.style(text=message, fg="yellow")
    click.echo(message=styled_message, err=True)


@beartype
def _log_error(message: str) -> None:
    """Log an error message."""
    styled_message = click.style(text=message, fg="red")
    click.echo(message=styled_message, err=True)


@beartype
def _detect_newline(content_bytes: bytes) -> bytes | None:
    """Detect the newline character used in the content."""
    for newline in (b"\r\n", b"\n", b"\r"):
        if newline in content_bytes:
            return newline
    return None


@beartype
def _map_languages_to_suffix() -> dict[str, str]:
    """Map programming languages to their corresponding file extension."""
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
    """Group directives based on the provided markers."""
    directives: Sequence[str] = []

    for marker in markers:
        directive = rf"group doccmd[{marker}]"
        directives = [*directives, directive]
    return directives


@beartype
def _get_skip_directives(markers: Iterable[str]) -> Iterable[str]:
    """Skip directives based on the provided markers."""
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
    """Get the file suffix, either from input or based on the language."""
    if given_file_extension is None:
        language_to_suffix = _map_languages_to_suffix()
        given_file_extension = language_to_suffix.get(language.lower(), ".txt")

    return given_file_extension


@beartype
def _resolve_workers(*, requested_workers: int) -> int:
    """Resolve the input worker count, auto-detecting CPUs when zero."""
    if requested_workers != 0:
        return requested_workers

    detected_cpus = os.cpu_count()
    if not detected_cpus or detected_cpus < 1:
        return 1
    return detected_cpus


@beartype
def _evaluate_document(
    *,
    document: Document,
    example_workers: int,
) -> None:
    """Evaluate the document."""
    examples = tuple(document.examples())
    if example_workers == 1 or len(examples) in {0, 1}:
        for example in examples:
            example.evaluate()
        return

    max_workers = min(example_workers, len(examples))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(example.evaluate) for example in examples]
        for future in as_completed(fs=futures):
            future.result()


@beartype
class _GroupModifiedError(Exception):
    """
    Error raised when there was an attempt to modify a code block in a
    group.
    """

    def __init__(
        self,
        *,
        example: Example,
        modified_example_content: str,
    ) -> None:
        """Initialize the error."""
        self._example = example
        self._modified_example_content = modified_example_content

    def __str__(self) -> str:
        """Get the string representation of the error."""
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
    """Error collected during continue-on-error mode."""

    message: str
    exit_code: int


class _FatalProcessingError(Exception):
    """
    Error raised when processing a document requires exiting
    immediately.
    """

    def __init__(self, exit_code: int) -> None:
        """Capture the exit code doccmd should terminate with."""
        self.exit_code = exit_code
        super().__init__()


@beartype
def _handle_error(
    *,
    message: str,
    exit_code: int,
    continue_on_error: bool,
    exc: Exception | None = None,
) -> _CollectedError:
    """Handle an error by either returning it or raising a fatal error."""
    if continue_on_error:
        return _CollectedError(message=message, exit_code=exit_code)
    raise _FatalProcessingError(exit_code=exit_code) from exc


@beartype
def _process_file_path(
    *,
    file_path: Path,
    suffix_map: Mapping[str, MarkupLanguage],
    args: Sequence[str | Path],
    languages: Sequence[str],
    pad_file: bool,
    write_to_file: bool,
    pad_groups: bool,
    temporary_file_name_prefix: str,
    temporary_file_name_template: str,
    given_temporary_file_extension: str | None,
    skip_directives: Iterable[str],
    group_markers: Iterable[str],
    group_file: bool,
    group_mdx_by_attribute: str | None,
    use_pty: bool,
    log_command_evaluators: Sequence[_LogCommandEvaluator],
    sphinx_jinja2: bool,
    fail_on_parse_error: bool,
    fail_on_group_write: bool,
    continue_on_error: bool,
    example_workers: int,
) -> list[_CollectedError]:
    """Process a single documentation file."""
    local_errors: list[_CollectedError] = []
    markup_language = suffix_map[file_path.suffix]
    encoding = _get_encoding(document_path=file_path)
    if encoding is None:
        could_not_determine_encoding_msg = (
            f"Could not determine encoding for {file_path}."
        )
        _log_error(message=could_not_determine_encoding_msg)
        if fail_on_parse_error:
            local_errors.append(
                _handle_error(
                    message=could_not_determine_encoding_msg,
                    exit_code=1,
                    continue_on_error=continue_on_error,
                )
            )
        return local_errors

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
            write_to_file=write_to_file,
            pad_groups=pad_groups,
            temporary_file_extension=temporary_file_extension,
            temporary_file_name_prefix=temporary_file_name_prefix,
            temporary_file_name_template=temporary_file_name_template,
            skip_directives=skip_directives,
            group_markers=group_markers,
            group_file=group_file,
            group_mdx_by_attribute=group_mdx_by_attribute,
            use_pty=use_pty,
            markup_language=markup_language,
            encoding=encoding,
            log_command_evaluators=log_command_evaluators,
            newline=newline,
            parse_sphinx_jinja2=False,
        )
        sybils = [*sybils, sybil]

    if sphinx_jinja2:
        temporary_file_extension = given_temporary_file_extension or ".jinja"
        sybil = _get_sybil(
            args=args,
            code_block_languages=[],
            pad_temporary_file=pad_file,
            write_to_file=write_to_file,
            pad_groups=pad_groups,
            temporary_file_extension=temporary_file_extension,
            temporary_file_name_prefix=temporary_file_name_prefix,
            temporary_file_name_template=temporary_file_name_template,
            skip_directives=skip_directives,
            group_markers=group_markers,
            group_file=group_file,
            group_mdx_by_attribute=group_mdx_by_attribute,
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
                local_errors.append(
                    _handle_error(
                        message=message,
                        exit_code=1,
                        continue_on_error=continue_on_error,
                        exc=exc,
                    )
                )
            continue

        try:
            _evaluate_document(
                document=document,
                example_workers=example_workers,
            )
        except _GroupModifiedError as exc:
            if fail_on_group_write:
                error_message = str(object=exc)
                _log_error(message=error_message)
                local_errors.append(
                    _handle_error(
                        message=error_message,
                        exit_code=1,
                        continue_on_error=continue_on_error,
                        exc=exc,
                    )
                )
                continue
            _log_warning(message=str(object=exc))
        except ValueError as exc:
            error_msg = f"Error running command '{args[0]}': {exc}"
            _log_error(message=error_msg)
            local_errors.append(
                _handle_error(
                    message=error_msg,
                    exit_code=1,
                    continue_on_error=continue_on_error,
                    exc=exc,
                )
            )
        except subprocess.CalledProcessError as exc:
            local_errors.append(
                _handle_error(
                    message="Command failed",
                    exit_code=exc.returncode,
                    continue_on_error=continue_on_error,
                    exc=exc,
                )
            )
        except OSError as exc:
            error_msg = f"Error running command '{args[0]}': {exc}"
            _log_error(message=error_msg)
            exit_code = exc.errno if exc.errno else 1
            local_errors.append(
                _handle_error(
                    message=error_msg,
                    exit_code=exit_code,
                    continue_on_error=continue_on_error,
                    exc=exc,
                )
            )

    return local_errors


@beartype
def _raise_group_modified(
    *,
    example: Example,
    modified_example_content: str,
) -> None:
    """
    Raise an error when there was an attempt to modify a code block in a
    group.
    """
    raise _GroupModifiedError(
        example=example,
        modified_example_content=modified_example_content,
    )


@beartype
def _get_encoding(*, document_path: Path) -> str | None:
    """Get the encoding of the file."""
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
    temporary_file_name_template: str,
    pad_temporary_file: bool,
    write_to_file: bool,
    pad_groups: bool,
    skip_directives: Iterable[str],
    group_markers: Iterable[str],
    group_file: bool,
    group_mdx_by_attribute: str | None,
    use_pty: bool,
    markup_language: MarkupLanguage,
    log_command_evaluators: Sequence[_LogCommandEvaluator],
    newline: str | None,
    parse_sphinx_jinja2: bool,
) -> Sybil:
    """Get a Sybil for running commands on the given file."""
    # Add default "all" marker if:
    # - Not using group_file
    # - AND (not using group_mdx_by_attribute OR this is not an MDX file)
    # This ensures MDX files with attribute grouping don't process
    # 'group doccmd[all]' directives, while other file types still do.
    default_group_markers: set[str] = (
        {"all"}
        if not group_file
        and (group_mdx_by_attribute is None or markup_language != MDX)
        else set()
    )
    all_group_markers = {*group_markers, *default_group_markers}
    group_directives = _get_group_directives(markers=all_group_markers)

    temp_file_path_maker = _TempFilePathMaker(
        prefix=temporary_file_name_prefix,
        suffix=temporary_file_extension,
        template=temporary_file_name_template,
    )

    shell_command_evaluator = ShellCommandEvaluator(
        args=args,
        temp_file_path_maker=temp_file_path_maker,
        pad_file=pad_temporary_file,
        write_to_file=write_to_file,
        newline=newline,
        use_pty=use_pty,
        encoding=encoding,
    )

    shell_command_group_evaluator = ShellCommandEvaluator(
        args=args,
        temp_file_path_maker=temp_file_path_maker,
        pad_file=pad_temporary_file,
        # We do not write to file for grouped code blocks.
        write_to_file=False,
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

    mdx_attribute_grouped_parsers: list[MdxAttributeGroupedSourceParser] = []

    if group_file:
        code_block_parsers = [
            markup_language.code_block_parser_cls(
                language=code_block_language,
            )
            for code_block_language in code_block_languages
        ]

        group_all_parsers = (
            [
                markup_language.group_all_parser_cls(
                    evaluator=group_evaluator,
                    pad_groups=pad_groups,
                )
            ]
            if code_block_languages
            else []
        )
    elif group_mdx_by_attribute is not None and markup_language == MDX:
        # For MDX files with attribute-based grouping:
        # Create an AttributeGroupedSourceParser that handles all blocks:
        # - Blocks with the grouping attribute are grouped by attribute value
        # - Blocks without the attribute are processed individually
        code_block_parsers = []
        for code_block_language in code_block_languages:
            code_block_parser = markup_language.code_block_parser_cls(
                language=code_block_language,
            )
            mdx_attribute_grouped_parsers.append(
                MdxAttributeGroupedSourceParser(
                    code_block_parser=code_block_parser,
                    evaluator=group_evaluator,
                    attribute_name=group_mdx_by_attribute,
                    pad_groups=pad_groups,
                    ungrouped_evaluator=evaluator,
                )
            )
        group_all_parsers = []
    else:
        code_block_parsers = [
            markup_language.code_block_parser_cls(
                language=code_block_language,
                evaluator=evaluator,
            )
            for code_block_language in code_block_languages
        ]
        group_all_parsers = []

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
            *group_all_parsers,
            *mdx_attribute_grouped_parsers,
        ),
        encoding=encoding,
    )


@cloup.command(name="doccmd", show_constraints=True)
@cloup.option_group(
    "Required options",
    cloup.option(
        "command",
        "-c",
        "--command",
        type=str,
        required=True,
        help="The command to run against code blocks.",
    ),
)
@cloup.option_group(
    "Code block selection",
    cloup.option(
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
        callback=multi_callback(
            callbacks=[
                _deduplicate,
                sequence_validator(validator=_validate_no_empty_string),
            ]
        ),
    ),
    cloup.option(
        "skip_markers",
        "--skip-marker",
        type=str,
        default=None,
        show_default=True,
        required=False,
        help=(
            """\
            The marker used to identify code blocks to be skipped.

            By default, code blocks which come just after a comment matching
            'skip doccmd[all]: next' are skipped (e.g. `.. skip doccmd[all]:
            next` in reStructuredText, `<!--- skip doccmd[all]: next -->` in
            Markdown or MDX, or `% skip doccmd[all]: next` in MyST).

            When using this option, those, and code blocks which come just
            after a comment including the given marker are ignored. For
            example, if the given marker is 'type-check', code blocks which
            come just after a comment matching 'skip doccmd[type-check]: next'
            are also skipped.

            To skip a code block for each of multiple markers, for example to
            skip a code block for the ``type-check`` and ``lint`` markers but
            not all markers, add multiple ``skip doccmd`` comments above the
            code block.
            """
        ),
        multiple=True,
        callback=_deduplicate,
    ),
    cloup.option(
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
    ),
)
@cloup.option_group(
    "Grouping options",
    cloup.option(
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
            'group doccmd[all]: start' and 'group doccmd[all]: end' are
            grouped (e.g. `.. group doccmd[all]: start` in reStructuredText,
            `<!--- group doccmd[all]: start -->` in Markdown/MDX, or `% group
            doccmd[all]: start` in MyST).

            When using this option, those, and code blocks which are grouped
            by a comment including the given marker are ignored. For example,
            if the given marker is 'type-check', code blocks which come within
            comments matching 'group doccmd[type-check]: start' and
            'group doccmd[type-check]: end' are also skipped.

            Error messages for grouped code blocks may include lines which do
            not match the document, so code formatters will not work on them.
            """
        ),
        multiple=True,
        callback=_deduplicate,
    ),
    cloup.option(
        "--group-file/--no-group-file",
        "group_file",
        default=False,
        show_default=True,
        help=(
            "Automatically group all code blocks within each file. "
            "When enabled, all code blocks in a file are treated as a single "
            "group and executed together, without requiring explicit group "
            "directives. This is useful for files where code blocks are "
            "designed for sequential execution. "
            "Error messages for grouped code blocks may include lines which "
            "do not match the document, so code formatters will not work on "
            "them."
        ),
    ),
    cloup.option(
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
    ),
    cloup.option(
        "--fail-on-group-write/--no-fail-on-group-write",
        "fail_on_group_write",
        default=True,
        show_default=True,
        type=bool,
        help=(
            "Whether to fail (with exit code 1) if a command (e.g. a "
            "formatter) tries to change code within a grouped code block. "
            "``doccmd`` does not support writing to grouped code blocks."
        ),
    ),
    cloup.option(
        "group_mdx_by_attribute",
        "--group-mdx-by-attribute",
        type=str,
        default=None,
        show_default=True,
        required=False,
        help=(
            "Group MDX code blocks by the value of the specified attribute. "
            "Code blocks with the same attribute value are grouped together "
            "and executed as a single unit. "
            "For example, with `--group-mdx-by-attribute group`, code blocks "
            'with `group="example1"` are grouped together. '
            "This follows the Docusaurus convention for grouping code blocks. "
            "This option only applies to MDX files. "
            "Error messages for grouped code blocks may include lines which "
            "do not match the document, so code formatters will not work on "
            "them."
        ),
    ),
)
@cloup.option_group(
    "Temporary file options",
    cloup.option(
        "temporary_file_extension",
        "--temporary-file-extension",
        type=str,
        required=False,
        help=(
            "The file extension to give to the temporary file made from the "
            "code block. By default, the file extension is inferred from the "
            "language, or it is '.txt' if the language is not recognized."
        ),
        callback=_validate_file_extension_or_none,
    ),
    cloup.option(
        "temporary_file_name_prefix",
        "--temporary-file-name-prefix",
        type=str,
        default="doccmd",
        show_default=True,
        required=True,
        help=(
            "The prefix to give to the temporary file made from the code "
            "block. This is useful for distinguishing files created by this "
            "tool from other files, e.g. for ignoring in linter "
            "configurations."
        ),
    ),
    cloup.option(
        "temporary_file_name_template",
        "--temporary-file-name-template",
        type=str,
        default="{prefix}_{source}_l{line}__{unique}_{suffix}",
        show_default=True,
        required=True,
        callback=_validate_template,
        help=(
            "The template for the temporary file name. "
            "Available placeholders: "
            "{prefix} (from --temporary-file-name-prefix), "
            "{source} (sanitized source filename), "
            "{line} (line number), "
            "{unique} (unique identifier), "
            "{suffix} (file extension, required). "
            "Example: '{prefix}_{unique}{suffix}' produces 'doccmd_a1b2.py'."
        ),
    ),
    cloup.option(
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
    ),
    cloup.option(
        "--write-to-file/--no-write-to-file",
        "write_to_file",
        is_flag=True,
        default=True,
        show_default=True,
        help=(
            "Write any changes made by the command back to the source "
            "document. "
            "Grouped code blocks never write to files."
        ),
    ),
)
@cloup.option_group(
    "File discovery options",
    cloup.option(
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
    ),
    cloup.option(
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
    ),
    cloup.option(
        "--markdown-extension",
        "markdown_suffixes",
        type=str,
        help=(
            "Files with this extension (suffix) to treat as Markdown. "
            "Give this multiple times to look for multiple extensions. "
            "By default, `.md` is treated as MyST, not Markdown. "
            "Use `--mdx-extension` for MDX files."
        ),
        multiple=True,
        show_default=True,
        callback=_validate_file_extensions,
    ),
    cloup.option(
        "--mdx-extension",
        "mdx_suffixes",
        type=str,
        help=(
            "Treat files with this extension (suffix) as MDX. "
            "Give this multiple times to look for multiple extensions."
        ),
        multiple=True,
        default=(".mdx",),
        show_default=True,
        callback=_validate_file_extensions,
    ),
    cloup.option(
        "--djot-extension",
        "djot_suffixes",
        type=str,
        help=(
            "Treat files with this extension (suffix) as Djot. "
            "Give this multiple times to look for multiple extensions."
        ),
        multiple=True,
        default=(".djot",),
        show_default=True,
        callback=_validate_file_extensions,
    ),
    cloup.option(
        "--norg-extension",
        "norg_suffixes",
        type=str,
        help=(
            "Treat files with this extension (suffix) as Norg. "
            "Give this multiple times to look for multiple extensions."
        ),
        multiple=True,
        default=(".norg",),
        show_default=True,
        callback=_validate_file_extensions,
    ),
    cloup.option(
        "--max-depth",
        type=click.IntRange(min=1),
        default=sys.maxsize,
        show_default=False,
        help="Maximum depth to search for files in directories.",
    ),
    cloup.option(
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
    ),
    cloup.option(
        "--respect-gitignore/--no-respect-gitignore",
        "respect_gitignore",
        is_flag=True,
        default=True,
        show_default=True,
        help=(
            "Respect .gitignore files when recursively discovering files "
            "in directories. "
            "Files passed directly are not affected by this option."
        ),
    ),
)
@cloup.option_group(
    "Execution options",
    cloup.option(
        "--use-pty",
        "use_pty_option",
        type=click.Choice(choices=_UsePty, case_sensitive=False),
        default=_UsePty.DETECT,
        show_default=True,
        help=(
            "Whether to use a pseudo-terminal for running commands. "
            "Using a PTY can be useful for getting color output from "
            "commands, but can also break in some environments. "
            "\n\n"
            "'yes': Always use PTY (not supported on Windows). "
            "\n\n"
            "'no': Never use PTY - useful when doccmd detects that it is "
            "running in a TTY outside of Windows but the environment does "
            "not support PTYs. "
            "\n\n"
            "'detect': Automatically determine based on environment (default)."
        ),
    ),
    cloup.option(
        "--example-workers",
        type=click.IntRange(min=0),
        default=1,
        show_default=True,
        help=(
            "Number of code blocks to evaluate concurrently within each "
            "document when `--no-write-to-file` is set. Use 0 to auto-detect "
            "based on the number of CPUs. Values greater than 1 are rejected "
            "when writing to files, since doccmd cannot safely apply changes "
            "in parallel. Best for files with many code blocks. Can be "
            "combined with --document-workers for maximum parallelism. "
            "Output may be interleaved when using parallel execution."
        ),
    ),
    cloup.option(
        "--document-workers",
        type=click.IntRange(min=0),
        default=1,
        show_default=True,
        help=(
            "Number of documents to evaluate concurrently when "
            "`--no-write-to-file` is set. Use 0 to auto-detect based on the "
            "number of CPUs. Values greater than 1 are rejected when writing "
            "to files, since doccmd cannot safely apply changes in parallel. "
            "Best for processing many files. Can be combined with "
            "--example-workers for maximum parallelism. "
            "Output may be interleaved when using parallel execution."
        ),
    ),
)
@cloup.option_group(
    "Error handling",
    cloup.option(
        "--fail-on-parse-error/--no-fail-on-parse-error",
        "fail_on_parse_error",
        default=False,
        show_default=True,
        type=bool,
        help=(
            "Whether to fail (with exit code 1) if a given file cannot be "
            "parsed."
        ),
    ),
    cloup.option(
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
    ),
)
@cloup.option_group(
    "Output options",
    cloup.option(
        "--verbose",
        "-v",
        is_flag=True,
        default=False,
        help="Enable verbose output.",
    ),
)
@click.argument(
    "document_paths",
    type=click.Path(exists=True, path_type=Path, dir_okay=True),
    nargs=-1,
    callback=_deduplicate,
)
@click.version_option(version=__version__)
@cloup.constraint(
    constr=cloup.constraints.mutually_exclusive,
    params=["group_markers", "group_file", "group_mdx_by_attribute"],
)
@beartype
def main(
    *,
    languages: Sequence[str],
    command: str,
    document_paths: Sequence[Path],
    temporary_file_extension: str | None,
    temporary_file_name_prefix: str,
    temporary_file_name_template: str,
    pad_file: bool,
    write_to_file: bool,
    pad_groups: bool,
    verbose: bool,
    skip_markers: Iterable[str],
    group_markers: Iterable[str],
    group_file: bool,
    group_mdx_by_attribute: str | None,
    use_pty_option: _UsePty,
    rst_suffixes: Sequence[str],
    myst_suffixes: Sequence[str],
    markdown_suffixes: Sequence[str],
    mdx_suffixes: Sequence[str],
    djot_suffixes: Sequence[str],
    norg_suffixes: Sequence[str],
    max_depth: int,
    exclude_patterns: Sequence[str],
    respect_gitignore: bool,
    fail_on_parse_error: bool,
    fail_on_group_write: bool,
    sphinx_jinja2: bool,
    continue_on_error: bool,
    example_workers: int,
    document_workers: int,
) -> None:
    """Run commands against code blocks in the given documentation files.

    This works with reStructuredText, MyST, Markdown, MDX, and Djot
    files.
    """
    args = shlex.split(s=command)
    use_pty = use_pty_option.use_pty()
    example_workers = _resolve_workers(requested_workers=example_workers)
    document_workers = _resolve_workers(requested_workers=document_workers)

    suffix_groups: Mapping[MarkupLanguage, Sequence[str]] = {
        MYST: myst_suffixes,
        RESTRUCTUREDTEXT: rst_suffixes,
        MARKDOWN: markdown_suffixes,
        MDX: mdx_suffixes,
        DJOT: djot_suffixes,
        NORG: norg_suffixes,
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
        respect_gitignore=respect_gitignore,
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

    given_temporary_file_extension = temporary_file_extension

    if example_workers > 1 and write_to_file:
        message = (
            "--example-workers greater than 1 requires --no-write-to-file. "
            "doccmd cannot safely write to documents in parallel. "
            "Add --no-write-to-file to enable parallel execution."
        )
        raise click.UsageError(message=message)
    if document_workers > 1 and write_to_file:
        message = (
            "--document-workers greater than 1 requires --no-write-to-file. "
            "doccmd cannot safely write to documents in parallel. "
            "Add --no-write-to-file to enable parallel execution."
        )
        raise click.UsageError(message=message)

    collected_errors: list[_CollectedError] = []
    if document_workers == 1 or not file_paths:
        try:
            for file_path in file_paths:
                collected_errors.extend(
                    _process_file_path(
                        file_path=file_path,
                        suffix_map=suffix_map,
                        args=args,
                        languages=languages,
                        pad_file=pad_file,
                        write_to_file=write_to_file,
                        pad_groups=pad_groups,
                        temporary_file_name_prefix=temporary_file_name_prefix,
                        temporary_file_name_template=temporary_file_name_template,
                        given_temporary_file_extension=given_temporary_file_extension,
                        skip_directives=skip_directives,
                        group_markers=group_markers,
                        group_file=group_file,
                        group_mdx_by_attribute=group_mdx_by_attribute,
                        use_pty=use_pty,
                        log_command_evaluators=log_command_evaluators,
                        sphinx_jinja2=sphinx_jinja2,
                        fail_on_parse_error=fail_on_parse_error,
                        fail_on_group_write=fail_on_group_write,
                        continue_on_error=continue_on_error,
                        example_workers=example_workers,
                    )
                )
        except _FatalProcessingError as exc:
            sys.exit(exc.exit_code)
    else:
        max_workers = min(document_workers, len(file_paths))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _process_file_path,
                    file_path=file_path,
                    suffix_map=suffix_map,
                    args=args,
                    languages=languages,
                    pad_file=pad_file,
                    write_to_file=write_to_file,
                    pad_groups=pad_groups,
                    temporary_file_name_prefix=temporary_file_name_prefix,
                    temporary_file_name_template=temporary_file_name_template,
                    given_temporary_file_extension=given_temporary_file_extension,
                    skip_directives=skip_directives,
                    group_markers=group_markers,
                    group_file=group_file,
                    group_mdx_by_attribute=group_mdx_by_attribute,
                    use_pty=use_pty,
                    log_command_evaluators=log_command_evaluators,
                    sphinx_jinja2=sphinx_jinja2,
                    fail_on_parse_error=fail_on_parse_error,
                    fail_on_group_write=fail_on_group_write,
                    continue_on_error=continue_on_error,
                    example_workers=example_workers,
                ): file_path
                for file_path in file_paths
            }
            try:
                for future in as_completed(fs=futures):
                    collected_errors.extend(future.result())
            except _FatalProcessingError as exc:
                for pending_future in futures:
                    pending_future.cancel()
                sys.exit(exc.exit_code)

    if collected_errors:
        max_exit_code = max(error.exit_code for error in collected_errors)
        sys.exit(max_exit_code)
