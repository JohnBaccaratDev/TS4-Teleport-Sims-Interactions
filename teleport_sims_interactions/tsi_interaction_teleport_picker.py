from interactions.base.picker_interaction import SimPickerInteraction
from teleport_sims_interactions.tsi_interaction_teleport_base import TsiTeleportBase


class TsiTeleportPicker(SimPickerInteraction, TsiTeleportBase):

    def _on_successful_picker_selection(self, results=()):
        self.start_teleport(results)