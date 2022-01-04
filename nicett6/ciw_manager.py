from enum import Enum
import logging

from nicett6.cover import Cover, TT6Cover, wait_for_motion_to_complete
from nicett6.ciw_helper import CIWHelper, ImageDef
from nicett6.utils import MAX_ASPECT_RATIO

_LOGGER = logging.getLogger(__name__)


class CIWAspectRatioMode(Enum):
    FIXED_TOP = 1
    FIXED_MIDDLE = 2
    FIXED_BOTTOM = 3


class CIWManager:
    def __init__(
        self,
        screen_tt6_cover: TT6Cover,
        mask_tt6_cover: TT6Cover,
        image_def: ImageDef,
    ):
        self.screen_tt6_cover: TT6Cover = screen_tt6_cover
        self.mask_tt6_cover: TT6Cover = mask_tt6_cover
        self.image_def = image_def

    def get_helper(self):
        return CIWHelper(
            self.screen_tt6_cover.cover,
            self.mask_tt6_cover.cover,
            self.image_def,
        )

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
        new_drops = self.calculate_new_drops(*args, **kwargs)
        if new_drops is not None:
            await self.screen_tt6_cover.send_drop_pct_command(new_drops[0])
            await self.mask_tt6_cover.send_drop_pct_command(new_drops[1])

    def default_baseline_drop(self, mode: CIWAspectRatioMode) -> float:
        return default_baseline_drop(mode, self.screen_tt6_cover.cover, self.image_def)

    def calculate_new_drops(
        self,
        target_aspect_ratio: float,
        mode: CIWAspectRatioMode,
        baseline_drop: float,
    ):
        try:
            return calculate_new_drops(
                target_aspect_ratio,
                mode,
                baseline_drop,
                self.screen_tt6_cover.cover.max_drop,
                self.mask_tt6_cover.cover.max_drop,
                self.image_def,
            )
        except ValueError as err:
            _LOGGER.info(f"Could not determine new drops: {err}")
            return None

    async def wait_for_motion_to_complete(self):
        return await wait_for_motion_to_complete(
            [
                self.screen_tt6_cover.cover,
                self.mask_tt6_cover.cover,
            ]
        )


def default_baseline_drop(
    mode: CIWAspectRatioMode,
    screen: Cover,
    image_def: ImageDef,
) -> float:
    """
    Return the most useful baseline_drop for each mode

    FIXED_BOTTOM: bottom of image when screen fully extended - mask will move
    FIXED_TOP: top of image when screen fully extended - screen will move
    FIXED_MIDDLE: middle of image when screen fully extended - screen and mask will move
    """
    if mode is CIWAspectRatioMode.FIXED_BOTTOM:
        return screen.max_drop - image_def.bottom_border_height
    elif mode is CIWAspectRatioMode.FIXED_TOP:
        return screen.max_drop - image_def.bottom_border_height - image_def.height
    elif mode is CIWAspectRatioMode.FIXED_MIDDLE:
        return screen.max_drop - image_def.bottom_border_height - image_def.height / 2.0
    else:
        raise ValueError("Invalid aspect ratio mode")


def calculate_new_drops(
    target_aspect_ratio: float,
    mode: CIWAspectRatioMode,
    baseline_drop: float,
    screen_max_drop: float,
    mask_max_drop: float,
    image_def: ImageDef,
):
    """
    Calculate new screen and mask drops to set a target aspect ratio

    Returns a tuple of (screen_drop_pct, mask_drop_pct)
    Won't accept a baseline_drop that is not sensible
    Generally tolerant of an invalid aspect ratio
    Will cap the new image height if it is too large
    (i.e. if 4:3 is requested on a 16:9 screen)
    Depending on baseline_drop, the returned percentages could be invalid
    but note that send_drop_pct_command will cap/floor them
    """
    check_baseline_drop(mode, baseline_drop, screen_max_drop, mask_max_drop, image_def)
    new_image_height = image_def.implied_image_height(target_aspect_ratio)
    if mode is CIWAspectRatioMode.FIXED_BOTTOM:
        newsd = baseline_drop + image_def.bottom_border_height
        newmd = baseline_drop - new_image_height
    elif mode is CIWAspectRatioMode.FIXED_TOP:
        newsd = baseline_drop + new_image_height + image_def.bottom_border_height
        newmd = baseline_drop
    elif mode is CIWAspectRatioMode.FIXED_MIDDLE:
        newsd = baseline_drop + new_image_height / 2.0 + image_def.bottom_border_height
        newmd = baseline_drop - new_image_height / 2.0
    else:
        raise ValueError("Invalid aspect ratio mode")
    return 1.0 - newsd / screen_max_drop, 1.0 - newmd / mask_max_drop


def check_baseline_drop(
    mode: CIWAspectRatioMode,
    baseline_drop: float,
    screen_max_drop: float,
    mask_max_drop: float,
    image_def: ImageDef,
):
    """
    Validate the baseline drop

    Assumes a minimum possible image height defined by the max sensible aspect ratio
    For min baseline drop, mask drop is always 0
    For max baseline drop, screen drop is always screen_max_drop
    """
    min_image_height = image_def.width / MAX_ASPECT_RATIO
    if mode is CIWAspectRatioMode.FIXED_BOTTOM:
        min_baseline_drop = min_image_height
        max_baseline_drop = screen_max_drop - image_def.bottom_border_height
    elif mode is CIWAspectRatioMode.FIXED_TOP:
        min_baseline_drop = 0.0
        max_baseline_drop = mask_max_drop
    elif mode is CIWAspectRatioMode.FIXED_MIDDLE:
        min_baseline_drop = min_image_height / 2.0
        max_baseline_drop = (
            screen_max_drop - image_def.bottom_border_height - min_image_height / 2.0
        )
    else:
        raise ValueError("Invalid aspect ratio mode")

    if baseline_drop < min_baseline_drop or baseline_drop > max_baseline_drop:
        raise ValueError(
            f"Invalid baseline drop of {baseline_drop} - "
            f"should be between {min_baseline_drop} and {max_baseline_drop}",
        )
