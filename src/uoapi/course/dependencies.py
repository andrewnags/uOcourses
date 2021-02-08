from typing import (
    Generic,
    TypeVar,
    Optional,
    List
)


T = TypeVar('T')


class DependencyNode(Generic[T]):
    kind = ''

    def __init__(
        self,
        children: Optional[List["DependencyNode[T]"]] = None
    ):
        if children is not None:
            self.children = children
        else:
            self.children = []

    def __repr__(self):
        return ''

    def __str__(self):
        return ''

    def to_dict(self):
        return {self.kind: [node.to_dict() for node in self.children]}


class OrNode(DependencyNode[T]):
    kind = 'or'

    def __repr__(self):
        return f'OrNode({self.children})'

    def __str__(self):
        return f'OrNode({self.children})'


class AndNode(DependencyNode[T]):
    kind = 'and'

    def __repr__(self):
        return f'AndNode({self.children})'

    def __str__(self):
        return f'AndNode({self.children})'


class CourseNode(DependencyNode[T]):
    kind = 'course'

    def __init__(
        self,
        v: Optional[T] = None,
        children: Optional[List["DependencyNode[T]"]] = None,
    ):
        super().__init__(children=children)
        self.val = v

    def __repr__(self):
        return f'CourseNode({self.val})'

    def to_dict(self):
        return {'course': self.val}


class RootNode(DependencyNode[T]):
    kind = 'root'

    def __repr__(self):
        return f'RootNode({self.children})'

    def __str__(self):
        return f'RootNode({self.children})'
