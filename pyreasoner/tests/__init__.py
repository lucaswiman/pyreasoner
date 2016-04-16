from unittest import TestCase

from ..expressions import is_conjunctive_normal_form
from ..expressions import convert_to_conjunctive_normal_form
from ..expressions import variables

a, b, c, d, e = variables('a b c d e')

cnf_expressions = (
    ~a & (b | c),
    (a | b) & (~b | c | ~d) & (d | e),
    a | b,
    a & b
)


class TestConjunctiveNormalForm(TestCase):
    def test_cnf_expressions(self):
        for cnf_expression in cnf_expressions:
            self.assertTrue(
                is_conjunctive_normal_form(cnf_expression),
                cnf_expression)
            self.assertEqual(
                convert_to_conjunctive_normal_form(cnf_expression),
                cnf_expression)
