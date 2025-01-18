"""
Tools for managing markup languages.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from sybil import Document, Region
from sybil.evaluators.skip import Skipper
from sybil.parsers.myst import CodeBlockParser as MystCodeBlockParser
from sybil.parsers.rest import CodeBlockParser as RestCodeBlockParser
from sybil.typing import Evaluator
from sybil_extras.parsers.myst.custom_directive_skip import (
    CustomDirectiveSkipParser as MystCustomDirectiveSkipParser,
)
from sybil_extras.parsers.rest.custom_directive_skip import (
    CustomDirectiveSkipParser as RestCustomDirectiveSkipParser,
)


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
    skip_parser_cls=MystCustomDirectiveSkipParser,
    code_block_parser_cls=MystCodeBlockParser,
)

ReStructuredText = MarkupLanguage(
    name="reStructuredText",
    skip_parser_cls=RestCustomDirectiveSkipParser,
    code_block_parser_cls=RestCodeBlockParser,
)
