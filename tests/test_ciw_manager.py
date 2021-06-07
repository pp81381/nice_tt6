import asyncio
from nicett6.ciw_helper import CIWAspectRatioMode, ImageDef
from nicett6.decode import PctPosResponse
from nicett6.ciw_manager import CIWManager
from nicett6.cover import Cover
from nicett6.ttbus_device import TTBusDeviceAddress
from nicett6.utils import run_coro_after_delay
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, call, MagicMock


async def cleanup_task(task):
    if not task.done():
        task.cancel()
    await task


class TestCIWManager(IsolatedAsyncioTestCase):
    def setUp(self):
        mock_reader = AsyncMock(name="reader")
        mock_reader.__aiter__.return_value = [
            PctPosResponse(TTBusDeviceAddress(0x02, 0x04), 110),
            PctPosResponse(TTBusDeviceAddress(0x03, 0x04), 539),
            PctPosResponse(TTBusDeviceAddress(0x04, 0x04), 750),  # Ignored
        ]
        self.conn = AsyncMock()
        self.conn.add_reader = MagicMock(return_value=mock_reader)
        self.conn.get_writer = MagicMock(return_value=AsyncMock(name="writer"))
        self.screen_tt_addr = TTBusDeviceAddress(0x02, 0x04)
        self.screen_max_drop = 2.0
        self.mask_tt_addr = TTBusDeviceAddress(0x03, 0x04)
        self.mask_max_drop = 0.8
        self.image_def = ImageDef(0.05, 1.8, 16 / 9)
        self.mgr = CIWManager(
            self.conn,
            self.screen_tt_addr,
            self.mask_tt_addr,
            self.screen_max_drop,
            self.mask_max_drop,
            self.image_def,
        )

    async def test1(self):
        await self.mgr._start()
        writer = self.conn.get_writer.return_value
        writer.send_web_on.assert_awaited_once()
        writer.send_web_pos_request.assert_has_awaits(
            [call(self.screen_tt_addr), call(self.mask_tt_addr)]
        )

    async def test2(self):
        await self.mgr.message_tracker()
        self.assertAlmostEqual(self.mgr.helper.aspect_ratio, 2.3508668821627974)

    async def test3(self):
        self.assertEqual(self.mgr.helper.screen.is_moving, False)
        self.assertEqual(self.mgr.helper.mask.is_moving, False)
        task = asyncio.create_task(self.mgr.wait_for_motion_to_complete())
        self.addAsyncCleanup(cleanup_task, task)
        self.assertEqual(task.done(), False)
        await asyncio.sleep(CIWManager.POLLING_INTERVAL + 0.1)
        self.assertEqual(task.done(), True)
        await task

    async def test4(self):
        self.mgr.helper.screen.moved()
        task = asyncio.create_task(self.mgr.wait_for_motion_to_complete())
        self.addAsyncCleanup(cleanup_task, task)

        self.assertEqual(self.mgr.helper.screen.is_moving, True)
        self.assertEqual(self.mgr.helper.mask.is_moving, False)
        self.assertEqual(task.done(), False)

        await asyncio.sleep(CIWManager.POLLING_INTERVAL + 0.1)

        self.assertEqual(self.mgr.helper.screen.is_moving, True)
        self.assertEqual(self.mgr.helper.mask.is_moving, False)
        self.assertEqual(task.done(), False)

        await asyncio.sleep(Cover.MOVEMENT_THRESHOLD_INTERVAL)

        self.assertEqual(self.mgr.helper.screen.is_moving, False)
        self.assertEqual(self.mgr.helper.mask.is_moving, False)
        self.assertEqual(task.done(), True)
        await task

    async def set_mask_moved(self):
        self.mgr.helper.mask.moved()

    async def test5(self):
        self.mgr.helper.screen.moved()
        asyncio.create_task(
            run_coro_after_delay(
                self.set_mask_moved(), CIWManager.POLLING_INTERVAL + 0.2
            )
        )
        task = asyncio.create_task(self.mgr.wait_for_motion_to_complete())
        self.addAsyncCleanup(cleanup_task, task)

        self.assertEqual(self.mgr.helper.screen.is_moving, True)
        self.assertEqual(self.mgr.helper.mask.is_moving, False)
        self.assertEqual(task.done(), False)

        await asyncio.sleep(CIWManager.POLLING_INTERVAL + 0.1)

        self.assertEqual(self.mgr.helper.screen.is_moving, True)
        self.assertEqual(self.mgr.helper.mask.is_moving, False)
        self.assertEqual(task.done(), False)

        await asyncio.sleep(0.2)

        self.assertEqual(self.mgr.helper.screen.is_moving, True)
        self.assertEqual(self.mgr.helper.mask.is_moving, True)
        self.assertEqual(task.done(), False)

        await asyncio.sleep(Cover.MOVEMENT_THRESHOLD_INTERVAL - 0.2)

        self.assertEqual(self.mgr.helper.screen.is_moving, False)
        self.assertEqual(self.mgr.helper.mask.is_moving, True)
        self.assertEqual(task.done(), False)

        await asyncio.sleep(0.3)

        self.assertEqual(self.mgr.helper.screen.is_moving, False)
        self.assertEqual(self.mgr.helper.mask.is_moving, False)
        self.assertEqual(task.done(), True)
        await task

    async def test6(self):
        await self.mgr.send_set_aspect_ratio(
            2.35,
            CIWAspectRatioMode.FIXED_MIDDLE,
            override_screen_drop_pct=0.0,
            override_mask_drop_pct=1.0,
        )
        writer = self.conn.get_writer.return_value
        writer.send_web_move_command.assert_has_awaits(
            [
                call(self.screen_tt_addr, 0.10957446808510651),
                call(self.mask_tt_addr, 0.5385638297872342),
            ]
        )

    async def test7(self):
        await self.mgr.send_close_command()
        writer = self.conn.get_writer.return_value
        writer.send_simple_command.assert_has_awaits(
            [
                call(self.screen_tt_addr, "MOVE_UP"),
                call(self.mask_tt_addr, "MOVE_UP"),
            ]
        )

    async def test8(self):
        await self.mgr.send_open_command()
        writer = self.conn.get_writer.return_value
        writer.send_simple_command.assert_has_awaits(
            [
                call(self.screen_tt_addr, "MOVE_DOWN"),
                call(self.mask_tt_addr, "MOVE_DOWN"),
            ]
        )

    async def test9(self):
        await self.mgr.send_stop_command()
        writer = self.conn.get_writer.return_value
        writer.send_simple_command.assert_has_awaits(
            [
                call(self.screen_tt_addr, "STOP"),
                call(self.mask_tt_addr, "STOP"),
            ]
        )
