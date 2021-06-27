from nicett6.cover import TT6Cover
from nicett6.ciw_helper import CIWHelper, ImageDef


class CIWManager:
    def __init__(
        self,
        screen_tt6_cover: TT6Cover,
        mask_tt6_cover: TT6Cover,
        image_def: ImageDef,
    ):
        self.screen_tt6_cover: TT6Cover = screen_tt6_cover
        self.mask_tt6_cover: TT6Cover = mask_tt6_cover
        self.helper = CIWHelper(screen_tt6_cover.cover, mask_tt6_cover.cover, image_def)

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
