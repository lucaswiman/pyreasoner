# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import abc
import operator
from functools import reduce

from six import with_metaclass  # noqa

from pyreasoner.expressions import And
from pyreasoner.expressions import Eq
from pyreasoner.expressions import Or
from pyreasoner.expressions import Var
from pyreasoner.expressions import eval_expr


class _Infinity(object):
    def __unicode__(self):  # pragma: no cover
        return '∞'

    def __repr__(self):
        return 'Infinity'

    def __lt__(self, other):
        # Infinity < other
        return False

    def __gt__(self, other):
        # other < Infinity
        return other != self

    def __eq__(self, other):
        return isinstance(other, _Infinity) or other == float('inf')

    def __neg__(self):
        return NegativeInfinity


class _NegativeInfinity(object):
    def __unicode__(self):  # pragma: no cover
        return '-∞'

    def __repr__(self):
        return 'NegativeInfinity'

    def __lt__(self, other):
        # NegativeInfinity < other
        return other != self

    def __gt__(self, other):
        # other < NegativeInfinity
        return False

    def __eq__(self, other):
        return isinstance(other, _NegativeInfinity) or other == float('-inf')

    def __neg__(self):
        return Infinity


Infinity = _Infinity()
NegativeInfinity = _NegativeInfinity()


class BaseSet(with_metaclass(abc.ABCMeta)):
    def __contains__(self, item):
        return eval_expr(self.get_constraints(Var('x')), {'x': item})

    @abc.abstractmethod
    def get_constraints(self, variable):
        raise NotImplementedError

    def __and__(self, other):
        if isinstance(other, (DiscreteSet, Intersection)):
            # These classes have more efficient means of constructing intersections.
            return other & self
        return Intersection(self, other)

    def __or__(self, other):
        return Union(self, other)


class DiscreteSet(BaseSet):
    def __init__(self, elements):
        self.elements = elements if isinstance(elements, frozenset) else frozenset(elements)

    def __eq__(self, other):
        return isinstance(other, DiscreteSet) and self.elements == other.elements

    def __repr__(self):
        return repr(self.elements)

    def __and__(self, other):
        return DiscreteSet(x for x in self.elements if x in other)

    def __or__(self, other):
        if isinstance(other, DiscreteSet):
            return DiscreteSet(self.elements | other.elements)
        intersection = self & other
        if self == intersection:
            return other
        return super(DiscreteSet, self).__or__(other)

    def __contains__(self, item):
        return item in self.elements

    def get_constraints(self, variable):
        if not self.elements:
            return False
        return reduce(
            operator.or_,
            (Eq(variable, elem) for elem in self.elements),
        )


class Union(BaseSet):
    def __init__(self, *children):
        self.children = children

    def __eq__(self, other):
        return isinstance(other, Union) and self.children == other.children

    def __or__(self, other):
        if isinstance(other, Union):
            return Union(*(self.children + other.children))
        else:
            return Union(*(self.children + (other, )))

    def __repr__(self):
        return '(%s)' % '∪'.join(map(repr, self.children))

    def __contains__(self, item):
        return any(item in child for child in self.children)

    def get_constraints(self, variable):
        return reduce(
            operator.or_,
            (child.get_constraints(variable) for child in self.children),
            Or()
        )


class Intersection(BaseSet):
    def __init__(self, *children):
        self.children = children

    def __eq__(self, other):
        return isinstance(other, Intersection) and self.children == other.children

    def __and__(self, other):
        if isinstance(other, Intersection):
            return Intersection(*(self.children + other.children))
        else:
            return Intersection(*(self.children + (other, )))

    def __repr__(self):
        return '(%s)' % '∩'.join(map(repr, self.children))

    def __contains__(self, item):
        return all(item in child for child in self.children)

    def get_constraints(self, variable):
        return reduce(
            operator.and_,
            (child.get_constraints(variable) for child in self.children),
            And()
        )


class OpenInterval(BaseSet):
    def __init__(self, left=NegativeInfinity, right=Infinity):
        self.left = left
        self.right = right

    def __eq__(self, other):
        return (
            isinstance(other, OpenInterval) and
            self.left == other.left and
            self.right == other.right)

    def __or__(self, other):
        if isinstance(other, OpenInterval):
            intersection = self & other
            if intersection == self:
                return other
            elif intersection == other:
                return self
        elif isinstance(other, DiscreteSet):
            if other & self == other:
                return self
        return super(OpenInterval, self).__or__(other)

    def __and__(self, other):
        if isinstance(other, OpenInterval):
            left = max(self.left, other.left)
            right = min(self.right, other.right)
            if left >= right:
                # In this case, the intersection is empty.
                return DiscreteSet([])
            return OpenInterval(left, right)
        return super(OpenInterval, self).__and__(other)

    def __repr__(self):
        return '(%r, %r)' % (self.left, self.right)

    def get_constraints(self, variable):
        return (variable > self.left) & (variable < self.right)
