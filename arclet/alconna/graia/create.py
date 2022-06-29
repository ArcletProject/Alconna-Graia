from __future__ import annotations

from typing import TYPE_CHECKING, Type

from creart import AbstractCreator, CreateTargetInfo, it, exists_module, mixin
from graia.creart.broadcast import BroadcastCreator
from graia.creart.saya import SayaCreator

if TYPE_CHECKING:
    from arclet.alconna.graia.saya import AlconnaBehaviour


class AlconnaBehaviorCreator(AbstractCreator):
    targets = (
        CreateTargetInfo(
            module="arclet.alconna.graia.saya",
            identify="AlconnaBehavior",
            humanized_name="Saya Behavior of Alconna",
            description=(
                "<common, arclet, alconna> A High-performance, Generality, "
                "Humane Command Line Arguments Parser Library."
            ),
            author=["ArcletProject@github"],
        ),
    )

    @staticmethod
    @mixin(BroadcastCreator, SayaCreator)
    def available() -> bool:
        return exists_module("arclet.alconna.graia.saya")

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
