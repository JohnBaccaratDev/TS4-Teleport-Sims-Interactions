import os
import services
import sims4
from objects.base_object import BaseObject
from sims4.resources import Types
from sims4.tuning.instance_manager import InstanceManager
from statistics.commodity_tracker import CommodityTracker
from teleport_sims_interactions.inject import inject_to
from teleport_sims_interactions.tsi_config import TsiConfig
from teleport_sims_interactions.tsi_globals import TsiGlobals
from zone_manager import ZoneManager

tsi_objects_interactions = (
    15338240950927191414,   # TSI_TeleportFromVicinity
    15645205003226109409,   # TSI_TeleportFromHouseholds
    12049733400046128765,   # TSI_TeleportFromEverywhere
    11429096759371179659,   # TSI_TeleportPreviouslyTeleported
    17998400609174570543,   # TSI_Config_Interaction_object_dispersal
    15077158744796329099    # TSI_Config_Interaction_ground_dispersal
)

tsi_sim_interactions = (
    9491249349531642848,    # TSI_LeaveForce
    15493171469843325676    # TSI_SendAllBack
)

with sims4.reload.protected(globals()):
    added_terrain_interactions = False
    added_sim_interactions = False

def get_sa_tuple_for_interactions(interactions):
    affordance_manager = services.affordance_manager()
    sa_list = []
    for sa_id in interactions:
        key = sims4.resources.get_resource_key(sa_id, Types.INTERACTION)
        sa_tuning = affordance_manager.get(key)
        if not sa_tuning is None:
            sa_list.append(sa_tuning)
    return tuple(sa_list)


@inject_to(InstanceManager, "load_data_into_class_instances")
def inject_object_interactions(original, self, *args, **kwargs):
    original(self, *args, **kwargs)

    if self.TYPE == Types.OBJECT:
        sa_for_objects_tuple = get_sa_tuple_for_interactions(tsi_objects_interactions)
        sa_for_sims_tuple = get_sa_tuple_for_interactions(tsi_sim_interactions)

        for (key, cls) in self._tuned_classes.items():
            if hasattr(cls, '_super_affordances'):

                # Since the ground already gets these interactions -> Avoid adding them to object itself.
                if hasattr(cls, "provides_terrain_interactions") and cls.provides_terrain_interactions and not cls.__qualname__ == "object_terrain":
                    continue

                cls._super_affordances += sa_for_objects_tuple

                if cls.__qualname__ == "object_sim":
                    cls._super_affordances += sa_for_sims_tuple

@inject_to(CommodityTracker, "on_initial_startup")
def inject_CommodityTracker_on_initial_startup(original, self):
    original(self)

    if self.owner is not None and self.owner.is_sim and self.owner.is_npc and TsiGlobals.sim_was_teleported(self.owner):
        TsiGlobals.max_commodities(self.owner)

@inject_to(BaseObject, "destroy")
def inject_BaseObject_destroy(original, self, source=None, cause=None, **kwargs):
    original(self, source=source, cause=cause, **kwargs)

    if self.is_sim and TsiGlobals.sim_was_teleported(self):
        TsiGlobals.remove_from_was_teleported(self.sim_id)


added_reset_inject = False
@inject_to(ZoneManager, "_update_current_zone")
def inject_ZoneManager_update_current_zone(original, self, zone_id):
    global added_reset_inject
    original(self, zone_id)

    TsiGlobals.clear_was_teleported()

TsiConfig.get_to_export()
TsiConfig.read_config()

try:
    log_file = TsiGlobals.get_log_file_path()
    if os.path.exists(log_file):
        os.remove(log_file)
except:
    pass