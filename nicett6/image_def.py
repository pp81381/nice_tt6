from dataclasses import dataclass

from nicett6.utils import check_aspect_ratio


@dataclass
class ImageDef:
    """Static definition of image area relative to the bottom of a cover"""

    bottom_border_height: float
    height: float
    aspect_ratio: float

    @property
    def width(self) -> float:
        return self.height * self.aspect_ratio

    def implied_image_height(self, target_aspect_ratio: float) -> float:
        check_aspect_ratio(target_aspect_ratio)
        image_height = self.width / target_aspect_ratio
        if image_height > self.height:
            image_height = self.height
        return image_height
