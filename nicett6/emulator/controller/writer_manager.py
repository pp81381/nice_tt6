import asyncio
import logging
from contextlib import contextmanager
from typing import Generator, Set

from nicett6.emulator.controller.writer_wrapper import WriterWrapper

_LOGGER = logging.getLogger(__name__)


class WriterManager:
    """
    Manage the writers of all connections

    Outbound messages from the controller are sent to all writers
    This class keeps track of all of the writers and provides a write_all method
    """

    def __init__(self) -> None:
        self.writers: Set[WriterWrapper] = set()

    @contextmanager
    def wrap_writer(
        self,
        writer: asyncio.StreamWriter,
    ) -> Generator[WriterWrapper, None, None]:
        _LOGGER.info("Connection opened")
        wrapped_writer = WriterWrapper(writer)
        self.writers.add(wrapped_writer)
        try:
            yield wrapped_writer
        finally:
            self.writers.remove(wrapped_writer)
            writer.close()
            _LOGGER.info("Connection closed")

    async def write_all(self, msg: str) -> None:
        for wrapped_writer in self.writers:
            await wrapped_writer.write_msg(msg)
