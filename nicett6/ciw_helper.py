from contextlib import contextmanager
from enum import Enum
import logging
import math
from nicett6.utils import AsyncObserver, check_pct
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

    def __init__(self, screen: Cover, mask: Cover, image_def: ImageDef):
        self.screen = screen
        self.mask = mask
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
                self.screen.max_drop,
                self.mask.max_drop,
                self.image_def,
            )
        except ValueError as err:
            _LOGGER.info(f"Could not determine new drops: {err}")
            return None


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
    baseline_drop: float,
    screen_max_drop: float,
    mask_max_drop: float,
    image_def: ImageDef,
):
    """
    Calculate new screen and mask drops to set a target aspect ratio

    Returns a tuple of (screen_drop_pct, mask_drop_pct)
    """
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
    return (
        check_pct("Implied screen drop", 1.0 - newsd / screen_max_drop),
        check_pct("Implied mask drop", 1.0 - newmd / mask_max_drop),
    )


@contextmanager
def ciw_position_logger(helper: CIWHelper, loglevel: int = logging.DEBUG):
    logger = CIWPositionLogger(helper, loglevel)
    try:
        logger.start_logging()
        yield logger
    finally:
        logger.stop_logging()


class CIWPositionLogger(AsyncObserver):
    def __init__(self, helper: CIWHelper, loglevel: int = logging.DEBUG):
        super().__init__()
        self.helper = helper
        self.loglevel = loglevel

    def start_logging(self):
        self.helper.screen.attach(self)
        self.helper.mask.attach(self)

    def stop_logging(self):
        self.helper.screen.detach(self)
        self.helper.mask.detach(self)

    async def update(self, observable):
        _LOGGER.log(
            self.loglevel,
            f"cover: {observable.name}; "
            f"aspect_ratio: {self.helper.aspect_ratio}; "
            f"screen_drop: {self.helper.screen.drop}; "
            f"mask_drop: {self.helper.mask.drop}",
        )
