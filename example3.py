import argparse
import asyncio
import logging
from nicett6.cover import Cover, wait_for_motion_to_complete
from nicett6.cover_manager import CoverManager
from nicett6.ttbus_device import TTBusDeviceAddress

_LOGGER = logging.getLogger(__name__)


async def log_cover_state(cover):
    try:
        while cover.is_moving:
            _LOGGER.info(
                f"drop: {cover.drop}; "
                f"is_opening: {cover.is_opening}; "
                f"is_closing: {cover.is_closing}; "
            )
            await asyncio.sleep(1.0)
    except asyncio.CancelledError:
        pass


async def example(serial_port):
    tt_addr = TTBusDeviceAddress(0x02, 0x04)
    max_drop = 2.0
    async with CoverManager(serial_port) as mgr:
        tt6_cover = await mgr.add_cover(tt_addr, Cover("Cover", max_drop))

        message_tracker_task = asyncio.create_task(mgr.message_tracker())
        logger_task = asyncio.create_task(log_cover_state(tt6_cover.cover))

        await tt6_cover.send_drop_pct_command(0.9)
        await wait_for_motion_to_complete([tt6_cover.cover])

        await tt6_cover.send_close_command()
        await wait_for_motion_to_complete([tt6_cover.cover])

        logger_task.cancel()
        await logger_task

    await message_tracker_task


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s",
        "--serial_port",
        type=str,
        default="socket://localhost:50200",
        help="serial port",
    )
    args = parser.parse_args()
    asyncio.run(example(args.serial_port))
