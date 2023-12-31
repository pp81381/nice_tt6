import asyncio
from typing import Iterable

from nicett6.consts import RCV_EOL
from nicett6.emulator.controller.device_manager import DeviceRegistry
from nicett6.emulator.controller.line_handler import LineHandler
from nicett6.emulator.controller.server_controller import ServerController
from nicett6.emulator.controller.web_pos_manager import WebPosManager
from nicett6.emulator.controller.writer_manager import WriterManager


async def read_line_bytes(reader):
    try:
        line_bytes = await reader.readuntil(RCV_EOL)
    except asyncio.IncompleteReadError as err:
        if len(err.partial) > 0 and err.partial != b"\n":
            raise
        line_bytes = b""
    return line_bytes


async def handle_messages(
    writer_manager: WriterManager,
    web_pos_manager: WebPosManager,
    device_registry: DeviceRegistry,
    server_controller: ServerController,
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
) -> None:
    with writer_manager.wrap_writer(writer) as wrapped_writer:
        line_handler = LineHandler(
            wrapped_writer,
            web_pos_manager,
            device_registry,
            server_controller,
        )
        listener_task: asyncio.Task = asyncio.create_task(read_line_bytes(reader))
        done: Iterable[asyncio.Task]
        pending: Iterable[asyncio.Task] = [listener_task]
        while pending:
            done, pending = await asyncio.wait(
                pending,
                return_when=asyncio.FIRST_COMPLETED,
            )
            for d in done:
                if d is listener_task:
                    line_bytes = await d
                    if not line_bytes:
                        break
                    listener_task = asyncio.create_task(read_line_bytes(reader))
                    line_handler_task = asyncio.create_task(
                        line_handler.handle_line(line_bytes)
                    )
                    pending.add(listener_task)
                    pending.add(line_handler_task)
                else:
                    await d
