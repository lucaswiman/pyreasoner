from __future__ import absolute_import, division, unicode_literals

import abc
import operator
import re
from functools import reduce
from itertools import chain

from six import with_metaclass


class Evaluable(with_metaclass(abc.ABCMeta)):
    @abc.abstractmethod
    def eval(self, namespace):
        pass


def eval_expr(expr, namespace):
    if isinstance(expr, Evaluable):
        return expr.eval(namespace)
    else:
        return expr


def variables(names):
    if not isinstance(input, (list, tuple)):
        names = re.split(r'[, ]', names)
    return map(Var, names)


def is_boolean_atom(obj):
    return isinstance(obj, (Not, Var, bool))


def is_disjunction_of_atoms(expr):
    return is_boolean_atom(expr) or (
        isinstance(expr, Or) and
        all(is_boolean_atom(child) for child in expr.children))


def is_conjunctive_normal_form(expr):
    if is_boolean_atom(expr):
        return True
    return is_disjunction_of_atoms(expr) or (
        isinstance(expr, And) and
        all(is_disjunction_of_atoms(child) for child in expr.children)
    )


def convert_to_conjunctive_normal_form(expr):
    """
    Dumb conjunctive normal form algorithm based off this algorithm:
    https://april.eecs.umich.edu/courses/eecs492_w10/wiki/images/6/6b/CNF_conversion.pdf
    """
    if is_disjunction_of_atoms(expr):
        return expr
    elif isinstance(expr, Not):
        return convert_to_conjunctive_normal_form(expr.distribute_inwards())
    elif isinstance(expr, Or):
        return reduce(
            operator.and_
            (convert_to_conjunctive_normal_form(Not(child)) for child in expr.children))
    elif isinstance(expr, And):
        return reduce(
            operator.and_,
            (convert_to_conjunctive_normal_form(child) for child in expr.children))
    else:
        return expr


class ExpressionNode(object):
    def __or__(self, other):
        return Or(self, other)

    def __and__(self, other):
        return And(self, other)

    def __invert__(self):
        return Not(self)


class Var(ExpressionNode):
    __slots__ = ('name', )

    def __init__(self, name=None):
        if name is None:
            name = 'x_%s' % id(self)
        self.name = name

    def eval(self, namespace):
        if self in namespace:
            return namespace[self]
        elif self.name in namespace:
            return namespace[self.name]
        return self

    def __str__(self):
        return self.name

    __repr__ = __str__

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return self.name == other.name


class BooleanOperation(ExpressionNode):
    __slots__ = ('children', )

    def __init__(self, *children):
        self.children = children

    def eval(self, namespace):
        evaluated = [eval_expr(child, namespace) for child in self.children]
        if hasattr(self, 'default'):
            return reduce(self.operator, evaluated, self.default)
        return reduce(self.operator, evaluated)

    def __eq__(self, other):
        return type(self) == type(other) and self.children == other.children


class Or(BooleanOperation):
    operator = operator.or_

    def __str__(self):
        return '(%s)' % ' | '.join(str(child) for child in self.children)

    __repr__ = __str__

    def __or__(self, other):
        if isinstance(other, Or):
            return Or(*chain(self.children, other.children))
        else:
            return Or(*chain(self.children, [other]))


class And(BooleanOperation):
    operator = operator.and_

    def __str__(self):
        return '(%s)' % ' & '.join(str(child) for child in self.children)

    __repr__ = __str__

    def __and__(self, other):
        if isinstance(other, And):
            return And(*chain(self.children, other.children))
        else:
            return And(*chain(self.children, [other]))


class Not(BooleanOperation):
    def __init__(self, child):
        self.children = (child, )

    def eval(self, namespace):
        evaluated = eval_expr(self.children[0], namespace)
        if isinstance(evaluated, ExpressionNode):
            return ~evaluated
        elif isinstance(evaluated, bool):
            # Boolean
            return not evaluated
        else:
            raise TypeError(evaluated)

    def __str__(self):
        return '~%s' % self.children[0]

    __repr__ = __str__

    def distribute_inwards(self):
        child = self.children[0]
        if isinstance(child, bool):
            return not child
        elif isinstance(child, Not):
            # Simplify double negation.
            return child.children[0]
        elif isinstance(child, Or):
            # Instance of de Morgan's Law: ~(x | y) === (~x & ~y)
            return And(*(Not(descendant).distribute_inwards() for descendant in child.children))
        elif isinstance(child, And):
            # Instance of de Morgan's Law: ~(x & y) === (~x | ~y)
            return Or(*(Not(descendant).distribute_inwards() for descendant in child.children))
        else:
            return self
