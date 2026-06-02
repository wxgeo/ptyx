from typing import TypedDict, TYPE_CHECKING

if TYPE_CHECKING:
    from ptyx.latex_generator import LatexGenerator


class CompilerExtension(TypedDict):
    latex_generator: type["LatexGenerator"]
    tags: dict[str, tuple[int, int, None | list[str]]]
