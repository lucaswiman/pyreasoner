from __future__ import absolute_import, division, unicode_literals

import abc
import itertools
import operator
import re
from functools import reduce
from itertools import chain

import pycosat

from six import with_metaclass


def eval_expr(expr, namespace):
    if isinstance(expr, ExpressionNode):
        return expr.eval(namespace)
    else:
        return expr


def reify_expr(expr, namespace):
    if isinstance(expr, ExpressionNode):
        return expr.reify(namespace)
    else:
        return expr


def variables(names):
    if not isinstance(names, (list, tuple)):
        names = re.split(r'[, ]+', names)
    return [Var(name) for name in names]


def is_boolean_atom(obj):
    return isinstance(obj, (Var, bool)) or (
        isinstance(obj, Not) and isinstance(obj.children[0], (Var, bool)))


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


def _convert_to_conjunctive_normal_form(expr):
    """
    Dumb conjunctive normal form algorithm based off this algorithm:
    https://april.eecs.umich.edu/courses/eecs492_w10/wiki/images/6/6b/CNF_conversion.pdf
    """
    if is_disjunction_of_atoms(expr):
        return expr
    elif isinstance(expr, Not):
        return _convert_to_conjunctive_normal_form(expr.distribute_inwards())
    elif isinstance(expr, Or):
        collapsed = expr.recursive_collapse()
        if is_disjunction_of_atoms(collapsed):
            return collapsed
        for i, child in enumerate(collapsed.children):
            if isinstance(child, And):
                other_disjuncts = Or(*chain(collapsed.children[:i], collapsed.children[i + 1:]))
                result = _convert_to_conjunctive_normal_form(
                    And(*(descendant | other_disjuncts for descendant in child.children)))
                return result
        else:  # pragma: no cover
            # This branch would indicate a bug in recursive_collapse or
            # is_disjunction_of_atoms.
            assert False, 'Bug: Should be unreachable: %r' % expr
    elif isinstance(expr, And):
        return reduce(
            operator.and_,
            (_convert_to_conjunctive_normal_form(child) for child in expr.children),
            And())
    else:  # pragma: no cover
        assert False, 'Unhandled: %r' % expr


def convert_to_conjunctive_normal_form(expr):
    # Hack handle the boolean literal case so the return value is always an And node.
    return And() & _convert_to_conjunctive_normal_form(expr)


class ExpressionNode(with_metaclass(abc.ABCMeta)):

    @abc.abstractmethod
    def eval(self, namespace):  # pragma: no cover
        raise NotImplementedError

    @abc.abstractmethod
    def reify(self, namespace):  # pragma: no cover
        raise NotImplementedError

    @abc.abstractmethod
    def get_free_variables(self):  # pragma: no cover
        raise NotImplementedError

    def __or__(self, other):
        return Or(self, other)

    def __ror__(self, other):
        return Or(other, self)

    def __and__(self, other):
        return And(self, other)

    def __rand__(self, other):
        return And(other, self)

    def __invert__(self):
        return Not(self)


class Var(ExpressionNode):
    __slots__ = ('name', )

    def __init__(self, name=None):
        if name is None:
            name = 'x_%s' % id(self)
        self.name = name

    def reify(self, namespace):
        """
        Replace with the assignment in ``namespace``.

        Note that this does not follow chained a->b->c namespace substitutions
        as ``eval`` does.
        """
        if self in namespace:
            ret = namespace[self]
        elif self.name in namespace:
            ret = namespace[self.name]
        else:
            ret = self
        return ret

    def eval(self, namespace):
        reified = self.reify(namespace)
        if reified != self and hasattr(reified, 'eval'):
            # Handle the Var('x').eval({'x': Var('y'), 'y': 10}) case.
            return reified.eval(namespace)
        return reified

    def get_free_variables(self):
        return {self}

    def __str__(self):
        return self.name

    __repr__ = __str__

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return isinstance(other, Var) and self.name == other.name


class BooleanOperation(ExpressionNode):
    __slots__ = ('children', )

    def __init__(self, *children):
        self.children = children

    def get_free_variables(self):
        # operator.or_ is the set union operation.
        return reduce(operator.or_, (get_free_variables(child) for child in self.children))

    def reify(self, namespace):
        reified = [reify_expr(child, namespace) for child in self.children]
        return type(self)(*reified)

    def eval(self, namespace):
        evaluated = [eval_expr(child, namespace) for child in self.children]
        return reduce(self.operator, evaluated, self.default_reduce_value)

    def __eq__(self, other):
        return type(self) == type(other) and self.children == other.children


