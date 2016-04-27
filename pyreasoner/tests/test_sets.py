# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import TestCase

from pyreasoner.expressions import variables
from pyreasoner.sets import DiscreteSet
from pyreasoner.sets import Infinity
from pyreasoner.sets import NegativeInfinity
from pyreasoner.sets import OpenInterval
from pyreasoner.sets import Union

a, b, c = variables('a b c')


class TestInfinity(TestCase):
    def test(self):
        self.assertLess(0, Infinity)
        self.assertGreater(Infinity, 0)
        self.assertGreater(0, NegativeInfinity)
        self.assertLess(NegativeInfinity, 0)

        self.assertFalse(Infinity > Infinity)
        self.assertFalse(Infinity < Infinity)
        self.assertFalse(NegativeInfinity > NegativeInfinity)
        self.assertFalse(NegativeInfinity < NegativeInfinity)

        self.assertEqual(Infinity, Infinity)
        self.assertEqual(NegativeInfinity, NegativeInfinity)
        self.assertEqual(float('inf'), Infinity)
        self.assertEqual(Infinity, float('inf'))
        self.assertEqual(float('-inf'), NegativeInfinity)
        self.assertEqual(NegativeInfinity, float('-inf'))

        self.assertLess(NegativeInfinity, Infinity)
        self.assertGreater(Infinity, NegativeInfinity)
        self.assertEqual(-Infinity, NegativeInfinity)
        self.assertEqual(-NegativeInfinity, Infinity)


class TestRanges(TestCase):
    def test_contains(self):
        self.assertIn(0, OpenInterval())
        self.assertIn('asdf', OpenInterval('a', 'b'))
        self.assertNotIn(NegativeInfinity, OpenInterval())
        self.assertNotIn(Infinity, OpenInterval())
        self.assertNotIn(0, OpenInterval(0, 1))
        self.assertIn(0.5, OpenInterval(0, 1))

    def test_constraints(self):
        self.assertEqual(
            OpenInterval().get_constraints(a),
            (a > NegativeInfinity) & (a < Infinity)
        )
        self.assertEqual(
            OpenInterval('a', 'b').get_constraints(a),
            (a > 'a') & (a < 'b')
        )


class TestSetOperations(TestCase):
    def test_intersections(self):
        self.assertEqual(OpenInterval(0, 2) & OpenInterval(0, 2),
                         OpenInterval(0, 2))
        self.assertEqual(OpenInterval(0, 2) & OpenInterval(0, 1),
                         OpenInterval(0, 1))
        self.assertEqual(OpenInterval(0, 2) & OpenInterval(2, 3),
                         DiscreteSet([]))
        self.assertEqual(OpenInterval(0, 2) & DiscreteSet([1]),
                         DiscreteSet([1]))
        self.assertEqual(DiscreteSet([1]) & OpenInterval(0, 2),
                         DiscreteSet([1]))
        self.assertEqual(DiscreteSet([1]) & DiscreteSet([2]),
                         DiscreteSet([]))

        # TODO: Should be empty set.
        self.assertEqual(
            (OpenInterval(0, 2) | DiscreteSet([2])) & (OpenInterval(3, 4) | DiscreteSet([4])),
            (OpenInterval(0, 2) | DiscreteSet([2])) & (OpenInterval(3, 4) | DiscreteSet([4])))

    def test_unions(self):
        self.assertEqual(OpenInterval(0, 2) | OpenInterval(0, 2),
                         OpenInterval(0, 2))
        self.assertEqual(OpenInterval(0, 2) | OpenInterval(0, 1),
                         OpenInterval(0, 2))
        self.assertEqual(OpenInterval(0, 2) | OpenInterval(0, 3),
                         OpenInterval(0, 3))
        self.assertEqual(OpenInterval(0, 2) | OpenInterval(2, 3),
                         Union(OpenInterval(0, 2), OpenInterval(2, 3)))
        self.assertEqual(OpenInterval(0, 2) | DiscreteSet([1]),
                         OpenInterval(0, 2))
        self.assertEqual(DiscreteSet([1]) | OpenInterval(0, 2),
                         OpenInterval(0, 2))
        self.assertEqual(DiscreteSet([1]) | DiscreteSet([2]),
                         DiscreteSet([1, 2]))
