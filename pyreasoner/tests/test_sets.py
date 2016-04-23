# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import TestCase

from pyreasoner.expressions import variables
from pyreasoner.sets import Infinity
from pyreasoner.sets import NegativeInfinity
from pyreasoner.sets import OpenInterval

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
        assert False

    def test_unions(self):
        assert False
