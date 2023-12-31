import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Awaitable, Callable, List, Optional, TypeVar
from weakref import WeakSet

from serial_asyncio_fast import create_serial_connection  # type: ignore[import-untyped]

from nicett6.buffer import MessageBuffer

_LOGGER = logging.getLogger(__name__)

T = TypeVar("T")


class MultiplexerReaderStopSentinel:
    pass


class MultiplexerReader(AsyncIterator[T]):
    """Generic class for Readers"""

    def __init__(self, decoder: Callable[[bytes], T]) -> None:
        self.queue: asyncio.Queue[T | MultiplexerReaderStopSentinel] = asyncio.Queue()
        self.is_stopped: bool = False
        self.is_iterated: bool = False
        self.decoder = decoder

    def message_received(self, msg: bytes) -> None:
        if not self.is_stopped:
            decoded_msg = self.decode(msg)
            self.queue.put_nowait(decoded_msg)

    def decode(self, data: bytes) -> T:
        return self.decoder(data)

    def connection_lost(self, exc: Exception | None):
        if not self.is_stopped:
            self.stop()

    def stop(self) -> None:
        if not self.is_stopped:
            self.is_stopped = True
            self.queue.put_nowait(MultiplexerReaderStopSentinel())

    def __aiter__(self) -> AsyncIterator[T]:
        return self

    async def __anext__(self) -> T:
        if self.is_iterated:
            raise RuntimeError("MultiplexerReader cannot be iterated twice")
        item = await self.queue.get()
        if isinstance(item, MultiplexerReaderStopSentinel):
            self.is_iterated = True
            raise StopAsyncIteration
        return item


class MultiplexerWriter:
    """Base class for Writers"""

    def __init__(self, conn: "MultiplexerSerialConnection") -> None:
        self.conn = conn
        self.send_lock = asyncio.Lock()

    async def write(self, msg: bytes) -> None:
        assert self.conn.is_open
        async with self.send_lock:
            _LOGGER.debug(f"Writing message {msg!r}")
            self.conn.transport.write(msg)
            await asyncio.sleep(self.conn.post_write_delay)

    async def process_request(self, coro: Awaitable[None], time_window: float = 1.0):
        """
        Send a command and collect the response messages that arrive in time_window

        Usage:
             coro = writer.write("DO SOMETHING")
             messages = await writer.process_request(coro)

        Note that there could be unrelated messages received if web commands are on
        or if another command has just been submitted
        """
        reader: MultiplexerReader = self.conn.add_reader()
        await coro
        await asyncio.sleep(time_window)
        self.conn.remove_reader(reader)
        return [msg async for msg in reader]


class MultiplexerProtocol(asyncio.Protocol):
    def __init__(self, eol: bytes) -> None:
        self.readers: WeakSet[MultiplexerReader] = WeakSet()
        self.buf: MessageBuffer = MessageBuffer(eol)

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        _LOGGER.info("Connection made")

    def data_received(self, chunk: bytes) -> None:
        messages: List[bytes] = self.buf.append_chunk(chunk)
        for msg in messages:
            _LOGGER.debug(f"data_received: %r", msg)
            for r in self.readers:
                r.message_received(msg)

    def connection_lost(self, exc: Exception | None) -> None:
        if self.buf.buf != b"":
            _LOGGER.warn(
                "Connection lost with partial message in buffer: %r", self.buf.buf
            )
        else:
            _LOGGER.info("Connection lost")
        for r in self.readers:
            r.connection_lost(exc)


class MultiplexerSerialConnection:
    def __init__(
        self,
        reader_factory: Callable[[], MultiplexerReader],
        writer_factory: Callable[["MultiplexerSerialConnection"], MultiplexerWriter],
        post_write_delay: float = 0,
    ) -> None:
        self.reader_factory = reader_factory
        self.writer_factory = writer_factory
        self.post_write_delay = post_write_delay
        self._transport: Optional[asyncio.Transport] = None
        self._protocol: Optional[MultiplexerProtocol] = None

    @property
    def is_open(self) -> bool:
        return self._transport is not None and self._protocol is not None

    @property
    def transport(self) -> asyncio.Transport:
        if self._transport is None:
            raise RuntimeError("connection is not open")
        return self._transport

    @property
    def protocol(self) -> MultiplexerProtocol:
        if self._protocol is None:
            raise RuntimeError("connection is not open")
        return self._protocol

    async def open(self, eol, **kwargs) -> None:
        assert not self.is_open
        loop = asyncio.get_running_loop()
        self._transport, protocol = await create_serial_connection(
            loop,
            lambda: MultiplexerProtocol(eol),
            **kwargs,
        )
        assert isinstance(protocol, MultiplexerProtocol)
        self._protocol = protocol

    def add_reader(self) -> MultiplexerReader:
        if self._protocol is None:
            raise RuntimeError("connection is not open")
        reader = self.reader_factory()
        self._protocol.readers.add(reader)
        return reader

    def remove_reader(self, reader: MultiplexerReader) -> None:
        if self._protocol is None:
            raise RuntimeError("connection is not open")
        self._protocol.readers.remove(reader)
        reader.stop()

    def get_writer(self) -> MultiplexerWriter:
        return self.writer_factory(self)

    def close(self) -> None:
        if self._transport is not None:
            self._transport.close()
            self._transport = None
            self._protocol = None
