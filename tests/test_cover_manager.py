from logging import WARNING
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from nicett6.cover import Cover
from nicett6.cover_manager import CoverManager
from nicett6.decode import PctPosResponse
from nicett6.ttbus_device import TTBusDeviceAddress
from tests import make_mock_conn

TEST_READER_POS_RESPONSE = [
    PctPosResponse(TTBusDeviceAddress(0x02, 0x04), 110),
    PctPosResponse(TTBusDeviceAddress(0x03, 0x04), 539),  # Address 0x03 Ignored
]


class TestCoverManagerOpen(IsolatedAsyncioTestCase):
    async def test1(self):
        conn = make_mock_conn(TEST_READER_POS_RESPONSE)
        with patch(
            "nicett6.cover_manager.open_tt6",
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
            "nicett6.cover_manager.open_tt6",
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
        with self.assertLogs("nicett6.cover_manager", level=WARNING) as cm:
            await self.mgr.message_tracker()
        self.assertAlmostEqual(self.cover.drop, 1.78)
        self.assertEqual(
            cm.output,
            [
                "WARNING:nicett6.cover_manager:response message addressed to unknown device: PctPosResponse(TTBusDeviceAddress(0x03, 0x04), 539)",
            ],
        )


class TestCoverManagerContextManager(IsolatedAsyncioTestCase):
    def setUp(self):
        self.conn = make_mock_conn(TEST_READER_POS_RESPONSE)
        patcher = patch(
            "nicett6.cover_manager.open_tt6",
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
            writer.send_simple_command.assert_awaited_with(self.tt_addr, "MOVE_DOWN")
            self.conn.close.assert_not_called()
        self.conn.close.assert_called_once()


class TestCoverManagerMessageTracker(IsolatedAsyncioTestCase):
    async def test1(self):
        tt_addr = TTBusDeviceAddress(0x02, 0x04)
        msg = PctPosResponse(tt_addr, 250)
        mgr = CoverManager("DUMMY_SERIAL_PORT")
        mgr._message_tracker_reader = MagicMock()
        mgr._message_tracker_reader.__aiter__.return_value = [msg]
        mgr._writer = AsyncMock()
        with patch("nicett6.cover_manager.TT6Cover", new=AsyncMock) as tt6_cover:
            tt6_cover.send_pos_request = AsyncMock()
            tt6_cover.handle_response_message = AsyncMock()
            mock_cover = AsyncMock()
            await mgr.add_cover(tt_addr, mock_cover)
            await mgr.message_tracker()
            tt6_cover.handle_response_message.assert_awaited_once_with(msg)
