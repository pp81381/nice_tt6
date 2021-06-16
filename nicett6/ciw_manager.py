from nicett6.cover_manager import CoverManager
from nicett6.cover import TT6Cover
from nicett6.ttbus_device import TTBusDeviceAddress
from nicett6.ciw_helper import CIWHelper, ImageDef


class CIWManager:
    def __init__(
        self,
        serial_port: str,
        screen_tt_addr: TTBusDeviceAddress,
        mask_tt_addr: TTBusDeviceAddress,
        screen_max_drop: float,
        mask_max_drop: float,
        image_def: ImageDef,
    ):
        self._screen_tt_addr = screen_tt_addr
        self._mask_tt_addr = mask_tt_addr
        self.screen_tt6_cover: TT6Cover = None
        self.mask_tt6_cover: TT6Cover = None
        self._mgr = CoverManager(serial_port)
        self.helper = CIWHelper(screen_max_drop, mask_max_drop, image_def)

    async def __aenter__(self):
        await self.open()
        return self

    async def __aexit__(self, exception_type, exception_value, traceback):
        self.close()

    async def open(self):
        await self._mgr.open()
        self.screen_tt6_cover = await self._mgr.add_cover(
            self._screen_tt_addr,
            self.helper.screen,
        )
        self.mask_tt6_cover = await self._mgr.add_cover(
            self._mask_tt_addr,
            self.helper.mask,
        )

    def close(self):
        self._mgr.close()
        self.screen_tt6_cover = None
        self.mask_tt6_cover = None

    async def message_tracker(self):
        await self._mgr.message_tracker()

    async def wait_for_motion_to_complete(self):
        await self._mgr.wait_for_motion_to_complete()

    async def send_pos_request(self):
        await self.screen_tt6_cover.send_pos_request()
        await self.mask_tt6_cover.send_pos_request()

    async def send_close_command(self):
        await self.screen_tt6_cover.send_close_command()
        await self.mask_tt6_cover.send_close_command()

    async def send_open_command(self):
        await self.screen_tt6_cover.send_open_command()
        await self.mask_tt6_cover.send_open_command()

    async def send_stop_command(self):
        await self.screen_tt6_cover.send_stop_command()
        await self.mask_tt6_cover.send_stop_command()

    async def send_set_aspect_ratio(self, *args, **kwargs):
        new_drops = self.helper.calculate_new_drops(*args, **kwargs)
        if new_drops is not None:
            await self.screen_tt6_cover.send_drop_pct_command(new_drops[0])
            await self.mask_tt6_cover.send_drop_pct_command(new_drops[1])
