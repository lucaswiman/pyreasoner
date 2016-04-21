# -*- coding: utf-8 -*-
from __future__ import unicode_literals


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
