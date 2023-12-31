from unittest import IsolatedAsyncioTestCase, TestCase

from nicett6.ciw_helper import CIWHelper
from nicett6.cover import Cover
from nicett6.image_def import ImageDef


class TestCIWHelper(IsolatedAsyncioTestCase):
    def setUp(self):
        image_def = ImageDef(0.05, 1.8, 16 / 9)
        self.helper = CIWHelper(Cover("Screen", 2.0), Cover("Mask", 0.8), image_def)

    async def test1(self):
        """Screen fully up, mask fully up"""
        self.assertAlmostEqual(self.helper.screen.max_drop, 2.0)
        self.assertAlmostEqual(self.helper.image_width, 3.2)
        self.assertAlmostEqual(self.helper.screen.drop_pct, 1.0)
        self.assertAlmostEqual(self.helper.screen.drop, 0.0)
        self.assertAlmostEqual(self.helper.mask.drop_pct, 1.0)
        self.assertAlmostEqual(self.helper.mask.drop, 0.0)
        self.assertEqual(self.helper.image_is_visible, False)
        self.assertIsNone(self.helper.image_height)
        self.assertIsNone(self.helper.aspect_ratio)
        self.assertIsNone(self.helper.image_diagonal)
        self.assertIsNone(self.helper.image_area)

    async def test2(self):
        """Screen fully down, mask fully up"""
        await self.helper.screen.set_drop_pct(0.0)
        self.assertAlmostEqual(self.helper.screen.max_drop, 2.0)
        self.assertAlmostEqual(self.helper.image_width, 3.2)
        self.assertAlmostEqual(self.helper.screen.drop_pct, 0.0)
        self.assertAlmostEqual(self.helper.screen.drop, 2.0)
        self.assertAlmostEqual(self.helper.mask.drop_pct, 1.0)
        self.assertAlmostEqual(self.helper.mask.drop, 0.0)
        self.assertEqual(self.helper.image_is_visible, True)
        self.assertIsNotNone(self.helper.image_height)
        self.assertIsNotNone(self.helper.aspect_ratio)
        self.assertIsNotNone(self.helper.image_diagonal)
        self.assertIsNotNone(self.helper.image_area)
        if self.helper.image_height is not None:
            self.assertAlmostEqual(self.helper.image_height, 1.8)
        if self.helper.aspect_ratio is not None:
            self.assertAlmostEqual(self.helper.aspect_ratio, 16.0 / 9.0)
        if self.helper.image_diagonal is not None:
            self.assertAlmostEqual(self.helper.image_diagonal, 3.67151195)
        if self.helper.image_area is not None:
            self.assertAlmostEqual(self.helper.image_area, 5.76)

    async def test3(self):
        """Screen fully up, mask fully down"""
        await self.helper.mask.set_drop_pct(0.0)
        self.assertAlmostEqual(self.helper.screen.max_drop, 2.0)
        self.assertAlmostEqual(self.helper.image_width, 3.2)
        self.assertAlmostEqual(self.helper.screen.drop_pct, 1.0)
        self.assertAlmostEqual(self.helper.screen.drop, 0.0)
        self.assertAlmostEqual(self.helper.mask.drop_pct, 0.0)
        self.assertAlmostEqual(self.helper.mask.drop, 0.8)
        self.assertEqual(self.helper.image_is_visible, False)
        self.assertIsNone(self.helper.image_height)
        self.assertIsNone(self.helper.aspect_ratio)
        self.assertIsNone(self.helper.image_diagonal)
        self.assertIsNone(self.helper.image_area)

    async def test4(self):
        """Screen hiding top border, mask fully up"""
        await self.helper.screen.set_drop_pct(0.15 / 2.0)
        self.assertAlmostEqual(self.helper.screen.max_drop, 2.0)
        self.assertAlmostEqual(self.helper.image_width, 3.2)
        self.assertAlmostEqual(self.helper.screen.drop_pct, 0.15 / 2.0)
        self.assertAlmostEqual(self.helper.screen.drop, 1.85)
        self.assertAlmostEqual(self.helper.mask.drop_pct, 1.0)
        self.assertAlmostEqual(self.helper.mask.drop, 0.0)
        self.assertEqual(self.helper.image_is_visible, True)
        self.assertIsNotNone(self.helper.image_height)
        self.assertIsNotNone(self.helper.aspect_ratio)
        self.assertIsNotNone(self.helper.image_diagonal)
        self.assertIsNotNone(self.helper.image_area)
        if self.helper.image_height is not None:
            self.assertAlmostEqual(self.helper.image_height, 1.8)
        if self.helper.aspect_ratio is not None:
            self.assertAlmostEqual(self.helper.aspect_ratio, 16.0 / 9.0)
        if self.helper.image_diagonal is not None:
            self.assertAlmostEqual(self.helper.image_diagonal, 3.67151195)
        if self.helper.image_area is not None:
            self.assertAlmostEqual(self.helper.image_area, 5.76)

    async def test5(self):
        """Screen fully down, mask set for 2.35 absolute"""
        await self.helper.screen.set_drop_pct(0.0)
        await self.helper.mask.set_drop_pct(0.26462766)
        self.assertAlmostEqual(self.helper.screen.max_drop, 2.0)
        self.assertAlmostEqual(self.helper.image_width, 3.2)
        self.assertAlmostEqual(self.helper.screen.drop_pct, 0.0)
        self.assertAlmostEqual(self.helper.screen.drop, 2.0)
        self.assertAlmostEqual(self.helper.mask.drop_pct, 0.26462766)
        self.assertAlmostEqual(self.helper.mask.drop, 0.588297872)
        self.assertEqual(self.helper.image_is_visible, True)
        self.assertIsNotNone(self.helper.image_height)
        self.assertIsNotNone(self.helper.aspect_ratio)
        self.assertIsNotNone(self.helper.image_diagonal)
        self.assertIsNotNone(self.helper.image_area)
        if self.helper.image_height is not None:
            self.assertAlmostEqual(self.helper.image_height, 1.361702128)
        if self.helper.aspect_ratio is not None:
            self.assertAlmostEqual(self.helper.aspect_ratio, 2.35)
        if self.helper.image_diagonal is not None:
            self.assertAlmostEqual(self.helper.image_diagonal, 3.477676334)
        if self.helper.image_area is not None:
            self.assertAlmostEqual(self.helper.image_area, 4.35744681)
