from interactions.base.immediate_interaction import ImmediateSuperInteraction
from teleport_sims_interactions.tsi_globals import TsiGlobals


class TsiSendBackForce(ImmediateSuperInteraction):

    def _trigger_interaction_start_event(cls):
        TsiGlobals.send_sim_home(cls.target)
