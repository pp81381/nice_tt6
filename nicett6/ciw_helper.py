from contextlib import contextmanager
import logging
import math

from nicett6.cover import Cover
from nicett6.utils import AsyncObserver, check_aspect_ratio

_LOGGER = logging.getLogger(__name__)


class ImageDef:
    """Static definition of image area relative to the bottom of a cover"""

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
        check_aspect_ratio(target_aspect_ratio)
        image_height = self.width / target_aspect_ratio
        if image_height > self.height:
            image_height = self.height
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

    @contextmanager
    def position_logger(self, loglevel: int = logging.DEBUG):
        logger = CIWPositionLogger(self, loglevel)
        try:
            logger.start_logging()
            yield logger
        finally:
            logger.stop_logging()


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
