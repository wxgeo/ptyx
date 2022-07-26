from typing import Union, TypeVar, Optional, List, Any, Iterable, Protocol, runtime_checkable

from ptyx.utilities import term_color

NodeChild = Union[str, "Node"]
T = TypeVar("T", bound=NodeChild)


@runtime_checkable
class Node(Protocol):
    """A node.

    `name` is either the tag name, if the node corresponds
    to a tag's content, or the argument number, if the node corresponds
    to a tag's argument."""

    def __init__(self, name: Union[str, int]):
        self.parent: Optional[Node] = None
        self.name = name
        self.options: Optional[str] = None
        self.children: List[NodeChild] = []

    def __repr__(self):
        return f"<Node {self.name} at {hex(id(self))}>"

    def add_child(self, child: T) -> Optional[T]:
        if not child:
            return None
        self.children.append(child)
        if isinstance(child, Node):
            child.parent = self
        return child

    # @property
    # def content(self):
    #   if len(self.children) != 1:
    #       raise ValueError, "Ambiguous: node has several subnodes."
    #   return self.children[0]

    def arg(self, i: int) -> Any:
        """Return argument number i content, which may be a Node, or some text (str)."""
        child = self.children[i]
        if getattr(child, "name", None) != i:
            raise ValueError(f"Incorrect argument number for node {child!r}.")
        assert isinstance(child, Node), repr(child)
        children_number = len(child.children)
        if children_number > 1:
            raise ValueError("Don't use pTyX code inside %s argument number %s." % (self.name, i + 1))
        if children_number == 0:
            if self.name == "EVAL":
                # EVAL isn't a real tag name: if a variable `#myvar` is found
                # somewhere, it is parsed as an `#EVAL` tag with `myvar` as argument.
                # So, a lonely `#` is parsed as an `#EVAL` with no argument at all.
                raise ValueError("Error! There is a lonely '#' somewhere !")
            print("Warning: %s argument number %s is empty." % (self.name, i + 1))
            return ""

        return child.children[0]

    def display(self, color=True, indent=0, raw=False) -> str:
        texts = ["%s+ Node %s" % (indent * " ", self._format(self.name, color))]
        for child in self.children:
            if isinstance(child, Node):
                texts.append(child.display(color, indent + 2, raw=raw))
            else:
                assert isinstance(child, str)
                text = repr(child)
                if not raw:
                    if len(text) > 30:
                        text = text[:25] + " [...]'"
                if color:
                    text = term_color(text, "green")
                texts.append("%s  - text: %s" % (indent * " ", text))
        return "\n".join(texts)

    def as_text(self, skipped_children: Iterable[int] = ()) -> str:
        content = []
        for i, child in enumerate(self.children):
            if i in skipped_children:
                continue
            if isinstance(child, Node):
                content.append(child.as_text())
            else:
                assert isinstance(child, str)
                content.append(child)
        return "".join(content)

    @staticmethod
    def _format(val: object, color: bool) -> str:
        if not color:
            return str(val)
        if isinstance(val, str):
            return term_color(val, "yellow")
        if isinstance(val, int):
            return term_color(str(val), "blue")
        return str(val)
