import asyncio
import logging
from nicett6.connection import open_connection
from nicett6.ttbus_device import TTBusDeviceAddress
from nicett6.utils import run_coro_after_delay, parse_example_args

_LOGGER = logging.getLogger(__name__)


async def run_example_commands1(writer, screen_tt_addr, mask_tt_addr):
    await writer.send_web_on()
    await asyncio.sleep(0.5)
    await writer.send_simple_command(mask_tt_addr, "MOVE_DOWN")
    await asyncio.sleep(1.0)
    await writer.send_simple_command(screen_tt_addr, "READ_POS")
    await asyncio.sleep(3.0)
    await writer.send_simple_command(mask_tt_addr, "READ_POS")
    await writer.send_simple_command(mask_tt_addr, "MOVE_UP")
    await asyncio.sleep(5.0)
    _LOGGER.info("run_example_commands1 completed")


async def run_example_commands2(writer, screen_tt_addr, mask_tt_addr):
    await writer.send_web_on()
    await writer.send_web_pos_request(screen_tt_addr)
    await writer.send_hex_move_command(screen_tt_addr, 0xE0)
    await asyncio.sleep(5.0)
    await writer.send_simple_command(screen_tt_addr, "MOVE_UP")
    await asyncio.sleep(5.0)
    _LOGGER.info("run_example_commands2 completed")


async def run_example_commands3(writer, screen_tt_addr, mask_tt_addr):
    await writer.send_web_on()
    await writer.send_web_pos_request(screen_tt_addr)
    await writer.send_hex_move_command(screen_tt_addr, 0xE0)
    await asyncio.sleep(5.0)
    await writer.send_web_move_command(screen_tt_addr, 0.4)
    await asyncio.sleep(5.0)
    await writer.send_simple_command(screen_tt_addr, "MOVE_UP")
    await asyncio.sleep(15.0)
    await writer.send_web_pos_request(screen_tt_addr)
    await asyncio.sleep(0.5)
    _LOGGER.info("run_example_commands3 completed")


async def run_example_commands_screen_up(writer, screen_tt_addr, mask_tt_addr):
    await writer.send_web_on()
    await writer.send_simple_command(screen_tt_addr, "MOVE_UP")
    _LOGGER.info("run_example_commands_screen_up completed")


async def run_example_commands_screen_down(writer, screen_tt_addr, mask_tt_addr):
    await writer.send_web_on()
    await writer.send_simple_command(screen_tt_addr, "MOVE_DOWN")
    _LOGGER.info("run_example_commands_screen_down completed")


async def request_screen_position(writer, tt_addr):
    _LOGGER.info("requesting screen position")
    responses = await writer.process_request(
        writer.send_simple_command(tt_addr, "READ_POS"), 0.5
    )
    _LOGGER.info("screen position request responses: %r", responses)


async def read_sequences_simple(reader):
    _LOGGER.info("message reader started")
    async for msg in reader:
        _LOGGER.info(f"msg:{msg}")
    _LOGGER.info("message reader finished")


async def main(serial_port, run_example_commands):
    async with open_connection(serial_port) as conn:
        screen_tt_addr = TTBusDeviceAddress(0x02, 0x04)
        mask_tt_addr = TTBusDeviceAddress(0x03, 0x04)
        reader = conn.add_reader()
        reader_task = asyncio.create_task(read_sequences_simple(reader))
        writer = conn.get_writer()
        example_task = asyncio.create_task(
            run_example_commands(writer, screen_tt_addr, mask_tt_addr)
        )
        request_task = asyncio.create_task(
            run_coro_after_delay(request_screen_position(writer, screen_tt_addr))
        )
        await example_task
        await request_task
    await reader_task


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    examples = (
        ("ex1", run_example_commands1),
        ("ex2", run_example_commands2),
        ("ex3", run_example_commands3),
        ("up", run_example_commands_screen_up),
        ("down", run_example_commands_screen_down),
    )
    serial_port, example = parse_example_args(examples)
    asyncio.run(main(serial_port, example))