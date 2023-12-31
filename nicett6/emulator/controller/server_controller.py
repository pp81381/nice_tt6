from abc import ABC, abstractmethod


class ServerController(ABC):
    @abstractmethod
    async def stop_server(self):
        pass
