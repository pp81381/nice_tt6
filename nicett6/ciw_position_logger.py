import logging
from contextlib import contextmanager
from typing import Generator

from nicett6.ciw_helper import CIWHelper
from nicett6.cover import Cover
from nicett6.utils import AsyncObservable, AsyncObserver

_LOGGER = logging.getLogger(__name__)


@contextmanager
def position_logger(
    helper: CIWHelper, loglevel: int = logging.DEBUG
) -> Generator["CIWPositionLogger", None, None]:
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
