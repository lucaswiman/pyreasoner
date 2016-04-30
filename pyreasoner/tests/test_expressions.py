from unittest import TestCase

import hypothesis

from nose.tools import assert_true

from .strategies import boolean_expressions
from ..expressions import And
from ..expressions import Eq
from ..expressions import LessThan
from ..expressions import Not
from ..expressions import Or
from ..expressions import Var
from ..expressions import convert_to_conjunctive_normal_form
from ..expressions import eval_expr
from ..expressions import get_free_variables
from ..expressions import get_truth_table
from ..expressions import is_conjunctive_normal_form
from ..expressions import is_logically_equivalent
from ..expressions import is_satisfiable
from ..expressions import reify_expr
from ..expressions import solve_SAT
from ..expressions import variables

a, b, c, d, e = variables('a b c d e')

CNF_EXPRESSIONS = (
    ~a & (b | c),
    (a | b) & (~b | c | ~d) & (d | e),
    a | b,
    a & b
)
NON_CNF_EXPRESSIONS_WITH_SOLUTIONS = (
    (~(b | c), ~b & ~c),
    ((a & b) | c, (a | c) & (b | c)),
    (a & ((b | (d & e))), a & (b | d) & (b | e)),
)


def with_examples(examples):

    def add_examples(func):
        for example in examples:
            func = hypothesis.example(example)(func)
        return func

    return add_examples


def assert_logically_equivalent(expr1, expr2):
    assert_true(
        is_logically_equivalent(expr1, expr2),
        '%r is not logically equivalent to %r' % (expr1, expr2))


class TestConstructVariables(TestCase):
    def test(self):
        self.assertEqual(variables('a b c'), variables('a, b, c'))
        self.assertEqual(variables('a b c'), [a, b, c])
        self.assertEqual(variables(['a', 'b', 'c']), [a, b, c])
        self.assertTrue(Var().name)
        with self.assertRaises(ValueError):
            Var('not$a$variable')

        with self.assertRaises(ValueError):
            Var('in')  # builtin


class TestExpressionBooleanOperations(TestCase):
    def test_operations(self):
        self.assertEqual(a & True, And(a, True))
        self.assertEqual(a | True, Or(a, True))
        self.assertEqual(Or(a, b) | Or(c, d), Or(a, b, c, d))
        self.assertEqual(And(a, b) & And(c, d), And(a, b, c, d))
        self.assertEqual(And(a, b) | And(c, d), Or(a & b, c & d))

    def test_reverse_operations(self):
        self.assertEqual(a & True, And(a, True))
        self.assertEqual(True & a, And(True, a))
        self.assertEqual(True & (a & b), And(True, a, b))
        self.assertEqual(a | True, Or(a, True))
        self.assertEqual(True | a, Or(True, a))
        self.assertEqual(True | (a | b), Or(True, a, b))

    def test_distribute_inwards(self):
        self.assertEqual(Not(False).distribute_inwards(), True)
        self.assertEqual(Not(a & b).distribute_inwards(), ~a | ~b)
        self.assertEqual(Not(a | b).distribute_inwards(), ~a & ~b)
        self.assertEqual(Not(~a).distribute_inwards(), a)

    @hypothesis.given(boolean_expressions)
    @hypothesis.settings(max_examples=1000)
    def test_distribute_inwards_preserves_logical_equivalence(self, expr):
        negated = Not(expr)
        assert_logically_equivalent(negated, negated.distribute_inwards())


class TestConjunctiveNormalForm(TestCase):
    def test_cnf_expressions(self):
        for cnf_expression in CNF_EXPRESSIONS:
            self.assertTrue(
                is_conjunctive_normal_form(cnf_expression),
                cnf_expression)
            assert_logically_equivalent(
                convert_to_conjunctive_normal_form(cnf_expression),
                cnf_expression)

    def test_non_cnf_expressions(self):
        for expr, solution in NON_CNF_EXPRESSIONS_WITH_SOLUTIONS:
            self.assertFalse(
                is_conjunctive_normal_form(expr),
                expr)
            assert_logically_equivalent(
                convert_to_conjunctive_normal_form(expr),
                solution)

    def test_is_conjunctive_normal_form(self):
        self.assertTrue(is_conjunctive_normal_form(True))
        self.assertTrue(is_conjunctive_normal_form(False))
        self.assertTrue(is_conjunctive_normal_form(a))
        self.assertTrue(is_conjunctive_normal_form(a | b))
        self.assertTrue(is_conjunctive_normal_form((a | b) & c))
        self.assertTrue(is_conjunctive_normal_form((a | b) & (c | d)))
        self.assertFalse(is_conjunctive_normal_form(a | (b & c)))
        self.assertFalse(is_conjunctive_normal_form(a | (True & c)))

    @hypothesis.given(boolean_expressions)
    @hypothesis.settings(max_examples=1000)
    @hypothesis.example(a | ~~a)
    @hypothesis.example(~~~~a | a)
    def test_conversion_is_always_cnf(self, expr):
        self.assertTrue(
            is_conjunctive_normal_form(convert_to_conjunctive_normal_form(expr)))

    def test_empty_expressions(self):
        self.assertEqual(convert_to_conjunctive_normal_form(Or()), And(Or()))
        self.assertEqual(convert_to_conjunctive_normal_form(And()), And())


