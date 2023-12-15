from typing import Tuple


class TTBusDeviceAddress:
    def __init__(self, address: int, node: int):
        self.address = address
        self.node = node

    @property
    def id(self) -> str:
        return f"{self.address:02X}_{self.node:02X}"

    @property
    def as_tuple(self) -> Tuple[int, int]:
        return self.address, self.node

    def __str__(self) -> str:
        return f"{type(self).__name__}(0x{self.address:02X}, 0x{self.node:02X})"

    def __eq__(self, other: object):
        if not isinstance(other, TTBusDeviceAddress):
            return False
        return self.as_tuple == other.as_tuple

    def __hash__(self) -> int:
        return hash(self.as_tuple)
