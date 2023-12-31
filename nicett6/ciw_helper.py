import logging
import math
from contextlib import contextmanager
from typing import Generator, Optional

from nicett6.cover import Cover
from nicett6.image_def import ImageDef
from nicett6.utils import AsyncObservable, AsyncObserver

_LOGGER = logging.getLogger(__name__)


class CIWHelper:
    """Helper class that represents the behaviour of a CIW screen with a mask"""

    def __init__(self, screen: Cover, mask: Cover, image_def: ImageDef):
        self.screen = screen
        self.mask = mask
        self.image_def = image_def

    @property
    def image_width(self) -> float:
        return self.image_def.width

    @property
    def image_height(self) -> Optional[float]:
        return calculate_image_height(self.screen.drop, self.mask.drop, self.image_def)

    @property
    def image_diagonal(self) -> Optional[float]:
        return calculate_image_diagonal(self.image_height, self.image_width)

    @property
    def image_area(self) -> Optional[float]:
        return calculate_image_area(self.image_height, self.image_width)

    @property
    def image_is_visible(self) -> Optional[float]:
        return self.image_height is not None

    @property
    def aspect_ratio(self) -> Optional[float]:
        ih = self.image_height
        return None if ih is None else self.image_width / ih

    @contextmanager
    def position_logger(
        self, loglevel: int = logging.DEBUG
    ) -> Generator["CIWPositionLogger", None, None]:
        logger = CIWPositionLogger(self, loglevel)
        try:
            logger.start_logging()
            yield logger
        finally:
            logger.stop_logging()


def calculate_image_height(
    screen_drop: float, mask_drop: float, image_def: ImageDef
) -> Optional[float]:
    tmp_image_height = min(
        screen_drop - image_def.bottom_border_height - mask_drop,
        image_def.height,
    )
    visible_threshold = 0.1 * image_def.height
    return tmp_image_height if tmp_image_height > visible_threshold else None


def calculate_image_diagonal(height, width) -> Optional[float]:
    return math.sqrt(width**2 + height**2) if height is not None else None


def calculate_image_area(height, width) -> Optional[float]:
    return width * height if height is not None else None


class CIWPositionLogger(AsyncObserver):
    def __init__(self, helper: CIWHelper, loglevel: int = logging.DEBUG):
        super().__init__()
        self.helper = helper
        self.loglevel = loglevel

    def start_logging(self) -> None:
        self.helper.screen.attach(self)
        self.helper.mask.attach(self)

    def stop_logging(self) -> None:
        self.helper.screen.detach(self)
        self.helper.mask.detach(self)

    def log(self, cover: Cover):
        _LOGGER.log(
            self.loglevel,
            f"cover: {cover.name}; "
            f"aspect_ratio: {self.helper.aspect_ratio}; "
            f"screen_drop: {self.helper.screen.drop}; "
            f"mask_drop: {self.helper.mask.drop}",
        )

    async def update(self, observable: AsyncObservable) -> None:
        if isinstance(observable, Cover):
            self.log(observable)
