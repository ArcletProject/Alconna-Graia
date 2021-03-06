from __future__ import annotations

from typing import TYPE_CHECKING, Type
from creart import AbstractCreator, CreateTargetInfo, it, exists_module, mixin

if TYPE_CHECKING:
    from arclet.alconna.graia.saya import AlconnaBehaviour


class AlconnaBehaviorCreator(AbstractCreator):
    targets = (
        CreateTargetInfo(
            module="arclet.alconna.graia.saya",
            identify="AlconnaBehaviour",
            humanized_name="Saya Behavior of Alconna",
            description=(
                "<common, arclet, alconna> A High-performance, Generality, "
                "Humane Command Line Arguments Parser Library."
            ),
            author=["ArcletProject@github"],
        ),
    )
    from graia.creart.broadcast import BroadcastCreator
    from graia.creart.saya import SayaCreator
    @staticmethod
    @mixin(BroadcastCreator, SayaCreator)
    def available() -> bool:
        return exists_module("arclet.alconna.graia.saya")

    @staticmethod
    def create(create_type: Type['AlconnaBehaviour']) -> 'AlconnaBehaviour':
        from graia.broadcast import Broadcast
        from graia.saya import Saya
        from arclet.alconna.manager import command_manager
        from arclet.alconna import config

        broadcast = it(Broadcast)
        saya = it(Saya)
        behavior = create_type(broadcast, command_manager)
        saya.install_behaviours(behavior)
        config.set_loop(broadcast.loop)
        return behavior
