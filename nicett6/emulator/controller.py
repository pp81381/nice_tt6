import asyncio
from contextlib import contextmanager, ExitStack
import logging
from nicett6.emulator.cover_emulator import TT6CoverEmulator
from nicett6.emulator.line_handler import LineHandler
from nicett6.utils import AsyncObserver

_LOGGER = logging.getLogger(__name__)

SEND_EOL = b"\r\n"
RCV_EOL = b"\r"


@contextmanager
def make_tt6controller(web_on, devices):
    controller = TT6Controller(web_on)
    with ExitStack() as stack:
        for device in devices:
            controller.register_device(device)
            stack.callback(controller.deregister_device, device.tt_addr)
        yield controller


class DuplicateDeviceError(Exception):
    pass


class WriterWrapper:
    def __init__(self, writer):
        self.writer = writer
        self.ok = True

    async def write_msg(self, msg: str):
        if self.ok:
            try:
                self.writer.write(msg.encode("utf-8") + SEND_EOL)
                await self.writer.drain()
            except ConnectionResetError:
                self.ok = False
                _LOGGER.warning("Caught ConnectionResetError.  Connection marked bad.")

        if not self.ok:
            _LOGGER.warning(f"Message could not be written to defunkt client: {msg!r}")


async def read_line_bytes(reader):
    try:
        line_bytes = await reader.readuntil(RCV_EOL)
    except asyncio.IncompleteReadError as err:
        if len(err.partial) > 0 and err.partial != b"\n":
            raise
        line_bytes = b""
    return line_bytes


class TT6Controller(AsyncObserver):
    def __init__(self, web_on):
        super().__init__()
        self.web_on = web_on
        self.devices = {}
        self.writers = set()
        self._server = None

    def register_device(self, device: TT6CoverEmulator):
        if device.tt_addr in self.devices:
            raise DuplicateDeviceError()
        self.devices[device.tt_addr] = device
        device.attach(self)
        _LOGGER.info(f"registered device {device.tt_addr}")

    def deregister_device(self, tt_addr):
        device = self.devices[tt_addr]
        device.detach(self)
        del self.devices[tt_addr]
        _LOGGER.info(f"deregistered device {tt_addr}")

    def lookup_device(self, tt_addr):
        return self.devices[tt_addr]

    async def run_server(self, port):
        async with await asyncio.start_server(
            self.handle_messages, port=port
        ) as self._server:
            for s in self._server.sockets:
                logging.info("Serving on {}".format(s.getsockname()))
            try:
                await self._server.serve_forever()
            except asyncio.CancelledError:
                logging.info("Server stopped")

    def stop_server(self):
        if self._server is not None and self._server.is_serving():
            self._server.close()

    @contextmanager
    def wrap_writer(self, writer):
        _LOGGER.info("Connection opened")
        wrapped_writer = WriterWrapper(writer)
        self.writers.add(wrapped_writer)
        try:
            yield wrapped_writer
        finally:
            self.writers.remove(wrapped_writer)
            writer.close()
            _LOGGER.info("Connection closed")

    async def handle_messages(self, reader, writer):
        with self.wrap_writer(writer) as wrapped_writer:
            line_handler = LineHandler(wrapped_writer, self)
            listener_task = asyncio.create_task(read_line_bytes(reader))
            pending = {listener_task}
            while pending:
                done, pending = await asyncio.wait(
                    pending, return_when=asyncio.FIRST_COMPLETED
                )
                for d in done:
                    if listener_task is not None and d is listener_task:
                        line_bytes = await d
                        if not line_bytes:
                            listener_task = None
                        else:
                            listener_task = asyncio.create_task(read_line_bytes(reader))
                            line_handler_task = asyncio.create_task(
                                line_handler.handle_line(line_bytes)
                            )
                            pending.add(listener_task)
                            pending.add(line_handler_task)
                    else:
                        await d

    async def write_all_wrapped_writers(self, msg):
        for wrapped_writer in self.writers:
            await wrapped_writer.write_msg(msg)

    async def update(self, device):
        if self.web_on:
            await self.write_all_wrapped_writers(LineHandler.fmt_pos_msg(device))
