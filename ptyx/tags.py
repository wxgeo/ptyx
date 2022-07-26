from abc import ABC, abstractmethod
from typing import Dict, Type


class Node(ABC):
    def __init__(self, children):
        self.children = children



class GenericElement(Node, ABC):
    """Base abstract class for all elements.

    Each concrete element class will correspond to a pTyX tag.
    """

    elements: Dict[str, "Type[GenericElement]"] = {}
    tag_name = NotImplemented
    unparsed_args = NotImplemented
    parsed_args = NotImplemented

    @classmethod
    def __init_subclass__(
        cls, /, *, tag_name: str = None, unparsed_args: int = 0, parsed_args: int = 0, **kwargs
    ):
        super().__init_subclass__(**kwargs)

        cls.tag_name = tag_name
        if tag_name is not None:
            elements = GenericElement.elements
            if tag_name in elements:
                raise NameError(
                    "Each element must be associated to a unique tag.\n"
                    f"Class {cls} is associated to {tag_name}, but {elements[tag_name]} already was."
                )
            elements[tag_name] = cls


    @abstractmethod
    def handle(self):
        ...


class BlockElement(GenericElement, ABC):
    closing_tags = NotImplemented
    pass


class SimpleElement(GenericElement, ABC):
    pass


class Argument(Node):
    def __init__(self, number, children):
        super().__init__(children)

