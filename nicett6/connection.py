import logging
from contextlib import asynccontextmanager
from typing import Optional, TypeAlias

from serial import PARITY_NONE, STOPBITS_ONE  # type: ignore

from nicett6.decode import Decode, ResponseMessageType
from nicett6.encode import Encode
from nicett6.multiplexer import (
    MultiplexerReader,
    MultiplexerSerialConnection,
    MultiplexerWriter,
)
from nicett6.ttbus_device import TTBusDeviceAddress
from nicett6.utils import async_get_platform_serial_port

_LOGGER = logging.getLogger(__name__)

ResponseMessageConnectionType: TypeAlias = MultiplexerSerialConnection[
    ResponseMessageType
]
ResponseMessageReaderType: TypeAlias = MultiplexerReader[ResponseMessageType]
ResponseMessageWriterType: TypeAlias = MultiplexerWriter[ResponseMessageType]


class TT6Reader(ResponseMessageReaderType):
    pass


class TT6Writer(ResponseMessageWriterType):
    def __init__(self, conn: ResponseMessageConnectionType) -> None:
        super().__init__(conn)

    async def send_web_on(self) -> None:
        _LOGGER.debug(f"send_web_on")
        await self.write(Encode.web_on())

    async def send_web_off(self) -> None:
        _LOGGER.debug(f"send_web_off")
        await self.write(Encode.web_off())

    async def send_simple_command(
        self, tt_addr: TTBusDeviceAddress, cmd_name: str
    ) -> None:
        _LOGGER.debug(f"send_simple_command {cmd_name} to {tt_addr}")
        await self.write(Encode.simple_command(tt_addr, cmd_name))

    async def send_hex_move_command(
        self, tt_addr: TTBusDeviceAddress, hex_pos: int
    ) -> None:
        _LOGGER.debug(f"send_hex_move_command {hex_pos} to {tt_addr}")
        await self.write(Encode.simple_command_with_data(tt_addr, "MOVE_POS", hex_pos))

    async def send_web_move_command(
        self, tt_addr: TTBusDeviceAddress, pos: int
    ) -> None:
        _LOGGER.debug(f"send_web_move_command {pos} to {tt_addr}")
        await self.write(Encode.web_move_command(tt_addr, pos))

    async def send_web_pos_request(self, tt_addr: TTBusDeviceAddress) -> None:
        _LOGGER.debug(f"send_web_pos_request to {tt_addr}")
        await self.write(Encode.web_pos_request(tt_addr))


class TT6Connection(ResponseMessageConnectionType):
    pass


async def open(serial_port: Optional[str] = None) -> TT6Connection:
    if serial_port is None:
        serial_port = await async_get_platform_serial_port()
    conn = TT6Connection(
        Decode.decode_line_bytes,
        Decode.EOL,
        TT6Reader,
        TT6Writer,
        0.05,
        url=serial_port,
        baudrate=19200,
        timeout=None,
        parity=PARITY_NONE,
        stopbits=STOPBITS_ONE,
    )
    await conn.connect()
    return conn


@asynccontextmanager
async def open_connection(serial_port=None):
    conn = await open(serial_port)
    try:
        yield conn
    finally:
        conn.close()
