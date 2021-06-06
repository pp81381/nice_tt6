import asyncio
from contextlib import asynccontextmanager
import logging
from nice_tt6.cover import TT6CoverWriter
from nice_tt6.ttbus_device import TTBusDeviceAddress
from nice_tt6.ciw_helper import CIWHelper, ImageDef
from nice_tt6.connection import TT6Reader, TT6Writer, open_connection
from nice_tt6.decode import PctPosResponse
from nice_tt6.multiplexer import MultiplexerSerialConnection


_LOGGER = logging.getLogger(__name__)


@asynccontextmanager
async def open_ciw_manager(
    screen_tt_addr,
    mask_tt_addr,
    screen_max_drop,
    mask_max_drop,
    image_def,
    serial_port=None,
):
    async with open_connection(serial_port) as conn:
        mgr = CIWManager(
            conn,
            screen_tt_addr,
            mask_tt_addr,
            screen_max_drop,
            mask_max_drop,
            image_def,
        )
        await mgr._start()
        yield mgr


class CIWManager:

    POLLING_INTERVAL = 0.2

    def __init__(
        self,
        conn: MultiplexerSerialConnection,
        screen_tt_addr: TTBusDeviceAddress,
        mask_tt_addr: TTBusDeviceAddress,
        screen_max_drop: float,
        mask_max_drop: float,
        image_def: ImageDef,
    ):
        self._conn = conn
        self._screen_tt_addr = screen_tt_addr
        self._mask_tt_addr = mask_tt_addr
        self.helper = CIWHelper(screen_max_drop, mask_max_drop, image_def)
        # NOTE: message_tracker_reader is created here rather than in message_tracker
        # to ensure that all messages from this moment on are captured
        # in particular: the initial position messages generated by _start()
        self._message_tracker_reader: TT6Reader = self._conn.add_reader()
        self._writer: TT6Writer = self._conn.get_writer()
        self._screen_writer = TT6CoverWriter(
            screen_tt_addr, self.helper.screen, self._writer
        )
        self._mask_writer = TT6CoverWriter(mask_tt_addr, self.helper.mask, self._writer)

    async def _start(self):
        await self._writer.send_web_on()
        await self.send_pos_request()

    def _get_target_cover(self, tt_addr):
        if tt_addr == self._screen_tt_addr:
            return self.helper.screen
        elif tt_addr == self._mask_tt_addr:
            return self.helper.mask
        else:
            return None

    async def message_tracker(self):
        """Listen to PctPosResponse messages and keep screen and mask up to date"""
        _LOGGER.debug("pos message tracker started")
        async for msg in self._message_tracker_reader:
            _LOGGER.debug(f"msg:{msg}")
            if isinstance(msg, PctPosResponse):
                target_cover = self._get_target_cover(msg.tt_addr)
                if target_cover is not None:
                    target_cover.drop_pct = msg.pct_pos / 1000.0
                    _LOGGER.debug(
                        f"aspect_ratio: {self.helper.aspect_ratio}; "
                        f"screen_drop: {self.helper.screen.drop}; "
                        f"mask_drop: {self.helper.mask.drop}"
                    )
        _LOGGER.debug("pos message tracker finished")

    async def wait_for_motion_to_complete(self):
        """
        Poll for motion to complete

        Make sure that Cover.moving() is called when movement
        is initiated for this method to work reliably (see CoverWriter)
        """
        while True:
            await asyncio.sleep(self.POLLING_INTERVAL)
            if not self.helper.screen.is_moving and not self.helper.mask.is_moving:
                return

    async def send_pos_request(self):
        await self._screen_writer.send_pos_request()
        await self._mask_writer.send_pos_request()

    async def send_close_command(self):
        await self._screen_writer.send_close_command()
        await self._mask_writer.send_close_command()

    async def send_open_command(self):
        await self._screen_writer.send_open_command()
        await self._mask_writer.send_open_command()

    async def send_stop_command(self):
        await self._screen_writer.send_stop_command()
        await self._mask_writer.send_stop_command()

    async def send_set_aspect_ratio(self, *args, **kwargs):
        new_drops = self.helper.calculate_new_drops(*args, **kwargs)
        if new_drops is not None:
            await self._screen_writer.send_drop_pct_command(new_drops[0])
            await self._mask_writer.send_drop_pct_command(new_drops[1])
