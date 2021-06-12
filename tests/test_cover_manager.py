import asyncio
from nicett6.decode import PctPosResponse
from nicett6.cover_manager import CoverManager
from nicett6.cover import Cover
from nicett6.ttbus_device import TTBusDeviceAddress
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch


async def cleanup_task(task):
    if not task.done():
        task.cancel()
    await task


def make_mock_conn():
    mock_reader = AsyncMock(name="reader")
    mock_reader.__aiter__.return_value = [
        PctPosResponse(TTBusDeviceAddress(0x02, 0x04), 110),
        PctPosResponse(TTBusDeviceAddress(0x03, 0x04), 539),  # Ignored
    ]
    conn = AsyncMock()
    conn.add_reader = MagicMock(return_value=mock_reader)
    conn.get_writer = MagicMock(return_value=AsyncMock(name="writer"))
    conn.close = MagicMock()
    return conn


class TestCoverManager(IsolatedAsyncioTestCase):
    def setUp(self):
        self.conn = make_mock_conn()
        patcher = patch(
            "nicett6.cover_manager.TT6Connection",
            return_value=self.conn,
        )
        self.addCleanup(patcher.stop)
        patcher.start()
        self.tt_addr = TTBusDeviceAddress(0x02, 0x04)
        self.max_drop = 2.0
        self.mgr = CoverManager("DUMMY_SERIAL_PORT", self.tt_addr, self.max_drop)

    async def asyncSetUp(self):
        await self.mgr.open()

    async def test1(self):
        writer = self.conn.get_writer.return_value
        writer.send_web_on.assert_awaited_once()
        writer.send_web_pos_request.assert_awaited_with(self.tt_addr)

    async def test2(self):
        await self.mgr.message_tracker()
        self.assertAlmostEqual(self.mgr.cover.drop, 1.78)

    async def test3(self):
        self.assertFalse(self.mgr.cover.is_moving)
        self.assertTrue(await self.mgr.cover.check_for_idle())
        task = asyncio.create_task(self.mgr.wait_for_motion_to_complete())
        self.addAsyncCleanup(cleanup_task, task)
        self.assertFalse(task.done())
        await asyncio.sleep(CoverManager.POLLING_INTERVAL + 0.1)
        self.assertTrue(task.done())
        await task
        self.assertTrue(await self.mgr.cover.check_for_idle())

    async def test4(self):
        self.assertTrue(await self.mgr.cover.check_for_idle())
        await self.mgr.cover.moved()
        self.assertFalse(await self.mgr.cover.check_for_idle())

        task = asyncio.create_task(self.mgr.wait_for_motion_to_complete())
        self.addAsyncCleanup(cleanup_task, task)

        self.assertTrue(self.mgr.cover.is_moving)
        self.assertFalse(await self.mgr.cover.check_for_idle())
        self.assertFalse(task.done())

        await asyncio.sleep(CoverManager.POLLING_INTERVAL + 0.1)

        self.assertTrue(self.mgr.cover.is_moving)
        self.assertFalse(await self.mgr.cover.check_for_idle())
        self.assertFalse(task.done())

        await asyncio.sleep(Cover.MOVEMENT_THRESHOLD_INTERVAL)

        self.assertFalse(self.mgr.cover.is_moving)
        self.assertTrue(await self.mgr.cover.check_for_idle())
        self.assertTrue(task.done())
        await task

    async def test6(self):
        await self.mgr.tt6_cover.send_drop_pct_command(0.5)
        writer = self.conn.get_writer.return_value
        writer.send_web_move_command.assert_awaited_with(self.tt_addr, 0.5)

    async def test7(self):
        await self.mgr.tt6_cover.send_close_command()
        writer = self.conn.get_writer.return_value
        writer.send_simple_command.assert_awaited_with(self.tt_addr, "MOVE_UP"),

    async def test8(self):
        await self.mgr.tt6_cover.send_open_command()
        writer = self.conn.get_writer.return_value
        writer.send_simple_command.assert_awaited_with(self.tt_addr, "MOVE_DOWN"),

    async def test9(self):
        await self.mgr.tt6_cover.send_stop_command()
        writer = self.conn.get_writer.return_value
        writer.send_simple_command.assert_awaited_with(self.tt_addr, "STOP"),


class TestCoverManagerContextManager(IsolatedAsyncioTestCase):
    def setUp(self):
        self.conn = make_mock_conn()
        patcher = patch(
            "nicett6.cover_manager.TT6Connection",
            return_value=self.conn,
        )
        self.addCleanup(patcher.stop)
        patcher.start()
        self.tt_addr = TTBusDeviceAddress(0x02, 0x04)
        self.max_drop = 2.0

    async def test1(self):
        async with CoverManager(
            "DUMMY_SERIAL_PORT", self.tt_addr, self.max_drop
        ) as mgr:
            writer = self.conn.get_writer.return_value
            writer.send_web_on.assert_awaited_once()
            writer.send_web_pos_request.assert_awaited_with(self.tt_addr)
            await mgr.tt6_cover.send_open_command()
            writer = self.conn.get_writer.return_value
            writer.send_simple_command.assert_awaited_with(self.tt_addr, "MOVE_DOWN"),
            self.conn.close.assert_not_called()
        self.conn.close.assert_called_once()