class TestGetFreeVariables(TestCase):
    def test(self):
        self.assertEqual(get_free_variables(a), {a})
        self.assertEqual(get_free_variables(~a), {a})
        self.assertEqual(get_free_variables(a | a), {a})
        self.assertEqual(get_free_variables(a & a), {a})
        self.assertEqual(get_free_variables(a & b), {a, b})
        self.assertEqual(get_free_variables(~(a & b)), {a, b})
        self.assertEqual(get_free_variables(~(a | b)), {a, b})


class TestTruthTable(TestCase):
    def test_and(self):
        and_table = {
            (b1, b2): b1 and b2
            for b1, b2 in [(True, True), (True, False), (False, True), (False, False)]
        }

        self.assertEqual(get_truth_table(a & b), and_table)

    def test_or(self):
        or_table = {
            (b1, b2): b1 or b2
            for b1, b2 in [(True, True), (True, False), (False, True), (False, False)]
        }

        self.assertEqual(get_truth_table(a | b), or_table)

    def test_negation(self):
        self.assertEqual(get_truth_table(~a), {(True, ): False, (False, ): True})

    @hypothesis.given(boolean_expressions)
    @hypothesis.settings(max_examples=1000)
    def test_truth_table_invariants(self, expr):
        table = get_truth_table(expr)
        negated_table = get_truth_table(Not(expr))
        or_table = get_truth_table(expr | expr)
        and_table = get_truth_table(expr & expr)
        contradiction_table = get_truth_table(expr & Not(expr))
        tautology_table = get_truth_table(expr | Not(expr))
        self.assertEqual(table, and_table)
        self.assertEqual(table, or_table)
        self.assertEqual(
            negated_table,
            {assignment: not value for assignment, value in table.items()})
        self.assertEqual(
            contradiction_table,
            {assignment: False for assignment in table.keys()})
        self.assertEqual(
            tautology_table,
            {assignment: True for assignment in table.keys()})

    def test_no_free_variables(self):
        self.assertEqual(get_truth_table(Or(True, False)), {(): True})
        self.assertEqual(get_truth_table(And(True, False)), {(): False})
        self.assertEqual(get_truth_table(True), {(): True})

    @hypothesis.given(boolean_expressions)
    @hypothesis.settings(max_examples=1000)
    @with_examples(CNF_EXPRESSIONS)
    def test_truth_table_and_reification(self, expr):
        if isinstance(expr, bool):
            expr = Or(expr)
        table = get_truth_table(expr)
        vars = get_free_variables(expr)
        self.assertEqual(2 ** len(vars), len(table))
        for assignment, value in table.items():
            self.assertEqual(len(vars), len(assignment))
            namespace = assignment
            self.assertEqual(eval_expr(expr.reify(namespace), {}),
                             expr.eval(namespace))
            self.assertEqual(eval_expr(expr.reify(namespace), {}), value)


