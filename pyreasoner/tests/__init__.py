from unittest import TestCase

from nose.tools import assert_true

from ..expressions import And
from ..expressions import Not
from ..expressions import Or
from ..expressions import convert_to_conjunctive_normal_form
from ..expressions import get_free_variables
from ..expressions import get_truth_table
from ..expressions import is_conjunctive_normal_form
from ..expressions import is_logically_equivalent
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


def assert_logically_equivalent(expr1, expr2):
    assert_true(
        is_logically_equivalent(expr1, expr2),
        '%r is not logically equivalent to %r' % (expr1, expr2))


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

    def test_no_free_variables(self):
        self.assertEqual(get_truth_table(Or(True, False)), {(): True})
        self.assertEqual(get_truth_table(And(True, False)), {(): False})


class TestReify(TestCase):
    def test_chained_evaluation(self):
        self.assertEqual(a.reify({a: b, b: c}), c)
        self.assertEqual(a.reify({b: c}), a)

    def test_or(self):
        self.assertEqual((a | c).reify({c: a}), a | a)

    def test_and(self):
        self.assertEqual((a & c).reify({c: a}), a & a)

    def test_negation(self):
        self.assertEqual((~a).reify({a: False}), Not(False))
        self.assertEqual((~a).reify({c: a}), ~a)
