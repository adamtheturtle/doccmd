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
import sybil_extras.parsers.myst.custom_directive_skip
import sybil_extras.parsers.rest.custom_directive_skip
from sybil import Document, Region
from sybil.evaluators.skip import Skipper
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

    @property
    def skipper(self) -> Skipper:
        """
        The skipper used by the parser.
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


# We do not use Beartype here because it is incompatible with a Protocol which
# has a property.
@dataclass(frozen=True)
class MarkupLanguage:
    """
    A markup language.
    """

    name: str
    skip_parser_cls: type[_SkipParser]
    code_block_parser_cls: type[_CodeBlockParser]


MyST = MarkupLanguage(
    name="MyST",
    skip_parser_cls=(
        sybil_extras.parsers.myst.custom_directive_skip.CustomDirectiveSkipParser
    ),
    code_block_parser_cls=sybil.parsers.myst.CodeBlockParser,
)

ReStructuredText = MarkupLanguage(
    name="reStructuredText",
    skip_parser_cls=sybil_extras.parsers.rest.custom_directive_skip.CustomDirectiveSkipParser,
    code_block_parser_cls=sybil.parsers.rest.CodeBlockParser,
)

Markdown = MarkupLanguage(
    name="Markdown",
    skip_parser_cls=sybil_extras.parsers.markdown.custom_directive_skip.CustomDirectiveSkipParser,
    code_block_parser_cls=sybil.parsers.markdown.CodeBlockParser,
)