class Or(BooleanOperation):
    operator = operator.or_
    default_reduce_value = False  # An empty disjunction is defined to be True.

    def __str__(self):
        return '(%s)' % ' | '.join(str(child) for child in self.children)

    __repr__ = __str__

    def __or__(self, other):
        if isinstance(other, Or):
            return Or(*chain(self.children, other.children))
        else:
            return Or(*chain(self.children, [other]))

    def __ror__(self, other):
        return Or(other, *self.children)

    def recursive_collapse(self):
        """
        Returns an Or node whose Or children have been promoted to the top level
        """
        children = []
        for child in self.children:
            if isinstance(child, Or):
                children.extend(child.recursive_collapse().children)
            else:
                children.append(child)
        return Or(*children)


class And(BooleanOperation):
    operator = operator.and_
    default_reduce_value = True  # An empty conjunction is defined to be False.

    def __str__(self):
        return '(%s)' % ' & '.join(str(child) for child in self.children)

    __repr__ = __str__

    def __and__(self, other):
        if isinstance(other, And):
            return And(*chain(self.children, other.children))
        else:
            return And(*chain(self.children, [other]))

    def __rand__(self, other):
        return And(other, *self.children)


class Not(BooleanOperation):
    def __init__(self, child):
        self.children = (child, )

    def eval(self, namespace):
        evaluated = eval_expr(self.children[0], namespace)
        if isinstance(evaluated, ExpressionNode):
            return ~evaluated
        elif isinstance(evaluated, bool):
            return not evaluated
        else:  # pragma: no cover
            raise TypeError(evaluated)

    def get_free_variables(self):
        return get_free_variables(self.children[0])

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


def get_free_variables(expr):
    if hasattr(expr, 'get_free_variables'):
        return expr.get_free_variables()
    else:
        return set()


def get_truth_table(expr):
    """
    Returns a ``{var_assignment: truth_value}`` dict representing the truth_table for the
    given expression.

    ``var_assignment`` is a tuple, whose attributes are alphabetically ordered variables
    of all the free variables in ``expr``.
    """
    variables = sorted(get_free_variables(expr), key=operator.attrgetter('name'))
    bools = [True, False]
    return {
        assignment: expr.eval({var: value for var, value in zip(variables, assignment)})
        for assignment in itertools.product(*([bools] * len(variables)))
    }


def is_logically_equivalent(expr1, expr2):
    return get_free_variables(expr1) == get_free_variables(expr2)


def solve_SAT(expr, num_solutions=None):
    """
    Returns a iterator of {var: truth value} assignments which satisfy the given
    expression.

    Expressions should not include a variable named ``__TRUE__`` or ``__FALSE__``,
    since those are used in the internals of this function as stand-ins for
    truth literals.
    """
    expr = convert_to_conjunctive_normal_form(expr)

    # Hack to include truth literals (not supported by pycosat API.
    # Trivial constraints are added to the list of constraints forcing these variables
    # to be True/False in any solutions.
    T = Var('__TRUE__')
    F = Var('__FALSE__')

    # This forces the variable T to be True, and F to be False. Note that this is still
    # conjunctive normal form, since T and F are literals.
    expr = expr & T & ~F

    vars = list(get_free_variables(expr))

    # 1-index, since pycosat expects nonzero integers.
    var2pycosat_index = {v: i + 1 for i, v in enumerate(vars)}

    def get_pycosat_index(literal):
        # pycosat accepts input as a list of CNF subclauses (disjunctions of variables
        # or negated variables).
        if isinstance(literal, Not):
            return -var2pycosat_index[literal.children[0]]
        elif isinstance(literal, Var):
            return var2pycosat_index[literal]
        elif isinstance(literal, ExpressionNode):  # pragma: no cover
            raise TypeError('Unhandled literal type %r' % literal)
        else:
            # Here we assume this is some other python object, so we consider it
            # a boolean.
            return var2pycosat_index[T] if literal else -var2pycosat_index[T]

    constraints = [
        map(get_pycosat_index,
            # Child is one of a literal or a disjunction of literals.
            (child.children if isinstance(child, Or) else [child]))
        for child in expr.children
    ]

    solutions = (
        pycosat.itersolve(constraints)
        if num_solutions is None else pycosat.itersolve(constraints, num_solutions))
    for solution in solutions:
        namespace = {}
        for i, var_assignment in enumerate(solution):
            # pycosat returns the solution as a list of positive or negative
            # 1-indexed variable numbers. Positive indices correspond to assignments
            # to True, and negative corresponds to False.
            as_bool = var_assignment > 0
            var = vars[i]
            if var in (T, F):
                assert as_bool == (var == T), \
                    'Bug: Solution has an invalid solution to the T/F literals.'
            else:
                namespace[var] = as_bool
        yield namespace


def is_satisfiable(expr):
    """
    Returns True if expr is satisfiable.
    """
    return next(solve_SAT(expr, 1), None) is not None
