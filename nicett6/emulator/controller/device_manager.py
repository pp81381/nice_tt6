import logging
from abc import ABC, abstractmethod
from typing import Dict

from nicett6.emulator.controller.web_pos_manager import WebPosManager
from nicett6.emulator.cover_emulator import TT6CoverEmulator
from nicett6.ttbus_device import TTBusDeviceAddress

_LOGGER = logging.getLogger(__name__)


class DuplicateDeviceError(Exception):
    pass


class DeviceRegistry(ABC):
    @abstractmethod
    def lookup_device(self, tt_addr: TTBusDeviceAddress) -> TT6CoverEmulator:
        pass


class DeviceManager(DeviceRegistry):
    def __init__(self, web_pos_manager: WebPosManager) -> None:
        self.devices: Dict[TTBusDeviceAddress, TT6CoverEmulator] = {}
        self.web_pos_manager = web_pos_manager

    def register_device(self, device: TT6CoverEmulator) -> None:
        if device.tt_addr in self.devices:
            raise DuplicateDeviceError()
        self.devices[device.tt_addr] = device
        device.attach(self.web_pos_manager)
        _LOGGER.info(f"registered device {device.tt_addr}")

    def deregister_device(self, tt_addr: TTBusDeviceAddress) -> None:
        device = self.devices[tt_addr]
        device.detach(self.web_pos_manager)
        del self.devices[tt_addr]
        _LOGGER.info(f"deregistered device {tt_addr}")

    def lookup_device(self, tt_addr: TTBusDeviceAddress) -> TT6CoverEmulator:
        return self.devices[tt_addr]
