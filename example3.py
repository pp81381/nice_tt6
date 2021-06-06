import argparse
import asyncio
import logging
from nice_tt6.cover_manager import open_cover_manager
from nice_tt6.ttbus_device import TTBusDeviceAddress

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
    async with open_cover_manager(tt_addr, max_drop, serial_port) as mgr:
        message_tracker_task = asyncio.create_task(mgr.message_tracker())
        logger_task = asyncio.create_task(log_cover_state(mgr.cover))

        await mgr.send_drop_pct_command(0.9)
        await mgr.wait_for_motion_to_complete()

        await mgr.send_close_command()
        await mgr.wait_for_motion_to_complete()

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