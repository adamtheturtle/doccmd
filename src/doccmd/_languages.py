"""
Tools for managing markup languages.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import sybil.parsers.markdown
import sybil.parsers.myst
import sybil.parsers.rest
import sybil_extras.parsers.markdown.custom_directive_skip
import sybil_extras.parsers.markdown.grouped_source
import sybil_extras.parsers.myst.custom_directive_skip
import sybil_extras.parsers.myst.grouped_source
import sybil_extras.parsers.rest.custom_directive_skip
import sybil_extras.parsers.rest.grouped_source
from beartype import beartype
from sybil import Document, Region
from sybil.typing import Evaluator


@runtime_checkable
class _SkipParser(Protocol):
    """
    A parser for skipping custom directives.
    """

    def __init__(self, directive: str) -> None:
        """
        Construct a skip parser.
        """
        # We disable a pylint warning here because the ellipsis is required
        # for pyright to recognize this as a protocol.
        ...  # pylint: disable=unnecessary-ellipsis

    def __call__(self, document: Document) -> Iterable[Region]:
        """
        Call the skip parser.
        """
        # We disable a pylint warning here because the ellipsis is required
        # for pyright to recognize this as a protocol.
        ...  # pylint: disable=unnecessary-ellipsis


@runtime_checkable
class _GroupedSourceParser(Protocol):
    """
    A parser for grouping code blocks.
    """

    def __init__(
        self,
        *,
        directive: str,
        evaluator: Evaluator,
        pad_groups: bool,
    ) -> None:
        """
        Construct a grouped code block parser.
        """
        # We disable a pylint warning here because the ellipsis is required
        # for pyright to recognize this as a protocol.
        ...  # pylint: disable=unnecessary-ellipsis

    def __call__(self, document: Document) -> Iterable[Region]:
        """
        Call the grouped code block parser.
        """
        # We disable a pylint warning here because the ellipsis is required
        # for pyright to recognize this as a protocol.
        ...  # pylint: disable=unnecessary-ellipsis


@runtime_checkable
class _CodeBlockParser(Protocol):
    """
    A parser for code blocks.
    """

    def __init__(
        self,
        language: str | None = None,
        evaluator: Evaluator | None = None,
    ) -> None:
        """
        Construct a code block parser.
        """
        # We disable a pylint warning here because the ellipsis is required
        # for pyright to recognize this as a protocol.
        ...  # pylint: disable=unnecessary-ellipsis

    def __call__(self, document: Document) -> Iterable[Region]:
        """
        Call the code block parser.
        """
        # We disable a pylint warning here because the ellipsis is required
        # for pyright to recognize this as a protocol.
        ...  # pylint: disable=unnecessary-ellipsis


@beartype
@dataclass(frozen=True)
class MarkupLanguage:
    """
    A markup language.
    """

    name: str
    skip_parser_cls: type[_SkipParser]
    code_block_parser_cls: type[_CodeBlockParser]
    group_parser_cls: type[_GroupedSourceParser]


MyST = MarkupLanguage(
    name="MyST",
    skip_parser_cls=(
        sybil_extras.parsers.myst.custom_directive_skip.CustomDirectiveSkipParser
    ),
    code_block_parser_cls=sybil.parsers.myst.CodeBlockParser,
    group_parser_cls=sybil_extras.parsers.myst.grouped_source.GroupedSourceParser,
)

ReStructuredText = MarkupLanguage(
    name="reStructuredText",
    skip_parser_cls=sybil_extras.parsers.rest.custom_directive_skip.CustomDirectiveSkipParser,
    code_block_parser_cls=sybil.parsers.rest.CodeBlockParser,
    group_parser_cls=sybil_extras.parsers.rest.grouped_source.GroupedSourceParser,
)

Markdown = MarkupLanguage(
    name="Markdown",
    skip_parser_cls=sybil_extras.parsers.markdown.custom_directive_skip.CustomDirectiveSkipParser,
    code_block_parser_cls=sybil.parsers.markdown.CodeBlockParser,
    group_parser_cls=sybil_extras.parsers.markdown.grouped_source.GroupedSourceParser,
)
