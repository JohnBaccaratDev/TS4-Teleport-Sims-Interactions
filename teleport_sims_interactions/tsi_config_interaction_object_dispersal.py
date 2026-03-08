from event_testing.results import TestResult
from teleport_sims_interactions.tsi_config_bool_interaction import TsiConfigBoolInteraction
from teleport_sims_interactions.tsi_interaction_mixin import TsiInteractionMixin


class TsiConfigInteractionObjectDispersal(TsiConfigBoolInteraction, TsiInteractionMixin):

    @classmethod
    def _test(cls, target, context, **kwargs):
        if not cls.has_ground_interactions(target):
            return TestResult.TRUE

        return TestResult(False, "Interaction is only for objects/sims.")
