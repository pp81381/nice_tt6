from enum import Enum
import logging
import math
from nicett6.utils import check_pct
from nicett6.cover import Cover


_LOGGER = logging.getLogger(__name__)


class CIWAspectRatioMode(Enum):
    FIXED_TOP = 1
    FIXED_MIDDLE = 2
    FIXED_BOTTOM = 3


class ImageDef:
    """Static definition of image area relative to the bottom of a cover"""

    HEIGHT_TOLERANCE = 0.00001

    def __init__(
        self,
        bottom_border_height,
        height,
        aspect_ratio,
    ):
        self.bottom_border_height = bottom_border_height
        self.height = height
        self.aspect_ratio = aspect_ratio

    @property
    def width(self):
        return self.height * self.aspect_ratio

    def implied_image_height(self, target_aspect_ratio):
        image_height = self.width / target_aspect_ratio
        if image_height > self.height + self.HEIGHT_TOLERANCE:
            raise ValueError(
                f"Image height implied by target aspect ratio ({image_height}) "
                f"is greater than the max image height ({self.height})"
            )
        return image_height


class CIWHelper:
    """Helper class that represents the behaviour of a CIW screen with a mask"""

    def __init__(
        self, screen_max_drop: float, mask_max_drop: float, image_def: ImageDef
    ):
        self.screen = Cover("Screen", screen_max_drop)
        self.mask = Cover("Mask", mask_max_drop)
        self.image_def = image_def

    @property
    def image_width(self):
        return self.image_def.width

    @property
    def image_height(self):
        return calculate_image_height(self.screen.drop, self.mask.drop, self.image_def)

    @property
    def image_diagonal(self):
        return calculate_image_diagonal(self.image_height, self.image_width)

    @property
    def image_area(self):
        return calculate_image_area(self.image_height, self.image_width)

    @property
    def image_is_visible(self):
        return self.image_height is not None

    @property
    def aspect_ratio(self):
        ih = self.image_height
        return None if ih is None else self.image_width / ih

    async def check_for_idle(self):
        """
        Check that *both* screen and mask are idle

        Has side effect of notifying observers that movement has completed
        """
        screen_is_idle = await self.screen.check_for_idle()
        mask_is_idle = await self.mask.check_for_idle()
        return screen_is_idle and mask_is_idle  # Beware of short circuit

    def calculate_new_drops(self, *args, **kwargs):
        try:
            return self._calculate_new_drops(*args, **kwargs)
        except ValueError as err:
            _LOGGER.info(f"Could not determine new drops: {err}")
            return None

    def _calculate_new_drops(
        self,
        target_aspect_ratio: float,
        mode: CIWAspectRatioMode,
        override_screen_drop_pct: float = None,
        override_mask_drop_pct: float = None,
    ):
        current_screen_drop = (
            self.screen.drop
            if override_screen_drop_pct is None
            else (1.0 - override_screen_drop_pct) * self.screen.max_drop
        )
        current_mask_drop = (
            self.mask.drop
            if override_mask_drop_pct is None
            else (1.0 - override_mask_drop_pct) * self.mask.max_drop
        )
        return calculate_new_drops(
            target_aspect_ratio,
            mode,
            current_screen_drop,
            current_mask_drop,
            self.screen.max_drop,
            self.mask.max_drop,
            self.image_def,
        )


def calculate_image_height(screen_drop, mask_drop, image_def):
    tmp_image_height = min(
        screen_drop - image_def.bottom_border_height - mask_drop,
        image_def.height,
    )
    visible_threshold = 0.1 * image_def.height
    return tmp_image_height if tmp_image_height > visible_threshold else None


def calculate_image_diagonal(height, width):
    return math.sqrt(width ** 2 + height ** 2) if height is not None else None


def calculate_image_area(height, width):
    return width * height if height is not None else None


def calculate_new_drops(
    target_aspect_ratio: float,
    mode: CIWAspectRatioMode,
    current_screen_drop: float,
    current_mask_drop: float,
    screen_max_drop: float,
    mask_max_drop: float,
    image_def: ImageDef,
):
    """
    Calculate new screen and mask drops to set a target aspect ratio

    Returns a tuple of (screen_drop_pct, mask_drop_pct)
    """
    current_image_height = calculate_image_height(
        current_screen_drop, current_mask_drop, image_def
    )
    new_image_height = image_def.implied_image_height(target_aspect_ratio)
    if mode is CIWAspectRatioMode.FIXED_BOTTOM:
        newsd, newmd = _calculate_drops_fixed_bottom(
            new_image_height,
            current_screen_drop,
            image_def.bottom_border_height,
        )
    elif mode is CIWAspectRatioMode.FIXED_TOP:
        newsd, newmd = _calculate_drops_fixed_top(
            new_image_height,
            current_image_height,
            current_screen_drop,
            current_mask_drop,
            image_def.bottom_border_height,
        )
    elif mode is CIWAspectRatioMode.FIXED_MIDDLE:
        newsd, newmd = _calculate_drops_fixed_middle(
            new_image_height,
            current_image_height,
            current_screen_drop,
            image_def.bottom_border_height,
        )
    else:
        raise ValueError("Invalid aspect ratio mode")
    return (
        check_pct("Implied screen drop", 1.0 - newsd / screen_max_drop),
        check_pct("Implied mask drop", 1.0 - newmd / mask_max_drop),
    )


def _calculate_drops_fixed_bottom(
    new_image_height, current_screen_drop, bottom_border_height
):
    bottom_of_image = current_screen_drop - bottom_border_height
    return current_screen_drop, bottom_of_image - new_image_height


def _calculate_drops_fixed_top(
    new_image_height,
    current_image_height,
    current_screen_drop,
    current_mask_drop,
    bottom_border_height,
):
    if current_image_height is not None:
        top_of_image = current_screen_drop - bottom_border_height - current_image_height
    else:
        top_of_image = current_mask_drop
    return (
        top_of_image + new_image_height + bottom_border_height,
        top_of_image,
    )


def _calculate_drops_fixed_middle(
    new_image_height,
    current_image_height,
    current_screen_drop,
    bottom_border_height,
):
    if current_image_height is None:
        raise ValueError("Image area must be visible to determine middle line")
    middle_of_image = (
        current_screen_drop - bottom_border_height - current_image_height / 2.0
    )
    return (
        middle_of_image + new_image_height / 2.0 + bottom_border_height,
        middle_of_image - new_image_height / 2.0,
    )
