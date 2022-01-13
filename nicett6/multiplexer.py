import asyncio
from nicett6.buffer import MessageBuffer
import logging
from serial_asyncio import create_serial_connection
import weakref

_LOGGER = logging.getLogger(__name__)


class MultiplexerReaderStopSentinel:
    pass


class MultiplexerReader:
    """ Base class for Readers """

    def __init__(self):
        self.queue = asyncio.Queue()
        self.is_stopped = False
        self.is_iterated = False

    def message_received(self, msg):
        if not self.is_stopped:
            decoded_msg = self.decode(msg)
            self.queue.put_nowait(decoded_msg)

    def decode(self, data):
        """ Override this method if needed """
        return data

    def connection_lost(self, exc):
        if not self.is_stopped:
            self.stop()

    def stop(self):
        if not self.is_stopped:
            self.is_stopped = True
            self.queue.put_nowait(MultiplexerReaderStopSentinel())

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.is_iterated:
            raise RuntimeError("MultiplexerReader cannot be iterated twice")
        item = await self.queue.get()
        if isinstance(item, MultiplexerReaderStopSentinel):
            self.is_iterated = True
            raise StopAsyncIteration
        return item


class MultiplexerWriter:
    """ Base class for Writers """

    def __init__(self, conn):
        self.conn = conn
        self.send_lock = asyncio.Lock()

    async def write(self, msg):
        assert self.conn.is_open
        async with self.send_lock:
            _LOGGER.debug(f"Writing message {msg}")
            self.conn.transport.write(msg)
            await asyncio.sleep(self.conn.post_write_delay)

    async def process_request(self, coro, time_window=1.0):
        """
        Send a command and collect the response messages that arrive in time_window

        Usage:
             coro = writer.write("DO SOMETHING")
             messages = await writer.process_request(coro)

        Note that there could be unrelated messages received if web commands are on
        or if another command has just been submitted
        """
        reader = self.conn.add_reader()
        await coro
        await asyncio.sleep(time_window)
        self.conn.remove_reader(reader)
        return [msg async for msg in reader]


class MultiplexerProtocol(asyncio.Protocol):
    def __init__(self, eol):
        self.readers = weakref.WeakSet()
        self.buf = MessageBuffer(eol)

    def connection_made(self, transport):
        _LOGGER.info("Connection made")

    def data_received(self, chunk):
        messages = self.buf.append_chunk(chunk)
        for msg in messages:
            _LOGGER.debug(f"data_received: %r", msg)
            for r in self.readers:
                r.message_received(msg)

    def connection_lost(self, exc):
        if self.buf.buf != b"":
            _LOGGER.warn(
                "Connection lost with partial message in buffer: %r", self.buf.buf
            )
        else:
            _LOGGER.info("Connection lost")
        for r in self.readers:
            r.connection_lost(exc)


class MultiplexerSerialConnection:
    def __init__(self, reader_factory, writer_factory, post_write_delay=0):
        self.reader_factory = reader_factory
        self.writer_factory = writer_factory
        self.post_write_delay = post_write_delay
        self.transport = None
        self.protocol = None
        self.is_open = False

    async def open(self, eol, **kwargs):
        assert not self.is_open
        loop = asyncio.get_event_loop()
        self.transport, self.protocol = await create_serial_connection(
            loop,
            lambda: MultiplexerProtocol(eol),
            **kwargs,
        )
        self.is_open = True

    def add_reader(self):
        assert self.is_open
        reader = self.reader_factory()
        self.protocol.readers.add(reader)
        return reader

    def remove_reader(self, reader):
        assert self.is_open
        self.protocol.readers.remove(reader)
        reader.stop()

    def get_writer(self):
        return self.writer_factory(self)

    def close(self):
        if self.is_open:
            self.transport.close()
            self.transport = None
            self.protocol = None
            self.is_open = False
