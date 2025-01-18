"""
Tools for managing markup languages.
"""

from dataclasses import dataclass

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
@dataclass(frozen=True)
class MarkupLanguage:
    """
    A markup language.
    """

    name: str
    skip_parser_cls: type[
        MystCustomDirectiveSkipParser | RestCustomDirectiveSkipParser
    ]
    code_block_parser_cls: type[MystCodeBlockParser | RestCodeBlockParser]


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
