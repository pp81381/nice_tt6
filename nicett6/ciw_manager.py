from dataclasses import dataclass

from nicett6.ciw_helper import CIWHelper
from nicett6.cover import wait_for_motion_to_complete
from nicett6.image_def import ImageDef
from nicett6.tt6_cover import TT6Cover


@dataclass
class CIWManager:
    screen_tt6_cover: TT6Cover
    mask_tt6_cover: TT6Cover
    image_def: ImageDef

    def get_helper(self) -> CIWHelper:
        return CIWHelper(
            self.screen_tt6_cover.cover,
            self.mask_tt6_cover.cover,
            self.image_def,
        )

    async def send_pos_request(self) -> None:
        await self.screen_tt6_cover.send_pos_request()
        await self.mask_tt6_cover.send_pos_request()

    async def send_simple_command(self, cmd_name: str) -> None:
        await self.screen_tt6_cover.send_simple_command(cmd_name)
        await self.mask_tt6_cover.send_simple_command(cmd_name)

    async def wait_for_motion_to_complete(self):
        return await wait_for_motion_to_complete(
            [
                self.screen_tt6_cover.cover,
                self.mask_tt6_cover.cover,
            ]
        )
