from event_testing.results import TestResult
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from teleport_sims_interactions.tsi_globals import TsiGlobals


class TsiSendBackAll(ImmediateSuperInteraction):

    @classmethod
    def _test(cls, target, context, **kwargs):
        if not TsiGlobals.any_not_send_back():
            return TestResult(False, "No sim left to send back.")

        return super()._test(target, context)

    def _trigger_interaction_start_event(cls):
        if TsiGlobals.any_not_send_back():
            while len(TsiGlobals.was_teleported) > 0:
                TsiGlobals.send_sim_home(TsiGlobals.was_teleported[-1].sim_info)
