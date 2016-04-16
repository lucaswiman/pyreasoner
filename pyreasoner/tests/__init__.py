from unittest import TestCase

from ..expressions import convert_to_conjunctive_normal_form
from ..expressions import is_conjunctive_normal_form
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


class TestConjunctiveNormalForm(TestCase):
    def test_cnf_expressions(self):
        for cnf_expression in CNF_EXPRESSIONS:
            self.assertTrue(
                is_conjunctive_normal_form(cnf_expression),
                cnf_expression)
            self.assertEqual(
                convert_to_conjunctive_normal_form(cnf_expression),
                cnf_expression)

    def test_non_cnf_expressions(self):
        for expr, solution in NON_CNF_EXPRESSIONS_WITH_SOLUTIONS:
            self.assertFalse(
                is_conjunctive_normal_form(expr),
                expr)
            self.assertEqual(
                convert_to_conjunctive_normal_form(expr),
                solution)
