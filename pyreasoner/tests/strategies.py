import operator

from hypothesis import strategies as st

from pyreasoner.expressions import And
from pyreasoner.expressions import Not
from pyreasoner.expressions import Or
from pyreasoner.expressions import variables

EXAMPLE_VARIABLES = variables('a b c d e f')
NEGATED_VARIABLES = list(map(operator.invert, EXAMPLE_VARIABLES))


boolean_atoms = st.sampled_from(
    EXAMPLE_VARIABLES + NEGATED_VARIABLES + [True, False])


def expressions_or(args):
    return Or(*args)

def expressions_and(args):
    return And(*args)


def combine_expressions(children):
    return (
        st.lists(children, min_size=2).map(expressions_or) |
        st.lists(children, min_size=2).map(expressions_and) |
        children.map(Not))


boolean_expressions = st.recursive(
    boolean_atoms,
    combine_expressions,
    max_leaves=100)