class TestReify(TestCase):
    def test_var(self):
        self.assertEqual(a.reify(a=6), 6)
        self.assertEqual(a.reify({a: 6}), 6)
        self.assertEqual(a.reify(b=6), a)
        self.assertEqual(a.reify(b=6), a)
        self.assertEqual(a.reify(a=b), b)
        self.assertEqual(a.reify({a: b}), b)

    def test_chained_evaluation(self):
        self.assertEqual(a.reify(a=b, b=c), b)
        self.assertEqual(a.eval(a=b, b=1), 1)
        self.assertEqual(a.reify(b=c), a)

    def test_or(self):
        self.assertEqual((a | c).reify(c=a), a | a)

    def test_reify_including_truth_literal(self):
        self.assertEqual((a | True).reify(a=False), Or(False, True))

    def test_and(self):
        self.assertEqual((a & c).reify({c: a}), a & a)

    def test_negation(self):
        self.assertEqual((~a).reify(a=False), Not(False))
        self.assertEqual((~a).reify(c=a), ~a)
        self.assertEqual((~a).eval(c=a), ~a)

    @hypothesis.given(boolean_expressions)
    @hypothesis.settings(max_examples=1000)
    @with_examples(CNF_EXPRESSIONS)
    def test_idempotency_with_empty_namespace(self, expr):
        self.assertEqual(reify_expr(expr, {}), expr)

    def assert_permutation_of_variables(self, expr):
        vars = list(get_free_variables(expr))
        hypothesis.assume(len(vars) > 1)
        perm = vars[1:] + [vars[0]]
        assignment = dict(zip(vars, perm))
        reverse_assignment = dict(zip(perm, vars))
        self.assertNotEqual(vars, perm)
        self.assertNotEqual(expr.reify(assignment), expr)
        self.assertEqual(expr.reify(assignment).reify(reverse_assignment), expr)
        self.assertEqual(expr.reify(reverse_assignment).reify(assignment), expr)

    @hypothesis.given(boolean_expressions)
    @hypothesis.settings(max_examples=1000)
    @with_examples(CNF_EXPRESSIONS)
    def test_permutation_of_variables(self, expr):
        self.assert_permutation_of_variables(expr)


def solve_SAT_truth_table(expr):
    """
    Solve SAT by building a full truth table.

    This is very inefficient for most expressions, though has the same worst
    case runtime as solve_SAT.
    """
    for assignment, value in get_truth_table(expr).items():
        if value:
            yield assignment


class TestSAT(TestCase):
    def test_pycosat_example(self):
        # Verify the example from the pycosat README works as expected:
        # The following CNF should have 9=18/2 solutions, which should include
        #  x1 = x5 = True, x2 = x3 = x4 = False
        #
        # p cnf 5 3
        # 1 -5 4 0
        # -1 5 3 4 0
        # -3 -4 0

        # Note x2 is omitted, since we don't have an API to get solution which
        # don't include free variables. And, really, it's kinda pointless to
        # make one AFAICT.
        x1, x3, x4, x5 = variables('x1 x3 x4 x5')

        expr = (
            (x1 | ~x5 | x4) &
            (~x1 | x5 | x3 | x4) &
            (~x3 | ~x4)
        )

        self.assertTrue(is_satisfiable(expr))
        expected_solution = expr.assignment_class(x1=True, x3=False, x4=False, x5=True)
        self.assertTrue(expr.eval(expected_solution))
        all_solutions = list(solve_SAT(expr))
        self.assertIn(expected_solution, all_solutions)
        self.assertEqual(len(all_solutions), 9)
        self.assertEqual(set(all_solutions), set(solve_SAT_truth_table(expr)))

    def test_expression_with_literal(self):
        self.assertTrue(is_satisfiable(True))
        self.assertEqual(list(solve_SAT(True)), [()])
        self.assertFalse(is_satisfiable(False))
        self.assertTrue(is_satisfiable(Or(True, False, a)))
        self.assertFalse(is_satisfiable(And(True, False, a)))

    @hypothesis.given(boolean_expressions)
    @hypothesis.settings(max_examples=1000, verbosity=hypothesis.Verbosity.verbose)
    def test_sat_matches_truth_table(self, expr):
        truth_table_solutions = set(solve_SAT_truth_table(expr))
        pycosat_solutions = set(solve_SAT(expr))
        self.assertEqual(truth_table_solutions, pycosat_solutions)


class TestRelationalExpressions(TestCase):
    def test_equality(self):
        self.assertFalse(Eq(5, 6).eval({}))
        self.assertEqual(Eq(a, 5).reify({'a': 5}), Eq(5, 5))
        self.assertTrue(Eq(5, 5).eval({}))

    def test_less_than(self):
        self.assertTrue(LessThan(5, 6).eval({}))
        self.assertTrue((a < 5).eval({'a': 4}))
        self.assertFalse((a < 5).eval({'a': 6}))

        self.assertTrue((4 < a).eval({'a': 5}))
