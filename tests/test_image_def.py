from unittest import TestCase

from nicett6.image_def import ImageDef


class TestImageDef(TestCase):
    def setUp(self):
        self.image_def = ImageDef(0.05, 1.8, 16 / 9)

    def test1(self):
        """Test width"""
        self.assertAlmostEqual(self.image_def.width, 3.2)

    def test2(self):
        """Test 2.35"""
        self.assertAlmostEqual(self.image_def.implied_image_height(2.35), 1.361702128)

    def test3(self):
        """Test 16 / 9"""
        self.assertAlmostEqual(self.image_def.implied_image_height(16 / 9), 1.8)

    def test4(self):
        """Test capping of implied image height"""
        self.assertAlmostEqual(self.image_def.implied_image_height(4 / 3), 1.8)

    def test5(self):
        """Test 16 / 9 ish capped"""
        self.assertAlmostEqual(self.image_def.implied_image_height(1.77), 1.8)

    def test6(self):
        """Test 16 / 9 ish not capped"""
        self.assertAlmostEqual(self.image_def.implied_image_height(1.78), 1.7977528)

    def test7(self):
        """Test invalid target aspect ratio low"""
        with self.assertRaises(ValueError):
            self.image_def.implied_image_height(0.2)

    def test8(self):
        """Test invalid target aspect ratio high"""
        with self.assertRaises(ValueError):
            self.image_def.implied_image_height(4)
