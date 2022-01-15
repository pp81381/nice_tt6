import asyncio
from nicett6.ciw_helper import CIWHelper, ImageDef
from nicett6.ciw_manager import (
    CIWManager,
    CIWAspectRatioMode,
    calculate_new_drops,
    check_baseline_drop,
)
from nicett6.cover import Cover, POLLING_INTERVAL
from nicett6.cover_manager import CoverManager
from nicett6.decode import PctPosResponse
from nicett6.ttbus_device import TTBusDeviceAddress
from nicett6.utils import run_coro_after_delay
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, call, MagicMock, patch


async def cleanup_task(task):
    if not task.done():
        task.cancel()
    await task


def make_mock_conn():
    mock_reader = AsyncMock(name="reader")
    mock_reader.__aiter__.return_value = [
        PctPosResponse(TTBusDeviceAddress(0x02, 0x04), 110),
        PctPosResponse(TTBusDeviceAddress(0x03, 0x04), 539),
        PctPosResponse(TTBusDeviceAddress(0x04, 0x04), 750),  # Address 0x04 Ignored
    ]
    conn = AsyncMock()
    conn.add_reader = MagicMock(return_value=mock_reader)
    conn.get_writer = MagicMock(return_value=AsyncMock(name="writer"))
    conn.close = MagicMock()
    return conn


