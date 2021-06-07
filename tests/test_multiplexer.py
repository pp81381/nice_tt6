import asyncio
from nicett6.multiplexer import (
    MultiplexerProtocol,
    MultiplexerReader,
    MultiplexerSerialConnection,
    MultiplexerWriter,
)
from unittest import IsolatedAsyncioTestCase
from unittest.mock import call, MagicMock, patch

RCV_EOL = b"\r"
SEND_EOL = b"\r"


def mock_csc_return_value(*args):
    """returns mock transport and the MultiPlexerProtocol in args[1]"""
    return MagicMock(), args[1]()


class TestConnection(IsolatedAsyncioTestCase):
    def setUp(self):
        patcher = patch(
            "nicett6.multiplexer.create_serial_connection",
            side_effect=mock_csc_return_value,
        )
        self.addCleanup(patcher.stop)
        self.mock_csc = patcher.start()

    async def test_conn(self):
        conn = MultiplexerSerialConnection(MultiplexerReader, MultiplexerWriter, 0.05)
        await conn.open(RCV_EOL)
        self.mock_csc.assert_called_once()
        self.assertTrue(conn.is_open)
        t = conn.transport
        self.assertIsInstance(t, MagicMock)
        p = conn.protocol
        self.assertIsInstance(p, MultiplexerProtocol)
        self.assertEqual(p.buf.eol, RCV_EOL)
        conn.close()
        self.assertFalse(conn.is_open)
        t.close.assert_called_once_with()


class TestReaderAndWriter(IsolatedAsyncioTestCase):

    DATA_RECEIVED = b"TEST MESSAGE 1" + RCV_EOL + b"TEST MESSAGE 2" + RCV_EOL
    EXPECTED_MESSAGES = [
        b"TEST MESSAGE 1" + RCV_EOL,
        b"TEST MESSAGE 2" + RCV_EOL,
    ]
    TEST_MESSAGE = b"TEST MESSAGE" + SEND_EOL

    def setUp(self):
        patcher = patch(
            "nicett6.multiplexer.create_serial_connection",
            side_effect=mock_csc_return_value,
        )
        self.addCleanup(patcher.stop)
        self.mock_csc = patcher.start()
        self.conn = MultiplexerSerialConnection(
            MultiplexerReader, MultiplexerWriter, 0.05
        )

    async def asyncSetUp(self) -> None:
        return await self.conn.open(RCV_EOL)

    def tearDown(self) -> None:
        self.conn.close()

    async def test_no_readers(self):
        reader = self.conn.add_reader()
        self.conn.protocol.data_received(self.DATA_RECEIVED)
        self.conn.protocol.connection_lost(None)

    async def test_one_reader(self):
        reader = self.conn.add_reader()
        self.conn.protocol.data_received(self.DATA_RECEIVED)
        self.conn.protocol.connection_lost(None)
        messages = [msg async for msg in reader]
        self.assertEqual(messages, self.EXPECTED_MESSAGES)

    async def test_one_reader_twice(self):
        reader = self.conn.add_reader()
        self.conn.protocol.data_received(self.DATA_RECEIVED)
        self.conn.protocol.connection_lost(None)
        messages = [msg async for msg in reader]
        self.assertEqual(messages, self.EXPECTED_MESSAGES)
        with self.assertRaises(RuntimeError):
            messages = [msg async for msg in reader]

    async def test_two_readers(self):
        readers = [self.conn.add_reader(), self.conn.add_reader()]
        self.conn.protocol.data_received(self.DATA_RECEIVED)
        self.conn.protocol.connection_lost(None)
        messages0 = [msg async for msg in readers[0]]
        self.assertEqual(messages0, self.EXPECTED_MESSAGES)
        messages1 = [msg async for msg in readers[1]]
        self.assertEqual(messages1, self.EXPECTED_MESSAGES)

    async def test_writer(self):
        writer = self.conn.get_writer()
        await writer.write(self.TEST_MESSAGE)
        self.conn.transport.write.assert_called_once_with(self.TEST_MESSAGE)

    async def test_multiple_writes(self):
        log = MagicMock()

        original_sleep = asyncio.sleep

        async def sleep_side_effect(delay):
            await original_sleep(  # If the lock isn't working then this will allow a message to be written
                0.2
            )
            log("sleep", delay)

        def write_side_effect(msg):
            log("write", msg)

        self.conn.transport.write.side_effect = write_side_effect

        writer = self.conn.get_writer()
        with patch("asyncio.sleep", side_effect=sleep_side_effect):
            await asyncio.wait(
                {
                    asyncio.create_task(writer.write(self.TEST_MESSAGE)),
                    asyncio.create_task(writer.write(self.TEST_MESSAGE)),
                    asyncio.create_task(writer.write(self.TEST_MESSAGE)),
                    asyncio.create_task(writer.write(self.TEST_MESSAGE)),
                    asyncio.create_task(writer.write(self.TEST_MESSAGE)),
                }
            )

        log.assert_has_calls(
            [
                call("write", self.TEST_MESSAGE),
                call("sleep", 0.05),
                call("write", self.TEST_MESSAGE),
                call("sleep", 0.05),
                call("write", self.TEST_MESSAGE),
                call("sleep", 0.05),
                call("write", self.TEST_MESSAGE),
                call("sleep", 0.05),
                call("write", self.TEST_MESSAGE),
            ]
        )

    async def test_process_request(self):
        dummy_request = b"DUMMY MESSAGE" + SEND_EOL
        data1 = b"RESPONSE" + RCV_EOL
        data2 = b"OTHER STUFF" + RCV_EOL
        data3 = b"MORE STUFF" + RCV_EOL
        writer = self.conn.get_writer()
        coro = writer.write(dummy_request)
        task = asyncio.create_task(writer.process_request(coro))
        await asyncio.sleep(0)  # Let the task create the reader
        self.conn.protocol.data_received(data1 + data2)
        await asyncio.sleep(0.1)
        self.conn.protocol.data_received(data3)
        messages = await task
        self.conn.transport.write.assert_called_once_with(dummy_request)
        self.assertEqual(messages, [data1, data2, data3])