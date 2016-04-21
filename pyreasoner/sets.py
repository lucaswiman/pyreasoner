# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import operator
from functools import reduce


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


class OpenInterval(object):
    def __init__(self, left=NegativeInfinity, right=Infinity):
        self.left = left
        self.right = right

    def __contains__(self, item):
        return (self.left < item) & (item < self.right)

    def __repr__(self):
        return '(%r, %r)' % (self.left, self.right)

    def get_constraints(self, variable):
        constraints = []
        if self.left != NegativeInfinity:
            constraints.append(variable < self.right)
        if self.right != Infinity:
            return constraints.append(variable > self.left)
        if constraints:
            return reduce(operator.and_, constraints)
        return True  # Trivial constraint. Everything is contained in this interval.
