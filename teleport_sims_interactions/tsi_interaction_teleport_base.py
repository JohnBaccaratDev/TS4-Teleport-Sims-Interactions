import math as pymath

import alarms
import clock
import os
import services
import teleport_sims_interactions
import terrain
import sims
import sims4
import traceback
from build_buy import get_room_id
from interactions.base.immediate_interaction import ImmediateSuperInteraction
import routing
from objects import ALL_HIDDEN_REASONS
from objects.object_enums import ResetReason
from rabbit_hole.career_rabbit_hole import CareerRabbitHole
from sims.sim_info_types import Species, Age
from sims.sim_spawner import SimSpawner
from sims4.localization import _create_localized_string, LocalizationHelperTuning, ConcatenationStyle
from sims4.math import Location, Transform
from teleport_sims_interactions import TsiConfig
from teleport_sims_interactions.tsi_interaction_mixin import TsiInteractionMixin
from ui.ui_dialog import UiDialogOkCancel
from world.spawn_point import SpawnPointOption
from teleport_sims_interactions.tsi_globals import TsiGlobals, logger

if TsiGlobals.has_update_with_faries:
    from carry.carry_utils import is_wing_proxy_object


class TsiTeleportBase(ImmediateSuperInteraction, TsiInteractionMixin):

    sim_infos_to_teleport = list()
    rabbit_hole_sim_infos = list()
    original_location = None
    teleport_to_object = False


    def _trigger_interaction_start_event(self):
        self.set_original_location()


    def set_original_location(self):
        if self.has_ground_interactions(self.target) and hasattr(self, "context") and self.context is not None and hasattr(self.context, "pick") and self.context.pick is not None:
            self.original_location = sims4.math.Location(sims4.math.Transform(self.context.pick.location), self.context.pick.routing_surface)
            self.teleport_to_object = False
        else:
            self.original_location = self.target.location
            self.teleport_to_object = True


    def start_teleport(self, to_teleport):
        try:
            self.sim_infos_to_teleport = list()
            self.rabbit_hole_sim_infos = list()
            rabbithole_service = services.get_rabbit_hole_service()

            for id in to_teleport:
                sim_info = services.sim_info_manager().get(id)
                if rabbithole_service.is_in_rabbit_hole(sim_info.sim_id):
                    self.rabbit_hole_sim_infos.append(sim_info)
                else:
                    self.sim_infos_to_teleport.append(sim_info)

            if len(self.rabbit_hole_sim_infos) > 0:
                rh = {}
                for si in self.rabbit_hole_sim_infos:
                    rabbithole_display = self.get_localized_string_for_rabbit_hole(si)
                    if rabbithole_display is None:
                        continue

                    if rabbithole_display in rh:
                        rh[rabbithole_display].append(si)
                    else:
                        rh[rabbithole_display] = list()
                        rh[rabbithole_display].append(si)

                text = sims4.localization._create_localized_string(0x0FA95301)
                for rabbithole in rh.keys():
                    sims = ""
                    for sim_info in rh[rabbithole]:
                        if sim_info.sim_id == rh[rabbithole][0].sim_id:
                            sims += str(sim_info.first_name) + " " + str(sim_info.last_name)
                        else:
                            sims += ", " + str(sim_info.first_name) + " " + str(sim_info.last_name)

                    sims = LocalizationHelperTuning.get_raw_text(sims)
                    rabbithole_text = sims4.localization._create_localized_string(rabbithole._string_id)
                    line = sims4.localization._create_localized_string(0x0FA95302, rabbithole_text, sims)
                    text = sims4.localization.LocalizationHelperTuning.get_separated_string_by_style(ConcatenationStyle.NEW_LINE_SEPARATION, text, LocalizationHelperTuning.get_raw_text(""))
                    text = sims4.localization.LocalizationHelperTuning.get_separated_string_by_style(ConcatenationStyle.NEW_LINE_SEPARATION, text, line)
                final_text = lambda **_: text
                dialog = self.get_rabbit_hole_dialog(final_text)
                dialog.show_dialog(on_response=self.rabbithole_dialog_callback)
            else:
                self.teleport_sims()
        except Exception as e:
            with open(TsiGlobals.get_log_file_path(), "w") as f:
                f.writelines(traceback.format_exc())
            raise e



    def get_rabbit_hole_dialog(self, text):
        title = lambda **_: sims4.localization._create_localized_string(0xE69983E2)
        ok = lambda **_: sims4.localization._create_localized_string(0xC5922585)
        cancel = lambda **_: sims4.localization._create_localized_string(0x4F69892E)
        return UiDialogOkCancel.TunableFactory().default((services.client_manager().get_first_client().active_sim), title=title, text=text, text_ok=ok, text_cancel=cancel)


    def get_localized_string_for_rabbit_hole(self, sim_info):
        rabbithole_service = services.get_rabbit_hole_service()
        if rabbithole_service.is_in_rabbit_hole(sim_info.sim_id):
            for rabbit_hole in rabbithole_service._rabbit_holes[sim_info.sim_id]:
                interaction = None
                if rabbit_hole.affordance is not None:
                    interaction = rabbit_hole.affordance
                elif isinstance(rabbit_hole, CareerRabbitHole):
                    interaction = rabbit_hole.get_affordance(sim_info, rabbit_hole._career_uid)

                if interaction is not None:
                    if hasattr(interaction, "visual_type_override_data") and interaction.visual_type_override_data is not None and hasattr(interaction.visual_type_override_data, "tooltip_text") and interaction.visual_type_override_data.tooltip_text is not None:
                        return interaction.visual_type_override_data.tooltip_text
                    if hasattr(interaction, "display_name"):
                        return interaction.display_name

                return LocalizationHelperTuning.get_raw_text(str(rabbit_hole))
        return None


    def rabbithole_dialog_callback(self, dialog):
        if dialog.accepted:
            for sim_info in self.rabbit_hole_sim_infos:
                self.sim_infos_to_teleport.append(sim_info)

        if len(self.sim_infos_to_teleport) > 0:
            self.teleport_sims()
        self.rabbit_hole_sim_infos = list()


    def sort_for_teleport(self, sim):
        age = sim.age
        if sim.is_teen_or_older:
            age = Age.TEEN

        if sim.species == Species.HORSE:
            age *= 2 * 2
        elif sim.species != Species.HUMAN:
            age /= 2

        return age


    def teleport_sims(self):
        if len(self.sim_infos_to_teleport) < 1:
            return

        self.sim_infos_to_teleport.sort(key=self.sort_for_teleport, reverse=True)
        locations = self.get_teleport_locations()
        loci = 0

        TsiGlobals.clear_previous_teleported()
        for si in self.sim_infos_to_teleport:
            TsiGlobals.add_to_previous_teleported(si.sim_id)
            self.teleport_single_sim(si, locations[loci])
            loci += 1
            if len(locations) <= loci:
                loci = 0

        if TsiGlobals.has_update_with_faries and len(TsiGlobals.add_wings_back) > 0:
            if TsiGlobals.add_wings_back_alarm is not None:
                TsiGlobals.remove_add_wings_alarm()
            TsiGlobals.add_wings_back_alarm = alarms.add_alarm_real_time(TsiGlobals, clock.interval_in_real_seconds(1), TsiGlobals.add_wings)

        self.reset_state()


    def reset_state(self):
        self.original_location = None
        while len(self.sim_infos_to_teleport) > 0:
            self.sim_infos_to_teleport.pop()


    def teleport_single_sim(self, sim_info, loc):
        logger.info(str(sim_info) + " is going to be teleported.")
        sim_instance = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)

        if sim_instance is not None:
            TsiGlobals.add_to_was_teleported(sim_info)
            if not TsiGlobals.sim_is_in_pose(sim_instance):
                if TsiGlobals.has_update_with_faries and sim_instance.posture_state.back.target is not None and is_wing_proxy_object(sim_instance.posture_state.back.target):
                    TsiGlobals.add_to_add_wings_back(sim_info)

                sim_instance.reset(ResetReason.RESET_EXPECTED, None, "Was teleported")
            sim_instance.location = loc
            logger.info(str(sim_info) + " was teleported to " + str(loc.transform.translation) + ".")
            TsiGlobals.max_commodities(sim_instance.sim_info)

        else:
            TsiGlobals.add_to_was_teleported(sim_info)
            SimSpawner.spawn_sim(sim_info, sim_location=loc, from_load=True, spawn_point_option=(SpawnPointOption.SPAWN_SAME_POINT))
            sim_instance = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            logger.info(str(sim_info) + " was spawned at " + str(loc.transform.translation) + ".")


        if not TsiGlobals.sim_instance_is_in_home_or_vacation_zone(sim_instance):
            if sim_info.is_npc:
                sim_instance.autonomy_component.reset_role_tracker()
                sim_instance.add_role(services.role_state_manager().get(0x3DF6))
            services.get_zone_situation_manager().create_visit_situation(sim_instance)
        return sim_instance


    def ring_position(cls, steps):

        ring_width = pymath.ceil(pymath.sqrt(steps))
        if ring_width % 2 == 0:
            ring_width += 1

        steps -= ((ring_width - 2) * (ring_width - 2))

        pos = (pymath.floor(ring_width / 2), pymath.floor(ring_width / 2))

        directions = [(-1, 0), (0, -1), (1, 0) , (0, 1)]
        steps_for_dir = ring_width - 1
        for d in directions:
            if steps <= 0:
                break
            if steps >= steps_for_dir:
                pos = (pos[0] + d[0] * steps_for_dir, pos[1] + d[1] * steps_for_dir)
                steps -= steps_for_dir
            else:
                pos = (pos[0] + d[0] * steps, pos[1] + d[1] * steps)
                steps = 0

        pos = (pos[0] * 0.5, pos[1] * 0.5)
        return pos


    def get_theoretical_pos(self, origin, steps):
        rp = self.ring_position(steps)
        x = origin.transform.translation.x + rp[0]
        z = origin.transform.translation.z + rp[1]
        y = terrain.get_terrain_height(x, z, origin.routing_surface)
        return Location(Transform(sims4.math.Vector3(x, y, z), origin.transform.orientation), origin.routing_surface)


    def get_teleport_locations(self):
        locations = list()
        if (self.teleport_to_object and not TsiConfig.object_dispersal) or (not self.teleport_to_object and not TsiConfig.ground_dispersal):
            locations.append(self.original_location)
            return locations

        lot = services.active_lot()
        if lot is None: # No lot -> Why even try?
            logger.error("No active lot?")
            locations.append(self.original_location)
            return locations

        pos = self.adjust_xz_at_center((self.original_location.transform.translation.x, self.original_location.transform.translation.y, self.original_location.transform.translation.z), self.round_xz)
        centered_x = pos[0]
        centered_z = pos[2]
        centered_y = terrain.get_terrain_height(centered_x, centered_z, self.original_location.routing_surface)
        if centered_y is None or centered_y == 0:
            logger.error("Axis y for snapped location returned " + str(centered_y))
            locations.append(self.original_location)
            return locations

        centered_loc = Location(Transform(sims4.math.Vector3(centered_x, centered_y, centered_z), self.original_location.transform.orientation), self.original_location.routing_surface)
        original_pos_room_id = get_room_id(self.original_location.zone_id, self.original_location.transform.translation, self.original_location.level)

        room_objects = list()
        obj_manager = services.current_zone().object_manager
        for obj in obj_manager._objects.values():
            if obj.ceiling_placement:
                continue

            if get_room_id(obj.zone_id, obj.position, obj.level) == original_pos_room_id and not (isinstance(obj, sims.sim.Sim) and any( obj.sim_id == sim_info.sim_id for sim_info in self.sim_infos_to_teleport )):
                room_objects.append(obj)

        i = 0
        directions = [(0.3, 0), (0, 0.3), (-0.3, 0), (0, -0.3), (0.1732, 0.1732), (0.1732, -0.1732), (-0.1732, -0.1732), (-0.1732, 0.1732)]
        while len(locations) <= len(self.sim_infos_to_teleport) and i <= 225:
            i += 1

            loc = self.get_theoretical_pos(centered_loc, i)

            if abs(loc.transform.translation.y - self.original_location.transform.translation.y) > 3:
                logger.warn("Ignored position " + str(loc.transform.translation) + " as y axis difference is too large - Original: " + str(self.original_location.transform.translation.y) + " Snapped: " + str(loc.transform.translation.y))
                continue

            # If near a wall to a different room ignore loc
            pos = (loc.transform.translation.x, loc.transform.translation.y, loc.transform.translation.z)
            cont = False
            for d in directions:
                xyz = self.adjust_xz_at_center(pos, self.add_xz, d[0], d[1])
                p = sims4.math.Vector3Immutable(xyz[0], pos[1], xyz[2])
                room_id = get_room_id(self.original_location.zone_id, p, self.original_location.level)
                if room_id != original_pos_room_id:
                    logger.info("Ignored position " + str(loc.transform.translation) + " as it is too near the wall of another room")
                    cont = True
                    break

            if cont:
                continue

            directions_small = [(0.1, 0), (0, 0.1), (-0.1, 0), (0, -0.1), (0.075, 0.075), (0.075, -0.075), (-0.075, -0.075), (-0.075, 0.075)]
            # directions_smallest = [(0.08, 0), (0, 0.08), (-0.08, 0), (0, -0.08), (0.055, 0.055), (0.055, -0.055), (-0.055, -0.055), (-0.055, 0.055)]
            walkable = self.get_walkwable_vectors(loc, room_objects, directions_small)
            if len(walkable) == 0: # If we can't walk in any direction throw it away
                continue
            elif len(walkable) < 8: # If we can atleast walk in one, but not all, direction then test in smaller steps from the walkable locations
                cont = True
                # Introduces further getting-stuck problems currently sadly
                # for tr in walkable:
                #     new_loc = Location(tr, loc.routing_surface)
                #     if len(self.get_walkwable_vectors(loc, room_objects, directions_smallest)) == 8:
                #         loc = new_loc
                #         cont = False
                #         break
            # Else -> We have 8 walkable directions, append

            if cont:
                continue

            locations.append(loc)

        if len(locations) < 1:
            logger.warn("Could not determine adequate teleportation locations. The sims will just be teleported to the originally clicked location.")
            locations.append(self.original_location)
        else:
            logger.info("Determined " + str(len(locations)) + " teleport locations for " + str(len(self.sim_infos_to_teleport)) + " sims, after " + str(i) + " steps.")
        return locations

    # Tests for overlap with objects in multiple directions if walked, return a list of transforms that would be walkable
    def get_walkwable_vectors(self, from_loc, room_objects, directions):

        walkable = list()
        for d in directions:
            pos = (from_loc.transform.translation.x, from_loc.transform.translation.y, from_loc.transform.translation.z)
            xyz = self.adjust_xz_at_center(pos, self.add_xz, d[0], d[1])
            p = sims4.math.Vector3Immutable(xyz[0], pos[1], xyz[2])

            pt = Transform(p, self.original_location.transform.orientation)

            br = False
            for obj in room_objects:
                raycast_context = obj.raycast_context(for_carryable=False)
                slot_routing_location = obj.get_routing_location_for_transform(from_loc.transform, routing_surface=(self.original_location.routing_surface))
                routing_location = obj.get_routing_location_for_transform(pt, routing_surface=(self.original_location.routing_surface))
                # I'll be honest. I have no idea how this function is actually supposed to be used
                # It is only used a single time in the vanilla code base and I have no idea what "slot" means in this context
                # It does however give back results that fit. :)
                result, blocking_object_id = routing.ray_test_verbose(slot_routing_location, routing_location,
                                                                      raycast_context, return_object_id=True)
                if result == routing.RAYCAST_HIT_TYPE_IMPASSABLE or result == routing.RAYCAST_HIT_TYPE_LOS_IMPASSABLE:
                    br = True
                    break
            if not br:
                walkable.append(pt)

        return walkable

    def adjust_xz_at_center(self, pos, callback, *args):

        lot = services.active_lot()
        if lot is None:
            raise Exception("No Lot found")

        cx = lot.corners[0].x
        cz = lot.corners[0].z

        x = pos[0]
        y = pos[1]
        z = pos[2]

        # subtract so we are at an origin
        x -= cx
        z -= cz

        tempx = x
        tempz = z

        r = lot.rotation

        # rotate around origin
        x = (tempx * pymath.cos(r)) - (tempz * pymath.sin(r))
        z = (tempx * pymath.sin(r)) + (tempz * pymath.cos(r))

        new = callback(x, z, args)
        x = new[0]
        z = new[1]

        # rest is reversal of the whole operation chain
        tempx = x
        tempz = z

        x = (tempx * pymath.cos(-r)) - (tempz * pymath.sin(-r))
        z = (tempx * pymath.sin(-r)) + (tempz * pymath.cos(-r))

        x += cx
        z += cz

        return (x, y, z)


    def add_xz(self, x, z, *args):
        x += args[0][0]
        z += args[0][1]
        return (x, z)


    def round_xz(self, x, z, *args):
        x = round(x * 2) / 2
        z = round(z * 2) / 2
        return (x, z)