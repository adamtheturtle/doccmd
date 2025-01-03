"""
Tools for managing markup languages.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Protocol, runtime_checkable

from beartype import beartype
from sybil.parsers.myst import CodeBlockParser as MystCodeBlockParser
from sybil.parsers.rest import CodeBlockParser as RestCodeBlockParser
from sybil_extras.parsers.myst.custom_directive_skip import (
    CustomDirectiveSkipParser as MystCustomDirectiveSkipParser,
)
from sybil_extras.parsers.rest.custom_directive_skip import (
    CustomDirectiveSkipParser as RestCustomDirectiveSkipParser,
)

if TYPE_CHECKING:
    from collections.abc import MutableMapping


@beartype
class UnknownMarkupLanguageError(Exception):
    """
    Raised when the markup language is not recognized.
    """

    def __init__(self, file_path: Path) -> None:
        """
        Args:
            file_path: The file path for which the markup language is unknown.
        """
        super().__init__(f"Markup language not known for {file_path}.")


@runtime_checkable
class _MarkupLanguage(Protocol):
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


@beartype
@dataclass(frozen=True)
class _MyST:
    """
    The MyST markup language.
    """

    skip_parser_cls: ClassVar[type[MystCustomDirectiveSkipParser]] = (
        MystCustomDirectiveSkipParser
    )
    code_block_parser_cls: ClassVar[type[MystCodeBlockParser]] = (
        MystCodeBlockParser
    )


@beartype
@dataclass(frozen=True)
class _ReStructuredText:
    """
    The reStructuredText markup language.
    """

    skip_parser_cls: ClassVar[type[RestCustomDirectiveSkipParser]] = (
        RestCustomDirectiveSkipParser
    )
    code_block_parser_cls: ClassVar[type[RestCodeBlockParser]] = (
        RestCodeBlockParser
    )


@beartype
def get_markup_language(
    file_path: Path,
    myst_suffixes: Iterable[str],
    rst_suffixes: Iterable[str],
) -> _MarkupLanguage:
    """
    Determine the markup language from the file path.
    """
    suffix_map: MutableMapping[str, _MarkupLanguage] = {}

    for suffix in myst_suffixes:
        suffix_map[suffix] = _MyST
    for suffix in rst_suffixes:
        suffix_map[suffix] = _ReStructuredText

    try:
        return suffix_map[file_path.suffix]
    except KeyError as exc:
        raise UnknownMarkupLanguageError(file_path=file_path) from exc
