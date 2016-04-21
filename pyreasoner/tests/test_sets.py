# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import TestCase

from pyreasoner.sets import Infinity
from pyreasoner.sets import NegativeInfinity


class TestInfinity(TestCase):
    def test(self):
        self.assertLess(5, Infinity)
        self.assertGreater(Infinity, 5)
        self.assertGreater(5, NegativeInfinity)
        self.assertLess(NegativeInfinity, 5)

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
