import alarms
import os
import services
import sims
import sims4
import teleport_sims_interactions
from sims4.math import Location, Transform
import traceback
from objects import ALL_HIDDEN_REASONS
from objects.object_enums import ResetReason
from sims.sim_info import SimInfo
from statistics.commodity import Commodity
from statistics.statistic_categories import StatisticCategory

logger = sims4.log.Logger("TeleportSimsInteractions", default_owner="JohnBaccarat")

class TsiTeleportedItem:
    def __init__(self, si):
        self.sim_info = si

    def is_still_around(self):
        return self.sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS) is not None

class TsiGlobals:
    with sims4.reload.protected(globals()):
        was_teleported = list()
        previous_teleported = list()
        posePlayer_installed = False
        ww_installed = False
        has_update_with_faries = False
        add_wings_back = list()
        add_wings_back_alarm = None

    @classmethod
    def get_log_file_path(cls):
        return os.path.join(teleport_sims_interactions.TsiConfig.get_config_path_folder(), "JohnBaccarat_TeleportSimsInteractions_LOG.txt")

    @classmethod
    def any_not_send_back(cls):
        cls.was_teleported = list(filter(TsiTeleportedItem.is_still_around, cls.was_teleported))
        return len(cls.was_teleported) > 0


    @classmethod
    def add_to_was_teleported(cls, si):
        if not cls.sim_was_teleported(si):
            cls.was_teleported.append(TsiTeleportedItem(si))


    @classmethod
    def remove_from_was_teleported(cls, sim_id):
        for item in cls.was_teleported:
            if item.sim_info.sim_id == sim_id:
                cls.was_teleported.remove(item)
                return


    @classmethod
    def clear_was_teleported(cls):
        cls.was_teleported = list()


    @classmethod
    def sim_was_teleported(cls, sim):
        for item in cls.was_teleported:
            if item.sim_info.sim_id == sim.sim_id:
                return True
        return False


    @classmethod
    def get_teleported_item(cls, sim):
        for item in cls.was_teleported:
            if item.sim_info.sim_id == sim.sim_id:
                return item
        return None


    @classmethod
    def add_to_previous_teleported(cls, sim_id):
        cls.previous_teleported.append(sim_id)

    @classmethod
    def clear_previous_teleported(cls):
        cls.previous_teleported = list()


    @classmethod
    def sim_instance_is_in_home_or_vacation_zone(cls, sim_instance):
        to_zone_id = sim_instance.sim_info.vacation_or_home_zone_id
        from_zone_id = sim_instance.zone_id
        return from_zone_id == to_zone_id


    @classmethod
    def load_sim_into_home_zone(cls, sim_instance):
        if TsiGlobals.sim_instance_is_in_home_or_vacation_zone(sim_instance):
            zone = services.get_zone(sim_instance.sim_info.vacation_or_home_zone_id)
            if zone is not None:
                logger.info("Teleported sim to default position of lot.")
                pos = zone.lot.get_default_position()
                sim_instance.location = Location(Transform(pos, sim_instance.location.transform.orientation), sim_instance.location.routing_surface)
            else:
                logger.error("Sim is in home zone, but current zone couldn't be found?")
            return

        sim_instance.sim_info.inject_into_inactive_zone((sim_instance.sim_info.vacation_or_home_zone_id), skip_instanced_check=True)
        sim_instance.sim_info.save_sim()
        sim_instance.schedule_destroy_asap(post_delete_func=(services.get_first_client().send_selectable_sims_update), source=cls, cause="Sim Info was sent into home zone. Destroying Sim Instance.")


    @classmethod
    def max_commodities(cls, sim_info):
        for statistic in sim_info.commodity_tracker.get_all_commodities():
            if isinstance(statistic, Commodity) and not sim_info.is_locked(statistic) and statistic.is_visible and StatisticCategory.Motive_Commodities in statistic.get_categories() and statistic.max_value == 100 and statistic.min_value == -100:
                if statistic.initial_tuning is not None and statistic.initial_tuning._value_range is not None and statistic.initial_tuning._value_range.upper_bound is not None:
                    v = statistic.initial_tuning._value_range.upper_bound
                elif statistic.initial_tuning is not None and statistic.initial_tuning._value is not None:
                    v = statistic.initial_tuning._value
                    v = ((statistic.max_value - v) * 0.75 ) + v
                else:
                    v = statistic.max_value

                statistic.set_value(v)

        sim_info.commodity_tracker.update_all_commodities()

    @classmethod
    def sim_is_in_pose(cls, sim_instance):

        def is_in_posePlayer_pose(sim_instance):
            if not cls.posePlayer_installed:
                return False

            for interaction in sim_instance.get_all_running_and_queued_interactions():
                if interaction.running and isinstance(interaction, APP_PoseInteraction):
                    return True

        def is_in_ww_pose(sim_instance):
            if not cls.ww_installed:
                return False

            return ww_pose_handler.is_sim_in_pose_interaction(TurboSim(sim_instance))

        return is_in_posePlayer_pose(sim_instance) or is_in_ww_pose(sim_instance)


    @classmethod
    def send_sim_home(cls, sim):
        try:
            if isinstance(sim, sims.sim_info.SimInfo):
                sim_info = sim
                sim_instance = sim.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            elif isinstance(sim, sims.sim.Sim):
                sim_instance = sim
                sim_info = sim.sim_info
            else:
                logger.error(str(type(sim)) + " type was supplied for send_sim_back. Stack:" + str(traceback.format_stack()))
                return

            logger.info("Trying to send " + str(sim_info.first_name) + " " + str(sim_info.last_name) + " back home.")

            if sim_instance is not None:
                logger.info("Resetting sim.")
                sim_instance.reset(ResetReason.RESET_EXPECTED, None, "Trying to send home.")
                sim_instance.queue.unlock()

                cls.load_sim_into_home_zone(sim_instance)

                item = cls.get_teleported_item(sim)
                if item is not None:
                    cls.was_teleported.remove(item)

            else:
                logger.error("Instance of " + str(sim_info.first_name) + " " + str(sim_info.last_name) + " was not available. Either already left or was already sent home.")
        except:
            logger.error(str(traceback.format_exc()))

    @classmethod
    def add_to_add_wings_back(cls, sim_info):
        for si in cls.add_wings_back:
            if si.sim_id == sim_info.sim_id:
                return
        cls.add_wings_back.append(sim_info)

    @classmethod
    def clear_add_wings_back(cls):
        cls.add_wings_back = list()

    @classmethod
    def remove_add_wings_alarm(cls):
        if TsiGlobals.add_wings_back_alarm is None:
            return

        alarms.cancel_alarm(TsiGlobals.add_wings_back_alarm)
        TsiGlobals.add_wings_back_alarm = None

    @classmethod
    def add_wings(cls, handle):
        cls.remove_add_wings_alarm()
        run_fixup_fairy_wings(TsiGlobals.add_wings_back)
        TsiGlobals.clear_add_wings_back()


TsiGlobals.posePlayer_installed = False
try:
    from poseplayer import PoseInteraction as APP_PoseInteraction
    TsiGlobals.posePlayer_installed = True
except:
    pass

TsiGlobals.ww_installed = False
try:
    import wickedwhims.sex.features.poseplayer.pose_handler as ww_pose_handler
    from turbolib2.wrappers.sim.sim import TurboSim
    TsiGlobals.ww_installed = True
except:
    pass

TsiGlobals.has_update_with_faries = False
try:
    from carry.carry_elements import run_fixup_fairy_wings
    TsiGlobals.has_update_with_faries = True
except:
    pass