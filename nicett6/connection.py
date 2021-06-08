from contextlib import asynccontextmanager
import logging
from nicett6.decode import Decode
from nicett6.encode import Encode
from nicett6.utils import async_get_platform_serial_port
from nicett6.multiplexer import (
    MultiplexerReader,
    MultiplexerSerialConnection,
    MultiplexerWriter,
)
from serial import PARITY_NONE, STOPBITS_ONE


_LOGGER = logging.getLogger(__name__)


@asynccontextmanager
async def open_connection(serial_port=None):
    conn = TT6Connection()
    try:
        await conn.open(serial_port)
        yield conn
    finally:
        conn.close()


class TT6Connection(MultiplexerSerialConnection):
    def __init__(self):
        super().__init__(TT6Reader, TT6Writer, 0.05)

    async def open(self, serial_port=None):
        if serial_port is None:
            serial_port = await async_get_platform_serial_port()
        await super().open(
            Decode.EOL,
            url=serial_port,
            baudrate=19200,
            timeout=None,
            parity=PARITY_NONE,
            stopbits=STOPBITS_ONE,
        )

    def close(self):
        super().close()


class TT6Reader(MultiplexerReader):
    def decode(self, data):
        return Decode.decode_line_bytes(data)


class TT6Writer(MultiplexerWriter):
    async def send_web_on(self):
        _LOGGER.debug(f"send_web_on")
        await self.write(Encode.web_on())

    async def send_web_off(self):
        _LOGGER.debug(f"send_web_off")
        await self.write(Encode.web_off())

    async def send_simple_command(self, tt_addr, cmd_code):
        _LOGGER.debug(f"send_simple_command {cmd_code} to {tt_addr}")
        await self.write(Encode.simple_command(tt_addr, cmd_code))

    async def send_hex_move_command(self, tt_addr, hex_pos):
        _LOGGER.debug(f"send_hex_move_command {hex_pos} to {tt_addr}")
        await self.write(Encode.simple_command_with_data(tt_addr, "MOVE_POS", hex_pos))

    async def send_web_move_command(self, tt_addr, pct_pos):
        _LOGGER.debug(f"send_web_move_command {pct_pos} to {tt_addr}")
        await self.write(Encode.web_move_command(tt_addr, pct_pos))

    async def send_web_pos_request(self, tt_addr):
        _LOGGER.debug(f"send_web_pos_request to {tt_addr}")
        await self.write(Encode.web_pos_request(tt_addr))
