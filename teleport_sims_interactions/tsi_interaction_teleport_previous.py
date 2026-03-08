from event_testing.results import TestResult
from teleport_sims_interactions import TsiGlobals
from teleport_sims_interactions.tsi_interaction_teleport_base import TsiTeleportBase


class TsiTeleportPrevious(TsiTeleportBase):

    @classmethod
    def _test(cls, target, context, **kwargs):
        if len(TsiGlobals.previous_teleported) > 0:
            return TestResult.TRUE

        return TestResult(False, "Noone was previously teleported.")


    def _trigger_interaction_start_event(self):
        self.set_original_location()
        self.start_teleport(TsiGlobals.previous_teleported)