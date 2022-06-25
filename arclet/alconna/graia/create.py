from __future__ import annotations

from typing import TYPE_CHECKING, Type

from creart import AbstractCreator, CreateTargetInfo, it
from graia.creart.broadcast import BroadcastCreator
from graia.creart.saya import SayaCreator

if TYPE_CHECKING:
    from arclet.alconna.graia.saya import AlconnaBehaviour


class AlconnaBehaviorCreator(AbstractCreator):
    targets = (
        CreateTargetInfo("arclet.alconna.graia.saya", "AlconnaBehavior"),
    )

    @staticmethod
    def available() -> bool:
        try:
            import arclet.alconna.graia.saya

            return BroadcastCreator.available() and SayaCreator.available()
        except ImportError:
            return False

    @staticmethod
    def create(create_type: Type['AlconnaBehaviour']) -> 'AlconnaBehaviour':
        from graia.broadcast import Broadcast
        from graia.saya import Saya
        from arclet.alconna.manager import command_manager

        broadcast = it(Broadcast)
        saya = it(Saya)
        behavior = create_type(broadcast, command_manager)
        saya.install_behaviours(behavior)
        return behavior
