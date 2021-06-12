import asyncio
from nicett6.ciw_helper import CIWAspectRatioMode, CIWHelper, ImageDef
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


class TestCIW(IsolatedAsyncioTestCase):
    def setUp(self):
        image_def = ImageDef(0.05, 1.8, 16 / 9)
        self.helper = CIWHelper(2.0, 0.8, image_def)

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

    async def test6(self):
        """Screen fully down, mask set for 2.35 FIXED_BOTTOM"""
        await self.helper.screen.set_drop_pct(0.0)

        screen_drop_pct, mask_drop_pct = self.helper._calculate_new_drops(
            2.35, CIWAspectRatioMode.FIXED_BOTTOM
        )
        self.assertAlmostEqual(screen_drop_pct, 0.0)
        self.assertAlmostEqual(mask_drop_pct, 0.26462766)

        await self.helper.screen.set_drop_pct(screen_drop_pct)
        await self.helper.mask.set_drop_pct(mask_drop_pct)
        self.assertAlmostEqual(self.helper.screen.drop_pct, 0.0)
        self.assertAlmostEqual(self.helper.screen.drop, 2.0)
        self.assertAlmostEqual(self.helper.mask.drop_pct, 0.26462766)
        self.assertAlmostEqual(self.helper.mask.drop, 0.588297872)
        self.assertEqual(self.helper.image_is_visible, True)
        self.assertAlmostEqual(self.helper.image_height, 1.361702128)
        self.assertAlmostEqual(self.helper.aspect_ratio, 2.35)

    async def test7(self):
        """Screen fully down, mask set for 16:9 FIXED_TOP (should just move mask)"""
        await self.helper.screen.set_drop_pct(0.0)

        screen_drop_pct, mask_drop_pct = self.helper._calculate_new_drops(
            16 / 9, CIWAspectRatioMode.FIXED_TOP
        )
        self.assertAlmostEqual(screen_drop_pct, 0.0)
        self.assertAlmostEqual(mask_drop_pct, 0.8125)

        await self.helper.mask.set_drop_pct(mask_drop_pct)
        self.assertAlmostEqual(self.helper.screen.drop_pct, 0.0)
        self.assertAlmostEqual(self.helper.screen.drop, 2.0)
        self.assertAlmostEqual(self.helper.mask.drop_pct, 0.8125)
        self.assertAlmostEqual(self.helper.mask.drop, 0.15)
        self.assertEqual(self.helper.image_is_visible, True)
        self.assertAlmostEqual(self.helper.image_height, 1.8)
        self.assertAlmostEqual(self.helper.aspect_ratio, 16 / 9)

    async def test8a(self):
        """Screen fully down, mask fully up, 2.35 FIXED_TOP"""
        await self.helper.screen.set_drop_pct(0.0)

        screen_drop_pct, mask_drop_pct = self.helper._calculate_new_drops(
            2.35, CIWAspectRatioMode.FIXED_TOP
        )
        self.assertAlmostEqual(screen_drop_pct, 0.219148936)
        self.assertAlmostEqual(mask_drop_pct, 0.8125)

        await self.helper.screen.set_drop_pct(screen_drop_pct)
        await self.helper.mask.set_drop_pct(mask_drop_pct)
        self.assertAlmostEqual(self.helper.screen.drop_pct, 0.219148936)
        self.assertAlmostEqual(self.helper.screen.drop, 1.561702128)
        self.assertAlmostEqual(self.helper.mask.drop_pct, 0.8125)
        self.assertAlmostEqual(self.helper.mask.drop, 0.15)
        self.assertEqual(self.helper.image_is_visible, True)
        self.assertAlmostEqual(self.helper.image_height, 1.361702128)
        self.assertAlmostEqual(self.helper.aspect_ratio, 2.35)

    async def test8b(self):
        """Screen fully down, mask set for 2.35 FIXED_TOP"""
        await self.helper.screen.set_drop_pct(0.0)
        await self.helper.mask.set_drop_pct(0.8125)

        screen_drop_pct, mask_drop_pct = self.helper._calculate_new_drops(
            2.35, CIWAspectRatioMode.FIXED_TOP
        )
        self.assertAlmostEqual(screen_drop_pct, 0.219148936)
        self.assertAlmostEqual(mask_drop_pct, 0.8125)

        await self.helper.screen.set_drop_pct(screen_drop_pct)
        await self.helper.mask.set_drop_pct(mask_drop_pct)
        self.assertAlmostEqual(self.helper.screen.drop_pct, 0.219148936)
        self.assertAlmostEqual(self.helper.screen.drop, 1.561702128)
        self.assertAlmostEqual(self.helper.mask.drop_pct, 0.8125)
        self.assertAlmostEqual(self.helper.mask.drop, 0.15)
        self.assertEqual(self.helper.image_is_visible, True)
        self.assertAlmostEqual(self.helper.image_height, 1.361702128)
        self.assertAlmostEqual(self.helper.aspect_ratio, 2.35)

    async def test8c(self):
        """Scenario screen fully down, mask set for 2.35 FIXED_TOP"""
        screen_drop_pct, mask_drop_pct = self.helper._calculate_new_drops(
            2.35,
            CIWAspectRatioMode.FIXED_TOP,
            override_screen_drop_pct=0.0,
            override_mask_drop_pct=0.8125,
        )
        self.assertAlmostEqual(screen_drop_pct, 0.219148936)
        self.assertAlmostEqual(mask_drop_pct, 0.8125)

        await self.helper.screen.set_drop_pct(screen_drop_pct)
        await self.helper.mask.set_drop_pct(mask_drop_pct)
        self.assertAlmostEqual(self.helper.screen.drop_pct, 0.219148936)
        self.assertAlmostEqual(self.helper.screen.drop, 1.561702128)
        self.assertAlmostEqual(self.helper.mask.drop_pct, 0.8125)
        self.assertAlmostEqual(self.helper.mask.drop, 0.15)
        self.assertEqual(self.helper.image_is_visible, True)
        self.assertAlmostEqual(self.helper.image_height, 1.361702128)
        self.assertAlmostEqual(self.helper.aspect_ratio, 2.35)

    async def test9a(self):
        """Screen fully down, mask set for 2.35 FIXED_MIDDLE"""
        await self.helper.screen.set_drop_pct(0.0)

        screen_drop_pct, mask_drop_pct = self.helper._calculate_new_drops(
            2.35, CIWAspectRatioMode.FIXED_MIDDLE
        )
        self.assertAlmostEqual(screen_drop_pct, 0.109574468)
        self.assertAlmostEqual(mask_drop_pct, 0.53856383)

        await self.helper.screen.set_drop_pct(screen_drop_pct)
        await self.helper.mask.set_drop_pct(mask_drop_pct)
        self.assertAlmostEqual(self.helper.screen.drop_pct, 0.109574468)
        self.assertAlmostEqual(self.helper.screen.drop, 1.780851064)
        self.assertAlmostEqual(self.helper.mask.drop_pct, 0.53856383)
        self.assertAlmostEqual(self.helper.mask.drop, 0.369148936)
        self.assertEqual(self.helper.image_is_visible, True)
        self.assertAlmostEqual(self.helper.image_height, 1.361702128)
        self.assertAlmostEqual(self.helper.aspect_ratio, 2.35)

    async def test9b(self):
        """Scenario screen fully down, mask set for 2.35 FIXED_MIDDLE"""
        screen_drop_pct, mask_drop_pct = self.helper._calculate_new_drops(
            2.35, CIWAspectRatioMode.FIXED_MIDDLE, override_screen_drop_pct=0.0
        )
        self.assertAlmostEqual(screen_drop_pct, 0.109574468)
        self.assertAlmostEqual(mask_drop_pct, 0.53856383)

        await self.helper.screen.set_drop_pct(screen_drop_pct)
        await self.helper.mask.set_drop_pct(mask_drop_pct)
        self.assertAlmostEqual(self.helper.screen.drop_pct, 0.109574468)
        self.assertAlmostEqual(self.helper.screen.drop, 1.780851064)
        self.assertAlmostEqual(self.helper.mask.drop_pct, 0.53856383)
        self.assertAlmostEqual(self.helper.mask.drop, 0.369148936)
        self.assertEqual(self.helper.image_is_visible, True)
        self.assertAlmostEqual(self.helper.image_height, 1.361702128)
        self.assertAlmostEqual(self.helper.aspect_ratio, 2.35)

    async def test10(self):
        """Screen fully down, mask set for 16:9 FIXED_MIDDLE (should just move mask)"""
        await self.helper.screen.set_drop_pct(0.0)

        screen_drop_pct, mask_drop_pct = self.helper._calculate_new_drops(
            16 / 9, CIWAspectRatioMode.FIXED_MIDDLE
        )
        self.assertAlmostEqual(screen_drop_pct, 0.0)
        self.assertAlmostEqual(mask_drop_pct, 0.8125)

        await self.helper.screen.set_drop_pct(screen_drop_pct)
        await self.helper.mask.set_drop_pct(mask_drop_pct)
        self.assertAlmostEqual(self.helper.screen.drop_pct, 0.0)
        self.assertAlmostEqual(self.helper.screen.drop, 2.0)
        self.assertAlmostEqual(self.helper.mask.drop_pct, 0.8125)
        self.assertAlmostEqual(self.helper.mask.drop, 0.15)
        self.assertEqual(self.helper.image_is_visible, True)
        self.assertAlmostEqual(self.helper.image_height, 1.8)
        self.assertAlmostEqual(self.helper.aspect_ratio, 16 / 9)

    async def test11(self):
        """Screen fully up, mask set for 2.35 FIXED_TOP"""
        screen_drop_pct, mask_drop_pct = self.helper._calculate_new_drops(
            2.35, CIWAspectRatioMode.FIXED_TOP
        )
        self.assertAlmostEqual(screen_drop_pct, 0.294148936)
        self.assertAlmostEqual(mask_drop_pct, 1.0)

        await self.helper.screen.set_drop_pct(screen_drop_pct)
        await self.helper.mask.set_drop_pct(mask_drop_pct)
        self.assertAlmostEqual(self.helper.screen.drop_pct, 0.294148936)
        self.assertAlmostEqual(self.helper.screen.drop, 1.411702128)
        self.assertAlmostEqual(self.helper.mask.drop_pct, 1.0)
        self.assertAlmostEqual(self.helper.mask.drop, 0)
        self.assertEqual(self.helper.image_is_visible, True)
        self.assertAlmostEqual(self.helper.image_height, 1.361702128)
        self.assertAlmostEqual(self.helper.aspect_ratio, 2.35)

    async def test12(self):
        """Screen fully up, mask set for 16:9 FIXED_TOP"""
        screen_drop_pct, mask_drop_pct = self.helper._calculate_new_drops(
            16 / 9, CIWAspectRatioMode.FIXED_TOP
        )
        self.assertAlmostEqual(screen_drop_pct, 0.075)
        self.assertAlmostEqual(mask_drop_pct, 1.0)

        await self.helper.screen.set_drop_pct(screen_drop_pct)
        await self.helper.mask.set_drop_pct(mask_drop_pct)
        self.assertAlmostEqual(self.helper.screen.drop_pct, 0.075)
        self.assertAlmostEqual(self.helper.screen.drop, 1.85)
        self.assertAlmostEqual(self.helper.mask.drop_pct, 1.0)
        self.assertAlmostEqual(self.helper.mask.drop, 0)
        self.assertEqual(self.helper.image_is_visible, True)
        self.assertAlmostEqual(self.helper.image_height, 1.8)
        self.assertAlmostEqual(self.helper.aspect_ratio, 16 / 9)

    async def test13(self):
        """Screen fully up, mask down by 0.05, set 2.35 FIXED_TOP changed to 16 / 9 FIXED_MIDDLE (won't fit)"""
        await self.helper.screen.set_drop_pct(1.0)
        self.helper.mask_drop_pct = 0.95 / self.helper.mask.max_drop

        screen_drop_pct, mask_drop_pct = self.helper._calculate_new_drops(
            2.35, CIWAspectRatioMode.FIXED_TOP
        )
        await self.helper.screen.set_drop_pct(screen_drop_pct)
        await self.helper.mask.set_drop_pct(mask_drop_pct)

        with self.assertRaises(ValueError):
            self.helper._calculate_new_drops(16 / 9, CIWAspectRatioMode.FIXED_MIDDLE)

    async def test14(self):
        """Screen half down, mask up, set 16:9 FIXED_BOTTOM (won't fit)"""
        await self.helper.screen.set_drop_pct(0.5)
        await self.helper.mask.set_drop_pct(1.0)
        with self.assertRaises(ValueError):
            self.helper._calculate_new_drops(16 / 9, CIWAspectRatioMode.FIXED_BOTTOM)

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

    async def test16(self):
        """Mask fully down, set 16:9 FIXED_TOP (won't fit)"""
        await self.helper.mask.set_drop_pct(0.0)
        with self.assertRaises(ValueError):
            self.helper._calculate_new_drops(16 / 9, CIWAspectRatioMode.FIXED_TOP)

    async def test17(self):
        """Mask fully down, set 16:9 FIXED_MIDDLE (won't fit)"""
        await self.helper.mask.set_drop_pct(0.0)
        with self.assertRaises(ValueError):
            self.helper._calculate_new_drops(16 / 9, CIWAspectRatioMode.FIXED_MIDDLE)

    async def test18(self):
        """Test check_for_idle with both covers at once"""
        with patch("nicett6.cover.Cover.notify_observers") as p:
            self.assertTrue(await self.helper.check_for_idle())
            p.assert_not_awaited()
            await self.helper.screen.set_drop_pct(0.9)
            p.assert_awaited_once()
            p.reset_mock()
            await self.helper.mask.set_drop_pct(0.9)
            p.assert_awaited_once()
            p.reset_mock()
            self.assertFalse(await self.helper.check_for_idle())
            p.assert_not_awaited()
            await asyncio.sleep(Cover.MOVEMENT_THRESHOLD_INTERVAL + 0.1)
            self.assertTrue(await self.helper.check_for_idle())
            self.assertEqual(p.await_count, 2)

    async def test19(self):
        """Test check_for_idle with mask only"""
        with patch("nicett6.cover.Cover.notify_observers") as p:
            self.assertTrue(await self.helper.check_for_idle())
            p.assert_not_awaited()
            await self.helper.mask.set_drop_pct(0.9)
            p.assert_awaited_once()
            p.reset_mock()
            self.assertFalse(await self.helper.check_for_idle())
            p.assert_not_awaited()
            await asyncio.sleep(Cover.MOVEMENT_THRESHOLD_INTERVAL + 0.1)
            self.assertTrue(await self.helper.check_for_idle())
            self.assertEqual(p.await_count, 1)

    async def test20(self):
        """Test check_for_idle with screen only"""
        with patch("nicett6.cover.Cover.notify_observers") as p:
            self.assertTrue(await self.helper.check_for_idle())
            p.assert_not_awaited()
            await self.helper.screen.set_drop_pct(0.9)
            p.assert_awaited_once()
            p.reset_mock()
            self.assertFalse(await self.helper.check_for_idle())
            p.assert_not_awaited()
            await asyncio.sleep(Cover.MOVEMENT_THRESHOLD_INTERVAL + 0.1)
            self.assertTrue(await self.helper.check_for_idle())
            self.assertEqual(p.await_count, 1)
