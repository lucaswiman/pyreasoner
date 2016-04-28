# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import TestCase

from pyreasoner.expressions import Eq
from pyreasoner.expressions import variables
from pyreasoner.sets import DiscreteSet
from pyreasoner.sets import Infinity
from pyreasoner.sets import Intersection
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


class TestLogic(TestCase):
    def test_contains(self):
        self.assertIn(0, OpenInterval())
        self.assertIn('asdf', OpenInterval('a', 'b'))
        self.assertNotIn(NegativeInfinity, OpenInterval())
        self.assertNotIn(Infinity, OpenInterval())
        self.assertNotIn(0, INT_0_1)
        self.assertIn(0.5, INT_0_1)
        self.assertIn(0.5, Intersection(INT_0_1, INT_0_2))

    def test_constraints(self):
        self.assertEqual(
            OpenInterval().get_constraints(a),
            (a > NegativeInfinity) & (a < Infinity))
        self.assertEqual(
            OpenInterval('a', 'b').get_constraints(a),
            (a > 'a') & (a < 'b'))
        self.assertEqual(
            DiscreteSet(['a']).get_constraints(a),
            Eq(a, 'a'))
        self.assertEqual(
            DiscreteSet([]).get_constraints(a),
            False)
        self.assertEqual(
            (DiscreteSet([1]) | INT_3_4).get_constraints(a),
            Eq(a, 1) | ((a > 3) & (a < 4)))
        self.assertEqual(
            Intersection(DiscreteSet([1]), DiscreteSet([1, 2])).get_constraints(a),
            Eq(a, 1) & (Eq(a, 1) | Eq(a, 2)))

INT_0_2 = OpenInterval(0, 2)
INT_0_1 = OpenInterval(0, 1)
INT_2_3 = OpenInterval(2, 3)
INT_3_4 = OpenInterval(3, 4)
INT_4_5 = OpenInterval(4, 5)


class TestSetOperations(TestCase):
    def test_intersections(self):
        self.assertEqual(INT_0_2 & INT_0_2,
                         INT_0_2)
        self.assertEqual(INT_0_2 & INT_0_1,
                         INT_0_1)
        self.assertEqual(INT_0_2 & INT_2_3,
                         DiscreteSet([]))
        self.assertEqual(INT_0_2 & DiscreteSet([1]),
                         DiscreteSet([1]))
        self.assertEqual(DiscreteSet([1]) & INT_0_2,
                         DiscreteSet([1]))
        self.assertEqual(DiscreteSet([1]) & DiscreteSet([2]),
                         DiscreteSet([]))

        # TODO: Should be empty set.
        self.assertEqual(
            (INT_0_2 | DiscreteSet([2])) & (INT_3_4 | DiscreteSet([4])),
            (INT_0_2 | DiscreteSet([2])) & (INT_3_4 | DiscreteSet([4])))

        self.assertEqual(
            Intersection(INT_0_2, INT_3_4) & Intersection(INT_4_5, INT_2_3),
            Intersection(INT_0_2, INT_3_4, INT_4_5, INT_2_3))
        self.assertEqual(
            Intersection(INT_0_2, INT_3_4) & Intersection(INT_4_5, INT_2_3),
            Intersection(INT_0_2, INT_3_4, INT_4_5, INT_2_3))
        self.assertEqual(
            Intersection(INT_0_2, INT_3_4) & INT_4_5,
            Intersection(INT_0_2, INT_3_4, INT_4_5))

    def test_unions(self):
        self.assertEqual(INT_0_2 | INT_0_2,
                         INT_0_2)
        self.assertEqual(INT_0_2 | OpenInterval(0, 1),
                         INT_0_2)
        self.assertEqual(INT_0_2 | OpenInterval(0, 3),
                         OpenInterval(0, 3))
        self.assertEqual(INT_0_2 | OpenInterval(2, 3),
                         Union(INT_0_2, OpenInterval(2, 3)))
        self.assertEqual(INT_0_2 | DiscreteSet([1]),
                         INT_0_2)
        self.assertEqual(DiscreteSet([1]) | INT_0_2,
                         INT_0_2)
        self.assertEqual(DiscreteSet([1, 3]) | INT_0_2,
                         Union(DiscreteSet([1, 3]), INT_0_2))
        self.assertEqual((DiscreteSet([1, 3]) | INT_0_2) | INT_3_4,
                         Union(DiscreteSet([1, 3]), INT_0_2, INT_3_4))
        self.assertEqual(DiscreteSet([1]) | DiscreteSet([2]),
                         DiscreteSet([1, 2]))
        self.assertEqual(DiscreteSet([1]) | DiscreteSet([2]),
                         DiscreteSet([1, 2]))
        self.assertEqual((INT_0_2 | INT_2_3) | (INT_3_4 | INT_4_5),
                         Union(INT_0_2, INT_2_3, INT_3_4, INT_4_5))

    def test_containment(self):
        self.assertIn(1, INT_0_2 | INT_2_3)
        self.assertIn(2.5, INT_0_2 | INT_2_3)
        self.assertNotIn(2, INT_0_2 | INT_2_3)
