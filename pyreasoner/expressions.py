from __future__ import absolute_import, division, unicode_literals

import abc
import itertools
import operator
import re
import typing  # noqa
from functools import reduce
from itertools import chain

import pycosat

from six import with_metaclass

from .utils import is_valid_identifier_for_namedtuple


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

    TODO: Include some of the optimizations in http://cs.jhu.edu/~jason/tutorials/convert-to-CNF
    (at least for SAT solving).
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

        # This would indicate a bug in recursive_collapse or is_disjunction_of_atoms.
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
    def eval(self, namespace=None, **kwargs):  # pragma: no cover
        raise NotImplementedError

    @abc.abstractmethod
    def reify(self, namespace=None, **kwargs):  # pragma: no cover
        raise NotImplementedError

    @abc.abstractproperty
    def free_variables(self):  # pragma: no cover
        raise NotImplementedError

    @property
    def assignment_class(self):
        if not hasattr(self, '_assignment_class'):
            self._assignment_class = typing.NamedTuple(
                'Assignment', sorted((var.name, bool) for var in self.free_variables))

        return self._assignment_class

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

    def __init__(self, name=None):
        if name is None:
            name = 'x_%s' % id(self)
        if not is_valid_identifier_for_namedtuple(name):
            raise ValueError('%r is an invalid identifier' % name)
        self.name = name

    def reify(self, namespace=None, **kwargs):
        """
        Replace with the assignment in ``namespace``.

        Note that this does not follow chained a->b->c namespace substitutions
        as ``eval`` does.
        """
        ret = self
        if namespace is not None and kwargs:
            raise ValueError('Cannot specify both namespace and kwargs')
        namespace = namespace or kwargs
        if isinstance(namespace, dict):
            if self in namespace:
                ret = namespace[self]
            elif self.name in namespace:
                ret = namespace[self.name]
        else:  # an Assignment namedtuple.
            ret = getattr(namespace, self.name, self)
        return ret

    def eval(self, namespace=None, **kwargs):
        if namespace is not None and kwargs:
            raise ValueError('Cannot specify both namespace and kwargs')
        namespace = namespace or kwargs
        reified = self.reify(namespace)
        if reified != self and hasattr(reified, 'eval'):
            # Handle the Var('x').eval({'x': Var('y'), 'y': 10}) case.
            return reified.eval(namespace)
        return reified

    @property
    def free_variables(self):
        return {self}

    def __str__(self):
        return self.name

    __repr__ = __str__

    def __hash__(self):
        return hash(self.name)

    def __lt__(self, other):
        return LessThan(self, other)

    def __gt__(self, other):
        return LessThan(other, self)

    def __eq__(self, other):
        return isinstance(other, Var) and self.name == other.name


class Operation(ExpressionNode):
    def __init__(self, *children):
        self.children = children

    @property
    def free_variables(self):
        # operator.or_ is the set union operation.
        return reduce(operator.or_, (get_free_variables(child) for child in self.children))

    def reify(self, namespace=None, **kwargs):
        if namespace is not None and kwargs:
            raise ValueError('Cannot specify both namespace and kwargs')
        namespace = namespace or kwargs
        reified = [reify_expr(child, namespace) for child in self.children]
        return type(self)(*reified)

    def eval(self, namespace=None, **kwargs):
        if namespace is not None and kwargs:
            raise ValueError('Cannot specify both namespace and kwargs')
        namespace = namespace or kwargs
        evaluated = [eval_expr(child, namespace) for child in self.children]
        if hasattr(self, 'default_reduce_value'):
            return reduce(self.operator, evaluated, self.default_reduce_value)
        else:
            return reduce(self.operator, evaluated)

    def __eq__(self, other):
        return type(self) == type(other) and self.children == other.children


class Or(Operation):
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
            if isinstance(child, Not):
                child = child.distribute_inwards()
            if isinstance(child, Or):
                children.extend(child.recursive_collapse().children)
            else:
                children.append(child)
        return Or(*children)


class And(Operation):
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


