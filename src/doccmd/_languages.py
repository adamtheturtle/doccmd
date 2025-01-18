"""
Tools for managing markup languages.
"""

from dataclasses import dataclass
from typing import ClassVar, Protocol, runtime_checkable

from beartype import beartype
from sybil.parsers.markdown import CodeBlockParser as MarkdownCodeBlockParser
from sybil.parsers.myst import CodeBlockParser as MystCodeBlockParser
from sybil.parsers.rest import CodeBlockParser as RestCodeBlockParser
from sybil_extras.parsers.markdown.custom_directive_skip import (
    CustomDirectiveSkipParser as MarkdownCustomDirectiveSkipParser,
)
from sybil_extras.parsers.myst.custom_directive_skip import (
    CustomDirectiveSkipParser as MystCustomDirectiveSkipParser,
)
from sybil_extras.parsers.rest.custom_directive_skip import (
    CustomDirectiveSkipParser as RestCustomDirectiveSkipParser,
)


@runtime_checkable
class MarkupLanguage(Protocol):
    """
    A protocol for markup languages.
    """

    @property
    def skip_parser_cls(
        self,
    ) -> type[MystCustomDirectiveSkipParser | RestCustomDirectiveSkipParser]:
        """
        Skip parser class.
        """
        # We disable a pylint warning here because the ellipsis is required
        # for pyright to recognize this as a protocol.
        ...  # pylint: disable=unnecessary-ellipsis

    @property
    def code_block_parser_cls(
        self,
    ) -> type[MystCodeBlockParser | RestCodeBlockParser]:
        """
        Skip parser class.
        """
        # We disable a pylint warning here because the ellipsis is required
        # for pyright to recognize this as a protocol.
        ...  # pylint: disable=unnecessary-ellipsis

    @property
    def name(self) -> str:
        """
        The name of the markup language.
        """
        # We disable a pylint warning here because the ellipsis is required
        # for pyright to recognize this as a protocol.
        ...  # pylint: disable=unnecessary-ellipsis


@beartype
@dataclass(frozen=True)
class MyST:
    """
    The MyST markup language.
    """

    name: ClassVar[str] = "MyST"

    skip_parser_cls: ClassVar[type[MystCustomDirectiveSkipParser]] = (
        MystCustomDirectiveSkipParser
    )
    code_block_parser_cls: ClassVar[type[MystCodeBlockParser]] = (
        MystCodeBlockParser
    )


@beartype
@dataclass(frozen=True)
class ReStructuredText:
    """
    The reStructuredText markup language.
    """

    name: ClassVar[str] = "reStructuredText"

    skip_parser_cls: ClassVar[type[RestCustomDirectiveSkipParser]] = (
        RestCustomDirectiveSkipParser
    )
    code_block_parser_cls: ClassVar[type[RestCodeBlockParser]] = (
        RestCodeBlockParser
    )


@beartype
@dataclass(frozen=True)
class Markdown:
    """
    The Markdown markup language.
    """

    name: ClassVar[str] = "Markdown"

    skip_parser_cls: ClassVar[type[RestCustomDirectiveSkipParser]] = (
        MarkdownCustomDirectiveSkipParser
    )
    code_block_parser_cls: ClassVar[type[RestCodeBlockParser]] = (
        MarkdownCodeBlockParser
    )
