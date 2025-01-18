"""
Tools for managing markup languages.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Protocol, runtime_checkable

from beartype import beartype
from sybil.parsers.myst import CodeBlockParser as MystCodeBlockParser
from sybil.parsers.rest import CodeBlockParser as RestCodeBlockParser
from sybil_extras.parsers.myst.custom_directive_skip import (
    CustomDirectiveSkipParser as MystCustomDirectiveSkipParser,
)
from sybil_extras.parsers.rest.custom_directive_skip import (
    CustomDirectiveSkipParser as RestCustomDirectiveSkipParser,
)


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
def get_suffix_map(
    myst_suffixes: Iterable[str],
    rst_suffixes: Iterable[str],
) -> dict[str, MarkupLanguage]:
    """
    Get a map of suffixes to markup languages.
    """
    suffix_map: dict[str, MarkupLanguage] = {}

    for suffix in myst_suffixes:
        suffix_map[suffix] = MyST
    for suffix in rst_suffixes:
        suffix_map[suffix] = ReStructuredText

    return suffix_map


@beartype
def get_markup_language(
    file_path: Path,
    suffix_map: Mapping[str, MarkupLanguage],
) -> MarkupLanguage:
    """
    Determine the markup language from the file path.
    """
    try:
        return suffix_map[file_path.suffix]
    except KeyError as exc:
        raise UnknownMarkupLanguageError(file_path=file_path) from exc