class TestCIWManager(IsolatedAsyncioTestCase):
    def setUp(self):
        self.conn = make_mock_conn()
        patcher = patch(
            "nicett6.cover_manager.TT6Connection",
            return_value=self.conn,
        )
        self.addCleanup(patcher.stop)
        patcher.start()
        self.screen_tt_addr = TTBusDeviceAddress(0x02, 0x04)
        self.mask_tt_addr = TTBusDeviceAddress(0x03, 0x04)

    async def asyncSetUp(self):
        self.mgr = CoverManager("DUMMY_SERIAL_PORT")
        await self.mgr.open()
        screen_tt6_cover = await self.mgr.add_cover(
            self.screen_tt_addr,
            Cover("Screen", 2.0),
        )
        mask_tt6_cover = await self.mgr.add_cover(
            self.mask_tt_addr,
            Cover("Mask", 0.8),
        )
        self.ciw = CIWManager(
            screen_tt6_cover,
            mask_tt6_cover,
            ImageDef(0.05, 1.8, 16 / 9),
        )

    async def test1(self):
        writer = self.conn.get_writer.return_value
        writer.send_web_on.assert_awaited_once()
        writer.send_web_pos_request.assert_has_awaits(
            [call(self.screen_tt_addr), call(self.mask_tt_addr)]
        )

    async def test2(self):
        await self.mgr.message_tracker()
        helper = CIWHelper(
            self.ciw.screen_tt6_cover.cover,
            self.ciw.mask_tt6_cover.cover,
            self.ciw.image_def,
        )
        self.assertAlmostEqual(helper.aspect_ratio, 2.3508668821627974)

    async def test3(self):
        self.assertEqual(self.ciw.screen_tt6_cover.cover.is_moving, False)
        self.assertEqual(self.ciw.mask_tt6_cover.cover.is_moving, False)
        task = asyncio.create_task(self.ciw.wait_for_motion_to_complete())
        self.addAsyncCleanup(cleanup_task, task)
        self.assertEqual(task.done(), False)
        await asyncio.sleep(POLLING_INTERVAL + 0.1)
        self.assertEqual(task.done(), True)
        await task

    async def test4(self):
        await self.ciw.screen_tt6_cover.cover.moved()
        task = asyncio.create_task(self.ciw.wait_for_motion_to_complete())
        self.addAsyncCleanup(cleanup_task, task)

        self.assertEqual(self.ciw.screen_tt6_cover.cover.is_moving, True)
        self.assertEqual(self.ciw.mask_tt6_cover.cover.is_moving, False)
        self.assertEqual(task.done(), False)

        await asyncio.sleep(POLLING_INTERVAL + 0.1)

        self.assertEqual(self.ciw.screen_tt6_cover.cover.is_moving, True)
        self.assertEqual(self.ciw.mask_tt6_cover.cover.is_moving, False)
        self.assertEqual(task.done(), False)

        await asyncio.sleep(Cover.MOVEMENT_THRESHOLD_INTERVAL)

        self.assertEqual(self.ciw.screen_tt6_cover.cover.is_moving, False)
        self.assertEqual(self.ciw.mask_tt6_cover.cover.is_moving, False)
        self.assertEqual(task.done(), True)
        await task

    async def test5(self):
        await self.ciw.screen_tt6_cover.cover.moved()
        asyncio.create_task(
            run_coro_after_delay(
                self.ciw.mask_tt6_cover.cover.moved(), POLLING_INTERVAL + 0.2
            )
        )
        task = asyncio.create_task(self.ciw.wait_for_motion_to_complete())
        self.addAsyncCleanup(cleanup_task, task)

        self.assertEqual(self.ciw.screen_tt6_cover.cover.is_moving, True)
        self.assertEqual(self.ciw.mask_tt6_cover.cover.is_moving, False)
        self.assertEqual(task.done(), False)

        await asyncio.sleep(POLLING_INTERVAL + 0.1)

        self.assertEqual(self.ciw.screen_tt6_cover.cover.is_moving, True)
        self.assertEqual(self.ciw.mask_tt6_cover.cover.is_moving, False)
        self.assertEqual(task.done(), False)

        await asyncio.sleep(0.2)

        self.assertEqual(self.ciw.screen_tt6_cover.cover.is_moving, True)
        self.assertEqual(self.ciw.mask_tt6_cover.cover.is_moving, True)
        self.assertEqual(task.done(), False)

        await asyncio.sleep(Cover.MOVEMENT_THRESHOLD_INTERVAL - 0.2)

        self.assertEqual(self.ciw.screen_tt6_cover.cover.is_moving, False)
        self.assertEqual(self.ciw.mask_tt6_cover.cover.is_moving, True)
        self.assertEqual(task.done(), False)

        await asyncio.sleep(0.3)

        self.assertEqual(self.ciw.screen_tt6_cover.cover.is_moving, False)
        self.assertEqual(self.ciw.mask_tt6_cover.cover.is_moving, False)
        self.assertEqual(task.done(), True)
        await task

    async def test6(self):
        await self.ciw.send_set_aspect_ratio(
            2.35,
            CIWAspectRatioMode.FIXED_MIDDLE,
            1.05,
        )
        writer = self.conn.get_writer.return_value
        writer.send_web_move_command.assert_has_awaits(
            [
                call(self.screen_tt_addr, 0.1095744680851064),
                call(self.mask_tt_addr, 0.5385638297872338),
            ]
        )

    async def test7(self):
        await self.ciw.send_close_command()
        writer = self.conn.get_writer.return_value
        writer.send_simple_command.assert_has_awaits(
            [
                call(self.screen_tt_addr, "MOVE_UP"),
                call(self.mask_tt_addr, "MOVE_UP"),
            ]
        )

    async def test8(self):
        await self.ciw.send_open_command()
        writer = self.conn.get_writer.return_value
        writer.send_simple_command.assert_has_awaits(
            [
                call(self.screen_tt_addr, "MOVE_DOWN"),
                call(self.mask_tt_addr, "MOVE_DOWN"),
            ]
        )

    async def test9(self):
        await self.ciw.send_stop_command()
        writer = self.conn.get_writer.return_value
        writer.send_simple_command.assert_has_awaits(
            [
                call(self.screen_tt_addr, "STOP"),
                call(self.mask_tt_addr, "STOP"),
            ]
        )


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

    def check_baseline_drop(self, mode: CIWAspectRatioMode, baseline_drop: float):
        return check_baseline_drop(
            mode,
            baseline_drop,
            self.screen_max_drop,
            self.mask_max_drop,
            self.image_def,
        )

    def test_bd_fb1(self):
        self.check_baseline_drop(
            CIWAspectRatioMode.FIXED_BOTTOM, 0.9143
        )  # min should be 0.9142857142857143

    def test_bd_fb2(self):
        with self.assertRaises(ValueError):
            self.check_baseline_drop(
                CIWAspectRatioMode.FIXED_BOTTOM, 0.9142
            )  # min should be 0.9142857142857143

    def test_bd_fb3(self):
        self.check_baseline_drop(
            CIWAspectRatioMode.FIXED_BOTTOM, 1.95
        )  # max should be 1.95

    def test_bd_fb4(self):
        with self.assertRaises(ValueError):
            self.check_baseline_drop(
                CIWAspectRatioMode.FIXED_BOTTOM, 1.951
            )  # max should be 1.95

    def test_bd_ft1(self):
        self.check_baseline_drop(CIWAspectRatioMode.FIXED_TOP, 0.0)  # min should be 0.0

    def test_bd_ft2(self):
        with self.assertRaises(ValueError):
            self.check_baseline_drop(
                CIWAspectRatioMode.FIXED_TOP, -0.001
            )  # min should be 0.0

    def test_bd_ft3(self):
        self.check_baseline_drop(CIWAspectRatioMode.FIXED_TOP, 0.8)  # max should be 0.8

    def test_bd_ft4(self):
        with self.assertRaises(ValueError):
            self.check_baseline_drop(
                CIWAspectRatioMode.FIXED_TOP, 0.801
            )  # max should be 0.8

    def test_bd_fm1(self):
        self.check_baseline_drop(
            CIWAspectRatioMode.FIXED_MIDDLE, 0.4572
        )  # min should be 0.45714285714285713

    def test_bd_fm2(self):
        with self.assertRaises(ValueError):
            self.check_baseline_drop(
                CIWAspectRatioMode.FIXED_MIDDLE, 0.4571
            )  # min should be 0.45714285714285713

    def test_bd_fm3(self):
        self.check_baseline_drop(
            CIWAspectRatioMode.FIXED_MIDDLE, 1.4928
        )  # max should be 1.4928571428571429

    def test_bd_fm4(self):
        with self.assertRaises(ValueError):
            self.check_baseline_drop(
                CIWAspectRatioMode.FIXED_MIDDLE, 1.4929
            )  # max should be 1.4928571428571429

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
        """FIXED_BOTTOM with baseline too high, target of 16:9."""
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
        # Used to raise ValueError
        screen_drop_pct, mask_drop_pct = self.calculate_new_drops(
            2.35,
            CIWAspectRatioMode.FIXED_BOTTOM,
            baseline_drop,
        )
        self.assertAlmostEqual(screen_drop_pct, 0.299148936)
        self.assertAlmostEqual(
            mask_drop_pct, 1.0125
        )  # Will be capped and hide top of image

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
        """FIXED_MIDDLE with baseline too high for target of 16:9."""
        baseline_drop = (
            self.screen_max_drop
            - self.image_def.bottom_border_height
            - self.image_def.height / 2.0
        ) + 0.01
        # Used to raise ValueError
        screen_drop_pct, mask_drop_pct = self.calculate_new_drops(
            16 / 9,
            CIWAspectRatioMode.FIXED_MIDDLE,
            baseline_drop,
        )
        self.assertAlmostEqual(screen_drop_pct, -0.005)  # Will be floored
        self.assertAlmostEqual(mask_drop_pct, 0.8)  # Will trim a bit off the top

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
        # Used to raise ValueError
        screen_drop_pct, mask_drop_pct = self.calculate_new_drops(
            2.35,
            CIWAspectRatioMode.FIXED_MIDDLE,
            baseline_drop,
        )
        self.assertAlmostEqual(screen_drop_pct, 0.2991489362)
        self.assertAlmostEqual(mask_drop_pct, 1.0125)  # Will be floored
