import asyncio
from nicett6.ciw_helper import (
    CIWAspectRatioMode,
    CIWHelper,
    ImageDef,
    calculate_new_drops,
)
from nicett6.cover import Cover
from unittest import TestCase, IsolatedAsyncioTestCase
from unittest.mock import patch


class TestImageDef(TestCase):
    def setUp(self):
        self.image_def = ImageDef(0.05, 1.8, 16 / 9)

    def tearDown(self) -> None:
        self.image_def = None

    def test1(self):
        self.assertAlmostEqual(self.image_def.width, 3.2)

    def test2(self):
        self.assertAlmostEqual(self.image_def.implied_image_height(2.35), 1.361702128)

    def test3(self):
        with self.assertRaises(ValueError):
            self.image_def.implied_image_height(1.0)


class TestCalculateDrops(TestCase):
    def setUp(self):
        self.screen_max_drop = 2.0
        self.mask_max_drop = 0.8
        self.image_def = ImageDef(0.05, 1.8, 16 / 9)

    def calculate_new_drops(
        self, target_aspect_ratio: float, mode: CIWAspectRatioMode, baseline_drop: float
    ):
        return calculate_new_drops(
            target_aspect_ratio,
            mode,
            baseline_drop,
            self.screen_max_drop,
            self.mask_max_drop,
            self.image_def,
        )

    def test_fb1(self):
        """FIXED_BOTTOM with baseline of screen fully down, target of 2.35."""
        baseline_drop = self.screen_max_drop - self.image_def.bottom_border_height
        screen_drop_pct, mask_drop_pct = self.calculate_new_drops(
            2.35,
            CIWAspectRatioMode.FIXED_BOTTOM,
            baseline_drop,
        )
        self.assertAlmostEqual(screen_drop_pct, 0.0)  # Fully down
        self.assertAlmostEqual(mask_drop_pct, 0.26462766)

    def test_fb2(self):
        """FIXED_BOTTOM with baseline of screen fully down, target of 16:9."""
        baseline_drop = self.screen_max_drop - self.image_def.bottom_border_height
        screen_drop_pct, mask_drop_pct = self.calculate_new_drops(
            16 / 9,
            CIWAspectRatioMode.FIXED_BOTTOM,
            baseline_drop,
        )
        self.assertAlmostEqual(screen_drop_pct, 0.0)  # Fully down
        self.assertAlmostEqual(mask_drop_pct, 0.8125)

    def test_fb3(self):
        """FIXED_BOTTOM with baseline too high target of 16:9."""
        baseline_drop = (
            self.screen_max_drop - self.image_def.bottom_border_height + 0.01
        )
        with self.assertRaises(ValueError):
            self.calculate_new_drops(
                16 / 9,
                CIWAspectRatioMode.FIXED_BOTTOM,
                baseline_drop,
            )

    def test_fb4(self):
        """FIXED_BOTTOM with lowest possible baseline for target of 2.35."""
        baseline_drop = self.image_def.implied_image_height(2.35)
        screen_drop_pct, mask_drop_pct = self.calculate_new_drops(
            2.35,
            CIWAspectRatioMode.FIXED_BOTTOM,
            baseline_drop,
        )
        self.assertAlmostEqual(screen_drop_pct, 0.294148936)
        self.assertAlmostEqual(mask_drop_pct, 1.0)

    def test_fb5(self):
        """FIXED_BOTTOM with less than the lowest possible baseline for target."""
        baseline_drop = self.image_def.implied_image_height(2.35) - 0.01
        with self.assertRaises(ValueError):
            self.calculate_new_drops(
                2.35,
                CIWAspectRatioMode.FIXED_BOTTOM,
                baseline_drop,
            )

    def test_ft1(self):
        """FIXED_TOP with baseline of screen fully down, target of 16:9."""
        baseline_drop = (
            self.screen_max_drop
            - self.image_def.bottom_border_height
            - self.image_def.height
        )
        screen_drop_pct, mask_drop_pct = self.calculate_new_drops(
            16 / 9,
            CIWAspectRatioMode.FIXED_TOP,
            baseline_drop,
        )
        self.assertAlmostEqual(screen_drop_pct, 0.0)  # Fully down
        self.assertAlmostEqual(mask_drop_pct, 0.8125)

    def test_ft2(self):
        """FIXED_TOP with baseline of screen fully down, target of 2.35."""
        baseline_drop = (
            self.screen_max_drop
            - self.image_def.bottom_border_height
            - self.image_def.height
        )
        screen_drop_pct, mask_drop_pct = self.calculate_new_drops(
            2.35,
            CIWAspectRatioMode.FIXED_TOP,
            baseline_drop,
        )
        self.assertAlmostEqual(screen_drop_pct, 0.219148936)
        self.assertAlmostEqual(mask_drop_pct, 0.8125)

    def test_ft3(self):
        """FIXED_TOP with baseline of 0, target of 2.35."""
        baseline_drop = 0.0
        screen_drop_pct, mask_drop_pct = self.calculate_new_drops(
            2.35,
            CIWAspectRatioMode.FIXED_TOP,
            baseline_drop,
        )
        self.assertAlmostEqual(screen_drop_pct, 0.294148936)
        self.assertAlmostEqual(mask_drop_pct, 1.0)

    def test_ft4(self):
        """FIXED_TOP with baseline of 0, target of 16:9."""
        baseline_drop = 0.0
        screen_drop_pct, mask_drop_pct = self.calculate_new_drops(
            16 / 9,
            CIWAspectRatioMode.FIXED_TOP,
            baseline_drop,
        )
        self.assertAlmostEqual(screen_drop_pct, 0.075)
        self.assertAlmostEqual(mask_drop_pct, 1.0)

    def test_ft5(self):
        """FIXED_TOP with max possible baseline and screen fully open"""
        baseline_drop = self.mask_max_drop
        image_height = (
            self.screen_max_drop
            - self.image_def.bottom_border_height
            - self.mask_max_drop
        )
        aspect_ratio = self.image_def.width / image_height
        screen_drop_pct, mask_drop_pct = self.calculate_new_drops(
            aspect_ratio,
            CIWAspectRatioMode.FIXED_TOP,
            baseline_drop,
        )
        self.assertAlmostEqual(screen_drop_pct, 0.0)
        self.assertAlmostEqual(mask_drop_pct, 0.0)

    def test_ft6(self):
        """FIXED_TOP with greater than max possible baseline"""
        baseline_drop = self.mask_max_drop + 0.01
        image_height = (
            self.screen_max_drop
            - self.image_def.bottom_border_height
            - self.mask_max_drop
        )
        aspect_ratio = self.image_def.width / image_height
        with self.assertRaises(ValueError):
            self.calculate_new_drops(
                aspect_ratio,
                CIWAspectRatioMode.FIXED_TOP,
                baseline_drop,
            )

    def test_ft7(self):
        """FIXED_TOP with negative baseline"""
        baseline_drop = -0.1
        with self.assertRaises(ValueError):
            self.calculate_new_drops(
                2.35,
                CIWAspectRatioMode.FIXED_TOP,
                baseline_drop,
            )

    def test_fm1(self):
        """FIXED_MIDDLE with baseline in middle, target of 2.35."""
        baseline_drop = (
            self.screen_max_drop
            - self.image_def.bottom_border_height
            - self.image_def.height / 2.0
        )
        screen_drop_pct, mask_drop_pct = self.calculate_new_drops(
            2.35,
            CIWAspectRatioMode.FIXED_MIDDLE,
            baseline_drop,
        )
        self.assertAlmostEqual(screen_drop_pct, 0.109574468)
        self.assertAlmostEqual(mask_drop_pct, 0.53856383)

    def test_fm2(self):
        """FIXED_MIDDLE with baseline in middle, target of 16:9."""
        baseline_drop = (
            self.screen_max_drop
            - self.image_def.bottom_border_height
            - self.image_def.height / 2.0
        )
        screen_drop_pct, mask_drop_pct = self.calculate_new_drops(
            16 / 9,
            CIWAspectRatioMode.FIXED_MIDDLE,
            baseline_drop,
        )
        self.assertAlmostEqual(screen_drop_pct, 0.0)
        self.assertAlmostEqual(mask_drop_pct, 0.8125)

    def test_fm3(self):
        """FIXED_MIDDLE with baseline too high, target of 16:9."""
        baseline_drop = (
            self.screen_max_drop
            - self.image_def.bottom_border_height
            - self.image_def.height / 2.0
        ) + 0.01
        with self.assertRaises(ValueError):
            self.calculate_new_drops(
                16 / 9,
                CIWAspectRatioMode.FIXED_MIDDLE,
                baseline_drop,
            )

    def test_fm4(self):
        """FIXED_MIDDLE with baseline as high as possible for target of 2.35."""
        baseline_drop = self.image_def.width / 2.35 / 2.0
        screen_drop_pct, mask_drop_pct = self.calculate_new_drops(
            2.35,
            CIWAspectRatioMode.FIXED_MIDDLE,
            baseline_drop,
        )
        self.assertAlmostEqual(screen_drop_pct, 0.294148936)
        self.assertAlmostEqual(mask_drop_pct, 1.0)

    def test_fm5(self):
        """FIXED_MIDDLE with baseline slightly too high for target of 2.35."""
        baseline_drop = self.image_def.width / 2.35 / 2.0 - 0.01
        with self.assertRaises(ValueError):
            self.calculate_new_drops(
                2.35,
                CIWAspectRatioMode.FIXED_MIDDLE,
                baseline_drop,
            )


class TestCIW(IsolatedAsyncioTestCase):
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

    async def test15(self):
        """Check validations"""
        with self.assertRaises(ValueError):
            await self.helper.screen.set_drop_pct(-0.1)
        with self.assertRaises(ValueError):
            await self.helper.screen.set_drop_pct(1.1)
        with self.assertRaises(ValueError):
            await self.helper.mask.set_drop_pct(-0.1)
        with self.assertRaises(ValueError):
            await self.helper.mask.set_drop_pct(1.1)