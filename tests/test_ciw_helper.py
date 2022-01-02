from nicett6.ciw_helper import CIWHelper, ImageDef
from nicett6.cover import Cover
from unittest import IsolatedAsyncioTestCase, TestCase


class TestImageDef(TestCase):
    def setUp(self):
        self.image_def = ImageDef(0.05, 1.8, 16 / 9)

    def tearDown(self) -> None:
        self.image_def = None

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


class TestCIWHelper(IsolatedAsyncioTestCase):
    def setUp(self):
        image_def = ImageDef(0.05, 1.8, 16 / 9)
        self.helper = CIWHelper(Cover("Screen", 2.0), Cover("Mask", 0.8), image_def)

    def tearDown(self) -> None:
        self.helper = None

    async def test1(self):
        """Screen fully up, mask fully up"""
        self.assertAlmostEqual(self.helper.screen.max_drop, 2.0)
        self.assertAlmostEqual(self.helper.image_width, 3.2)
        self.assertAlmostEqual(self.helper.screen.drop_pct, 1.0)
        self.assertAlmostEqual(self.helper.screen.drop, 0.0)
        self.assertAlmostEqual(self.helper.mask.drop_pct, 1.0)
        self.assertAlmostEqual(self.helper.mask.drop, 0.0)
        self.assertEqual(self.helper.image_is_visible, False)
        self.assertAlmostEqual(self.helper.image_height, None)
        self.assertAlmostEqual(self.helper.aspect_ratio, None)
        self.assertAlmostEqual(self.helper.image_diagonal, None)
        self.assertAlmostEqual(self.helper.image_area, None)

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
        self.assertAlmostEqual(self.helper.image_height, 1.8)
        self.assertAlmostEqual(self.helper.aspect_ratio, 16.0 / 9.0)
        self.assertAlmostEqual(self.helper.image_diagonal, 3.67151195)
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
        self.assertAlmostEqual(self.helper.image_height, None)
        self.assertAlmostEqual(self.helper.aspect_ratio, None)
        self.assertAlmostEqual(self.helper.image_diagonal, None)
        self.assertAlmostEqual(self.helper.image_area, None)

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
        self.assertAlmostEqual(self.helper.image_height, 1.8)
        self.assertAlmostEqual(self.helper.aspect_ratio, 16.0 / 9.0)
        self.assertAlmostEqual(self.helper.image_diagonal, 3.67151195)
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
        self.assertAlmostEqual(self.helper.image_height, 1.361702128)
        self.assertAlmostEqual(self.helper.aspect_ratio, 2.35)
        self.assertAlmostEqual(self.helper.image_diagonal, 3.477676334)
        self.assertAlmostEqual(self.helper.image_area, 4.35744681)
