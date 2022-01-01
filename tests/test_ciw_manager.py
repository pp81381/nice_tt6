import asyncio
from nicett6.ciw_helper import CIWAspectRatioMode, ImageDef
from nicett6.ciw_manager import CIWManager
from nicett6.cover import Cover, POLLING_INTERVAL
from nicett6.cover_manager import CoverManager
from nicett6.decode import PctPosResponse
from nicett6.ttbus_device import TTBusDeviceAddress
from nicett6.utils import run_coro_after_delay
from unittest import IsolatedAsyncioTestCase
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
        PctPosResponse(TTBusDeviceAddress(0x04, 0x04), 750),  # Ignored
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
        self.assertAlmostEqual(self.ciw.helper.aspect_ratio, 2.3508668821627974)

    async def test3(self):
        self.assertEqual(self.ciw.helper.screen.is_moving, False)
        self.assertEqual(self.ciw.helper.mask.is_moving, False)
        task = asyncio.create_task(self.ciw.wait_for_motion_to_complete())
        self.addAsyncCleanup(cleanup_task, task)
        self.assertEqual(task.done(), False)
        await asyncio.sleep(POLLING_INTERVAL + 0.1)
        self.assertEqual(task.done(), True)
        await task

    async def test4(self):
        await self.ciw.helper.screen.moved()
        task = asyncio.create_task(self.ciw.wait_for_motion_to_complete())
        self.addAsyncCleanup(cleanup_task, task)

        self.assertEqual(self.ciw.helper.screen.is_moving, True)
        self.assertEqual(self.ciw.helper.mask.is_moving, False)
        self.assertEqual(task.done(), False)

        await asyncio.sleep(POLLING_INTERVAL + 0.1)

        self.assertEqual(self.ciw.helper.screen.is_moving, True)
        self.assertEqual(self.ciw.helper.mask.is_moving, False)
        self.assertEqual(task.done(), False)

        await asyncio.sleep(Cover.MOVEMENT_THRESHOLD_INTERVAL)

        self.assertEqual(self.ciw.helper.screen.is_moving, False)
        self.assertEqual(self.ciw.helper.mask.is_moving, False)
        self.assertEqual(task.done(), True)
        await task

    async def test5(self):
        await self.ciw.helper.screen.moved()
        asyncio.create_task(
            run_coro_after_delay(self.ciw.helper.mask.moved(), POLLING_INTERVAL + 0.2)
        )
        task = asyncio.create_task(self.ciw.wait_for_motion_to_complete())
        self.addAsyncCleanup(cleanup_task, task)

        self.assertEqual(self.ciw.helper.screen.is_moving, True)
        self.assertEqual(self.ciw.helper.mask.is_moving, False)
        self.assertEqual(task.done(), False)

        await asyncio.sleep(POLLING_INTERVAL + 0.1)

        self.assertEqual(self.ciw.helper.screen.is_moving, True)
        self.assertEqual(self.ciw.helper.mask.is_moving, False)
        self.assertEqual(task.done(), False)

        await asyncio.sleep(0.2)

        self.assertEqual(self.ciw.helper.screen.is_moving, True)
        self.assertEqual(self.ciw.helper.mask.is_moving, True)
        self.assertEqual(task.done(), False)

        await asyncio.sleep(Cover.MOVEMENT_THRESHOLD_INTERVAL - 0.2)

        self.assertEqual(self.ciw.helper.screen.is_moving, False)
        self.assertEqual(self.ciw.helper.mask.is_moving, True)
        self.assertEqual(task.done(), False)

        await asyncio.sleep(0.3)

        self.assertEqual(self.ciw.helper.screen.is_moving, False)
        self.assertEqual(self.ciw.helper.mask.is_moving, False)
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