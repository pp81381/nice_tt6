import asyncio
import logging
from contextlib import ExitStack, contextmanager

from nicett6.emulator.controller.device_manager import DeviceManager
from nicett6.emulator.controller.handle_messages import handle_messages
from nicett6.emulator.controller.server_controller import ServerController
from nicett6.emulator.controller.web_pos_manager import WebPosManager
from nicett6.emulator.controller.writer_manager import WriterManager

_LOGGER = logging.getLogger(__name__)


@contextmanager
def make_tt6controller(web_on, devices):
    controller = TT6Controller(web_on)
    with ExitStack() as stack:
        for device in devices:
            controller.device_manager.register_device(device)
            stack.callback(controller.device_manager.deregister_device, device.tt_addr)
        yield controller


class TT6Controller(ServerController):
    def __init__(self, web_on: bool) -> None:
        self.writer_manager = WriterManager()
        self.web_pos_manager = WebPosManager(self.writer_manager, web_on)
        self.device_manager: DeviceManager = DeviceManager(self.web_pos_manager)
        self._server: asyncio.Server | None = None

    async def handle_messages(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        await handle_messages(
            self.writer_manager,
            self.web_pos_manager,
            self.device_manager,
            self,
            reader,
            writer,
        )

    async def run_server(self, port: int | str | None) -> None:
        async with await asyncio.start_server(
            self.handle_messages,
            port=port,
        ) as self._server:
            for s in self._server.sockets:
                _LOGGER.info("Serving on {}".format(s.getsockname()))
            try:
                await self._server.serve_forever()
            except asyncio.CancelledError:
                _LOGGER.info("Server stopped")

    async def stop_server(self):
        if self._server is not None and self._server.is_serving():
            self._server.close()
            await self._server.wait_closed()
