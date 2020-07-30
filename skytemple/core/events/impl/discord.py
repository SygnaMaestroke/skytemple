"""
Discord presence module.
If the extra dependencies are not installed, importing this module will raise an ImportError.
"""
#  Copyright 2020 Parakoopa
#
#  This file is part of SkyTemple.
#
#  SkyTemple is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SkyTemple is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SkyTemple.  If not, see <https://www.gnu.org/licenses/>.
import asyncio
import logging
import os
from typing import List, Optional

from gi.repository import GLib

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.events.abstract_listener import AbstractListener
from skytemple.core.module_controller import AbstractController
from skytemple.core.rom_project import RomProject
from pypresence import Presence
import time

from skytemple.core.string_provider import StringType
from skytemple_files.data.md.model import NUM_ENTITIES

CLIENT_ID = "736538698719690814"
IDLE_TIMEOUT = 5 * 60
logger = logging.getLogger(__name__)


class DiscordPresence(AbstractListener):
    def __init__(self):
        self.rpc: Presence = Presence(CLIENT_ID)
        self.rpc.connect()
        self._idle_timeout_id = None

        self.start = None
        self._reset_playtime()
        self.current_presence = 'main'
        self.module_info = None
        self.module_state = None
        self.rom_name = None
        self.debugger_script_name = None
        self.project: Optional[RomProject] = None

    def on_main_window_focus(self):
        if self._idle_timeout_id is not None:
            GLib.source_remove(self._idle_timeout_id)
        if self.current_presence == 'idle':
            self._reset_playtime()
        self.current_presence = 'main'
        self._update_current_presence()

    def on_debugger_window_focus(self):
        if self._idle_timeout_id is not None:
            GLib.source_remove(self._idle_timeout_id)
        self.current_presence = 'debugger'
        if self.current_presence == 'idle':
            self._reset_playtime()
        self._update_current_presence()

    def on_idle(self):
        self._idle_timeout_id = None
        self.current_presence = 'idle'
        self._update_current_presence()

    def on_focus_lost(self):
        if self._idle_timeout_id is None:
            self._idle_timeout_id = GLib.timeout_add_seconds(IDLE_TIMEOUT, self.on_idle)

    def on_project_open(self, project: RomProject):
        self.project = project
        self.rom_name = os.path.basename(project.filename)
        self._update_current_presence()

    def on_view_switch(self, module: AbstractModule, controller: AbstractController, breadcrumbs: List[str]):
        mod_handler = getattr(self, f"on_view_switch__{module.__class__.__name__}", None)
        if mod_handler and callable(mod_handler):
            mod_handler(module, controller, breadcrumbs)
        else:
            self.module_info = f'Editing in module "{module.__class__.__name__}"'
            self.module_state = self.rom_name
        self._update_current_presence()

    def on_view_switch__MiscGraphicsModule(self, module: AbstractModule, controller: AbstractController, breadcrumbs: List[str]):
        from skytemple.module.misc_graphics.module import MiscGraphicsModule
        from skytemple.module.misc_graphics.controller.w16 import W16Controller
        module: MiscGraphicsModule

        self.module_info = 'Editing graphics'
        self.module_state = self.rom_name
        if isinstance(controller, W16Controller):
            self.module_state = module.list_of_w16s[controller.item_id]

    def on_view_switch__DungeonGraphicsModule(self, module: AbstractModule, controller: AbstractController, breadcrumbs: List[str]):
        from skytemple.module.dungeon_graphics.module import DungeonGraphicsModule
        from skytemple.module.dungeon_graphics.controller.tileset import TilesetController
        module: DungeonGraphicsModule

        self.module_info = 'Editing dungeon tilesets'
        self.module_state = self.rom_name
        if isinstance(controller, TilesetController):
            self.module_state = f'Tileset {controller.item_id}'

    def on_view_switch__BgpModule(self, module: AbstractModule, controller: AbstractController, breadcrumbs: List[str]):
        from skytemple.module.bgp.module import BgpModule
        from skytemple.module.bgp.controller.bgp import BgpController
        module: BgpModule

        self.module_info = 'Editing background images'
        self.module_state = self.rom_name
        if isinstance(controller, BgpController):
            self.module_state = module.list_of_bgps[controller.item_id]

    def on_view_switch__RomModule(self, module: AbstractModule, controller: AbstractController, breadcrumbs: List[str]):
        self.module_info = 'Editing the ROM'
        self.module_state = self.rom_name

    def on_view_switch__ListsModule(self, module: AbstractModule, controller: AbstractController, breadcrumbs: List[str]):
        from skytemple.module.lists.module import ListsModule
        from skytemple.module.lists.controller.actor_list import ActorListController
        module: ListsModule

        self.module_info = 'Editing lists'
        self.module_state = self.rom_name
        if isinstance(controller, ActorListController):
            self.module_info = 'Editing the actor list'

    def on_view_switch__PatchModule(self, module: AbstractModule, controller: AbstractController, breadcrumbs: List[str]):
        self.module_info = 'Editing patches'
        self.module_state = self.rom_name

    def on_view_switch__MapBgModule(self, module: AbstractModule, controller: AbstractController, breadcrumbs: List[str]):
        from skytemple.module.map_bg.module import MapBgModule
        from skytemple.module.map_bg.controller.bg import BgController
        module: MapBgModule

        self.module_info = 'Editing map backgrounds'
        self.module_state = self.rom_name
        if isinstance(controller, BgController):
            self.module_state = breadcrumbs[0]

    def on_view_switch__ScriptModule(self, module: AbstractModule, controller: AbstractController, breadcrumbs: List[str]):
        from skytemple.module.script.module import ScriptModule
        from skytemple.module.script.controller.ssa import SsaController
        module: ScriptModule

        self.module_info = 'Editing scenes'
        self.module_state = self.rom_name
        if isinstance(controller, SsaController):
            if controller.type == 'sse':
                self.module_state = f'{breadcrumbs[1]} / {breadcrumbs[0]}'
            else:
                self.module_state = f'{breadcrumbs[2]} / {breadcrumbs[0]}'

    def on_view_switch__MonsterModule(self, module: AbstractModule, controller: AbstractController, breadcrumbs: List[str]):
        from skytemple.module.monster.module import MonsterModule
        from skytemple.module.monster.controller.monster import MonsterController
        module: MonsterModule

        self.module_info = 'Editing Pokémon'
        self.module_state = self.rom_name
        if isinstance(controller, MonsterController):
            self.module_state = module.project.get_string_provider().get_value(
                StringType.POKEMON_NAMES, controller.item_id % NUM_ENTITIES
            )

    def on_view_switch__StringsModule(self, module: AbstractModule, controller: AbstractController, breadcrumbs: List[str]):
        from skytemple.module.strings.module import StringsModule
        from skytemple.module.strings.controller.strings import StringsController
        module: StringsModule

        self.module_info = 'Editing Text Strings'
        self.module_state = self.rom_name
        if isinstance(controller, StringsController):
            self.module_state = controller.langname

    def on_debugger_script_open(self, script_name: str):
        self.debugger_script_name = script_name.replace(self.project.get_project_file_manager().dir(), '')
        self._update_current_presence()

    def _update_current_presence(self):
        if self.current_presence == 'main':
            self._update_presence(
                state=self.module_state,
                details=self.module_info,
                start=self.start,
                large_text=self.rom_name
            )
        elif self.current_presence == 'debugger':
            self._update_presence(
                state=self.debugger_script_name,
                details="In the debugger" if self.debugger_script_name is None else "Editing script",
                start=self.start,
                large_text=self.rom_name,
                small_image="bug"
            )
        else:  # idle
            self._update_presence(
                state=None,
                details="Idle",
                start=None,
                large_text=self.rom_name
            )

    def _update_presence(
            self, state, details, start,
            large_text, large_image='skytemple',
            small_image=None, small_text=None
    ):
        result = self.rpc.update(state=state, details=details, start=start, large_image=large_image,
                                 large_text=large_text, small_image=small_image, small_text=small_text)
        logger.debug(f"Presence update result: {result}")

    def _reset_playtime(self):
        self.start = int(time.time())