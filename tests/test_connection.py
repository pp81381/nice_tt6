from nicett6.decode import AckResponse
from nicett6.connection import open_connection
from nicett6.ttbus_device import TTBusDeviceAddress
from unittest import IsolatedAsyncioTestCase
from unittest.mock import call, MagicMock, patch

RCV_EOL = b"\r"


def mock_csc_return_value(*args, **kwargs):
    return MagicMock(), args[1]()


class TestReaderAndWriter(IsolatedAsyncioTestCase):
    def setUp(self):
        patcher = patch(
            "nicett6.multiplexer.create_serial_connection",
            side_effect=mock_csc_return_value,
        )
        self.addCleanup(patcher.stop)
        self.mock_csc = patcher.start()

    async def test_reader(self):
        async with open_connection() as conn:
            reader = conn.add_reader()
            conn.protocol.data_received(b"RSP 3 4 11" + RCV_EOL)
            conn.protocol.connection_lost(None)
            messages = [msg async for msg in reader]
            self.assertEqual(len(messages), 1)
            res = messages[0]
            self.assertIsInstance(res, AckResponse)
            self.assertEqual(res.tt_addr, TTBusDeviceAddress(0x03, 0x04))
            self.assertEqual(res.cmd_code, 0x11)

    async def test_writer(self):
        async with open_connection() as conn:
            writer = conn.get_writer()
            await writer.send_web_on()
            conn.transport.write.assert_called_once_with(b"WEB_ON" + RCV_EOL)
