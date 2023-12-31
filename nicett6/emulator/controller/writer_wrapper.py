import asyncio
import logging

from nicett6.consts import SEND_EOL

_LOGGER = logging.getLogger(__name__)


class WriterWrapper:
    def __init__(self, writer: asyncio.StreamWriter) -> None:
        self.writer = writer
        self.ok: bool = True

    async def write_msg(self, msg: str) -> None:
        if self.ok:
            try:
                self.writer.write(msg.encode("utf-8") + SEND_EOL)
                await self.writer.drain()
            except ConnectionResetError:
                self.ok = False
                _LOGGER.warning("Caught ConnectionResetError.  Connection marked bad.")

        if not self.ok:
            _LOGGER.warning(f"Message could not be written to defunkt client: {msg!r}")
