import asyncio
from nicett6.ciw_helper import CIWAspectRatioMode
from nicett6.decode import PctPosResponse
from nicett6.cover_manager import CoverManager
from nicett6.cover import Cover
from nicett6.ttbus_device import TTBusDeviceAddress
from nicett6.utils import run_coro_after_delay
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock


async def cleanup_task(task):
    if not task.done():
        task.cancel()
    await task


class TestCoverManager(IsolatedAsyncioTestCase):
    def setUp(self):
        mock_reader = AsyncMock(name="reader")
        mock_reader.__aiter__.return_value = [
            PctPosResponse(TTBusDeviceAddress(0x02, 0x04), 110),
            PctPosResponse(TTBusDeviceAddress(0x03, 0x04), 539),  # Ignored
        ]
        self.conn = AsyncMock()
        self.conn.add_reader = MagicMock(return_value=mock_reader)
        self.conn.get_writer = MagicMock(return_value=AsyncMock(name="writer"))
        self.tt_addr = TTBusDeviceAddress(0x02, 0x04)
        self.max_drop = 2.0
        self.mgr = CoverManager(self.conn, self.tt_addr, self.max_drop)

    async def test1(self):
        await self.mgr._start()
        writer = self.conn.get_writer.return_value
        writer.send_web_on.assert_awaited_once()
        writer.send_web_pos_request.assert_awaited_with(self.tt_addr)

    async def test2(self):
        await self.mgr.message_tracker()
        self.assertAlmostEqual(self.mgr.cover.drop, 1.78)

    async def test3(self):
        self.assertEqual(self.mgr.cover.is_moving, False)
        task = asyncio.create_task(self.mgr.wait_for_motion_to_complete())
        self.addAsyncCleanup(cleanup_task, task)
        self.assertEqual(task.done(), False)
        await asyncio.sleep(CoverManager.POLLING_INTERVAL + 0.1)
        self.assertEqual(task.done(), True)
        await task

    async def test4(self):
        self.mgr.cover.moved()
        task = asyncio.create_task(self.mgr.wait_for_motion_to_complete())
        self.addAsyncCleanup(cleanup_task, task)

        self.assertEqual(self.mgr.cover.is_moving, True)
        self.assertEqual(task.done(), False)

        await asyncio.sleep(CoverManager.POLLING_INTERVAL + 0.1)

        self.assertEqual(self.mgr.cover.is_moving, True)
        self.assertEqual(task.done(), False)

        await asyncio.sleep(Cover.MOVEMENT_THRESHOLD_INTERVAL)

        self.assertEqual(self.mgr.cover.is_moving, False)
        self.assertEqual(task.done(), True)
        await task

    async def set_mask_moved(self):
        self.mgr.helper.mask.moved()

    async def test6(self):
        await self.mgr.send_drop_pct_command(0.5)
        writer = self.conn.get_writer.return_value
        writer.send_web_move_command.assert_awaited_with(self.tt_addr, 0.5)

    async def test7(self):
        await self.mgr.send_close_command()
        writer = self.conn.get_writer.return_value
        writer.send_simple_command.assert_awaited_with(self.tt_addr, "MOVE_UP"),

    async def test8(self):
        await self.mgr.send_open_command()
        writer = self.conn.get_writer.return_value
        writer.send_simple_command.assert_awaited_with(self.tt_addr, "MOVE_DOWN"),

    async def test9(self):
        await self.mgr.send_stop_command()
        writer = self.conn.get_writer.return_value
        writer.send_simple_command.assert_awaited_with(self.tt_addr, "STOP"),