class Not(Operation):
    def __init__(self, child):
        self.children = (child, )

    def eval(self, namespace=None, **kwargs):
        if namespace is not None and kwargs:
            raise ValueError('Cannot specify both namespace and kwargs')
        namespace = namespace or kwargs
        evaluated = eval_expr(self.children[0], namespace)
        if isinstance(evaluated, ExpressionNode):
            return ~evaluated
        elif isinstance(evaluated, bool):
            return not evaluated
        else:  # pragma: no cover
            raise TypeError(evaluated)

    def __str__(self):
        if isinstance(self.children[0], bool):
            return 'Not(%s)' % self.children[0]
        return '~%s' % self.children[0]

    __repr__ = __str__

    def distribute_inwards(self):
        child = self.children[0]
        if isinstance(child, bool):
            return not child
        elif isinstance(child, Not):
            # Recursively simplify double negation.
            ret = child.children[0]
            if isinstance(ret, Not):
                ret = ret.distribute_inwards()
            return ret
        elif isinstance(child, Or):
            # Instance of de Morgan's Law: ~(x | y) === (~x & ~y)
            return And(*(Not(descendant).distribute_inwards() for descendant in child.children))
        elif isinstance(child, And):
            # Instance of de Morgan's Law: ~(x & y) === (~x | ~y)
            return Or(*(Not(descendant).distribute_inwards() for descendant in child.children))
        else:
            return self


class BinaryExpression(Operation):
    operation_name = None

    def __init__(self, lhs, rhs):
        self.children = self.lhs, self.rhs = [lhs, rhs]

    def __repr__(self):
        return '(%s %s %s)' % (self.lhs, self.operation_name, self.rhs)


class LessThan(BinaryExpression):
    operation_name = '<'
    operator = operator.lt


class GreaterThan(BinaryExpression):
    operation_name = '>'
    operator = operator.gt


class Eq(BinaryExpression):
    operation_name = '=='
    operator = operator.eq


def get_free_variables(expr):
    if hasattr(expr, 'free_variables'):
        return expr.free_variables
    else:
        return set()


EmptyAssignment = typing.NamedTuple('EmptyAssignment', [])


def get_assignment_class(expr):
    if isinstance(expr, ExpressionNode):
        return expr.assignment_class
    else:
        return EmptyAssignment


def get_truth_table(expr):
    """
    Returns a ``{var_assignment: truth_value}`` dict representing the truth_table for the
    given expression.

    ``var_assignment`` is a namedtuple, whose attributes are alphabetically ordered variables
    of all the free variables in ``expr``.
    """
    AssignmentClass = get_assignment_class(expr)
    bools = [True, False]
    assignments = itertools.starmap(
        AssignmentClass, itertools.product(*([bools] * len(AssignmentClass._fields))))
    return {
        assignment: eval_expr(expr, assignment._asdict()) for assignment in assignments
    }


def is_logically_equivalent(expr1, expr2):
    return get_truth_table(expr1) == get_truth_table(expr2)


def solve_SAT(expr, num_solutions=None):
    """
    Returns a iterator of {var: truth value} assignments which satisfy the given
    expression.

    Expressions should not include a variable named ``TRUE_``, since those
    are used in the internals of this function as stand-ins for truth literals.
    """
    expr = convert_to_conjunctive_normal_form(expr)
    Assignment = get_assignment_class(expr)

    # Hack to include a True literal (not directly supported by pycosat API).
    # We add a trivial constraint to the list of constraints, forcing this
    # variables to be True in any solutions. Note that this is still conjunctive
    # normal form, since T and F are literals.
    T = Var('TRUE_')
    expr = expr & T

    vars = list(get_free_variables(expr))

    # 1-index, since pycosat expects nonzero integers.
    var2pycosat_index = {v: i + 1 for i, v in enumerate(vars)}

    def get_pycosat_index(literal):
        # pycosat accepts input as a list of CNF subclauses (disjunctions of variables
        # or negated variables).
        if isinstance(literal, Not):
            return -get_pycosat_index(literal.children[0])
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
            if var == T:
                assert as_bool, 'Bug: Solution has an invalid solution to the T literal.'
            else:
                namespace[var.name] = as_bool
        yield Assignment(**namespace)


def is_satisfiable(expr):
    """
    Returns True if expr is satisfiable.
    """
    return next(solve_SAT(expr, 1), None) is not None
