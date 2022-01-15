import asyncio
from nicett6.decode import PctAckResponse, PctPosResponse
from nicett6.cover_manager import CoverManager
from nicett6.cover import Cover
from nicett6.ttbus_device import TTBusDeviceAddress
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

TEST_READER_POS_RESPONSE = [
    PctPosResponse(TTBusDeviceAddress(0x02, 0x04), 110),
    PctPosResponse(TTBusDeviceAddress(0x03, 0x04), 539),  # Address 0x03 Ignored
]


def make_mock_conn(reader_return_value):
    mock_reader = AsyncMock(name="reader")
    mock_reader.__aiter__.return_value = reader_return_value
    conn = AsyncMock()
    conn.add_reader = MagicMock(return_value=mock_reader)
    conn.get_writer = MagicMock(return_value=AsyncMock(name="writer"))
    conn.close = MagicMock()
    return conn


class TestCoverManagerOpen(IsolatedAsyncioTestCase):
    async def test1(self):
        conn = make_mock_conn(TEST_READER_POS_RESPONSE)
        with patch(
            "nicett6.cover_manager.TT6Connection",
            return_value=conn,
        ):
            mgr = CoverManager("DUMMY_SERIAL_PORT")
            await mgr.open()
            writer = conn.get_writer.return_value
            writer.send_web_on.assert_awaited_once()


class TestCoverManager(IsolatedAsyncioTestCase):
    def setUp(self):
        self.conn = make_mock_conn(TEST_READER_POS_RESPONSE)
        patcher = patch(
            "nicett6.cover_manager.TT6Connection",
            return_value=self.conn,
        )
        self.addCleanup(patcher.stop)
        patcher.start()
        self.tt_addr = TTBusDeviceAddress(0x02, 0x04)
        self.max_drop = 2.0
        self.mgr = CoverManager("DUMMY_SERIAL_PORT")

    async def asyncSetUp(self):
        await self.mgr.open()
        await self.mgr.add_cover(self.tt_addr, Cover("Cover", self.max_drop))
        self.tt6_cover = self.mgr._tt6_covers_dict[self.tt_addr]
        self.cover = self.tt6_cover.cover

    async def test1(self):
        writer = self.conn.get_writer.return_value
        writer.send_web_on.assert_awaited_once()
        writer.send_web_pos_request.assert_awaited_with(self.tt_addr)

    async def test2(self):
        await self.mgr.message_tracker()
        self.assertAlmostEqual(self.cover.drop, 1.78)

    async def test6(self):
        await self.tt6_cover.send_drop_pct_command(0.5)
        writer = self.conn.get_writer.return_value
        writer.send_web_move_command.assert_awaited_with(self.tt_addr, 0.5)

    async def test7(self):
        await self.tt6_cover.send_close_command()
        writer = self.conn.get_writer.return_value
        writer.send_simple_command.assert_awaited_with(self.tt_addr, "MOVE_UP"),

    async def test8(self):
        await self.tt6_cover.send_open_command()
        writer = self.conn.get_writer.return_value
        writer.send_simple_command.assert_awaited_with(self.tt_addr, "MOVE_DOWN"),

    async def test9(self):
        await self.tt6_cover.send_stop_command()
        writer = self.conn.get_writer.return_value
        writer.send_simple_command.assert_awaited_with(self.tt_addr, "STOP"),

    async def test10(self):
        """Test the notifier"""
        self.assertTrue(self.cover.is_closed)
        self.assertFalse(self.cover.is_moving)
        self.assertFalse(self.cover.is_opening)
        self.assertFalse(self.cover.is_closing)
        self.assertIsNone(self.tt6_cover._notifier._task)
        await self.cover.set_drop_pct(0.8)
        self.assertAlmostEqual(self.cover._prev_drop_pct, 1.0)
        self.assertFalse(self.cover.is_closed)
        self.assertTrue(self.cover.is_moving)
        self.assertTrue(self.cover.is_opening)
        self.assertFalse(self.cover.is_closing)
        self.assertIsNotNone(self.tt6_cover._notifier._task)
        self.assertFalse(self.tt6_cover._notifier._task.done())
        await asyncio.sleep(self.cover.MOVEMENT_THRESHOLD_INTERVAL + 0.01)
        self.assertAlmostEqual(self.cover._prev_drop_pct, 1.0)  #!!
        self.assertFalse(self.cover.is_closed)
        self.assertFalse(self.cover.is_moving)
        self.assertFalse(self.cover.is_opening)
        self.assertFalse(self.cover.is_closing)
        self.assertIsNotNone(self.tt6_cover._notifier._task)
        self.assertFalse(self.tt6_cover._notifier._task.done())
        await asyncio.sleep(
            self.tt6_cover._notifier.POST_MOVEMENT_ALLOWANCE
        )  # Wait for notifier
        self.assertAlmostEqual(self.cover._prev_drop_pct, 0.8)  # !!
        self.assertFalse(self.cover.is_closed)
        self.assertFalse(self.cover.is_moving)
        self.assertFalse(self.cover.is_opening)
        self.assertFalse(self.cover.is_closing)
        self.assertIsNotNone(self.tt6_cover._notifier._task)
        self.assertTrue(self.tt6_cover._notifier._task.done())
        await self.cover.moved()  # We are moving but we don't know the direction yet
        self.assertAlmostEqual(self.cover._prev_drop_pct, 0.8)
        self.assertFalse(self.cover.is_closed)
        self.assertTrue(self.cover.is_moving)
        self.assertFalse(self.cover.is_opening)
        self.assertFalse(self.cover.is_closing)


class TestCoverManagerContextManager(IsolatedAsyncioTestCase):
    def setUp(self):
        self.conn = make_mock_conn(TEST_READER_POS_RESPONSE)
        patcher = patch(
            "nicett6.cover_manager.TT6Connection",
            return_value=self.conn,
        )
        self.addCleanup(patcher.stop)
        patcher.start()
        self.tt_addr = TTBusDeviceAddress(0x02, 0x04)
        self.max_drop = 2.0

    async def test1(self):
        async with CoverManager("DUMMY_SERIAL_PORT") as mgr:
            tt6_cover = await mgr.add_cover(self.tt_addr, Cover("Cover", self.max_drop))
            writer = self.conn.get_writer.return_value
            writer.send_web_on.assert_awaited_once()
            writer.send_web_pos_request.assert_awaited_with(self.tt_addr)
            await tt6_cover.send_open_command()
            writer = self.conn.get_writer.return_value
            writer.send_simple_command.assert_awaited_with(self.tt_addr, "MOVE_DOWN"),
            self.conn.close.assert_not_called()
        self.conn.close.assert_called_once()


class TestCoverManagerMessageTracker(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tt_addr = TTBusDeviceAddress(0x02, 0x04)
        self.cover = AsyncMock()
        self.tt6_cover = AsyncMock()
        self.tt6_cover.cover = self.cover
        self.mgr = CoverManager("DUMMY_SERIAL_PORT")
        self.mgr._tt6_covers_dict[self.tt_addr] = self.tt6_cover

    async def test1(self):
        self.mgr._message_tracker_reader = AsyncMock(
            return_value=[PctPosResponse(self.tt_addr, 250)]
        )
        await self.mgr.message_tracker()
        self.cover.set_drop_pct.awaited_once_with(self.tt_addr, 0.25)

    async def test2(self):
        self.mgr._message_tracker_reader = AsyncMock(
            return_value=[PctAckResponse(self.tt_addr, 500)]
        )
        await self.mgr.message_tracker()
        self.cover.set_target_drop_pct_hint.awaited_once_with(self.tt_addr, 0.5)