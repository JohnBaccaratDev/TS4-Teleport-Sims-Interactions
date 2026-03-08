
from event_testing.results import TestResult
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from interactions.utils.tunable_icon import TunableIconVariant
from sims4.tuning.tunable import Tunable
from sims4.tuning.tunable_base import GroupNames
from sims4.utils import flexmethod
from singletons import DEFAULT
from teleport_sims_interactions import TsiConfig


class TsiConfigBoolInteraction(ImmediateSuperInteraction):
    INSTANCE_TUNABLES = {
        'config_property_name': Tunable(description="Name of property in TsiConfig", tunable_type=str, default="", needs_tuning=True),
        'pie_menu_icon_enabled':TunableIconVariant(description='Icon when enabled', tuning_group=GroupNames.UI),
        'pie_menu_icon_disabled':TunableIconVariant(description='Icon when disabled', tuning_group=GroupNames.UI)
    }

    @classmethod
    def _test(cls, target, context, **kwargs):
        if not hasattr(TsiConfig, cls.config_property_name):
            raise Exception("Property " + cls.config_property_name + " does not exist in TsiConfig.")

        return TestResult.TRUE


    @flexmethod
    def get_pie_menu_icon_info(cls, inst, target=DEFAULT, context=DEFAULT, **interaction_parameters):
        inst_or_cls = inst if inst is not None else cls
        resolver = inst_or_cls.get_resolver(target=target, context=context)
        if getattr(TsiConfig, inst_or_cls.config_property_name):
            icon_info_data = inst_or_cls.pie_menu_icon_enabled(resolver)
        else:
            icon_info_data = inst_or_cls.pie_menu_icon_disabled(resolver)
        return icon_info_data


    def _trigger_interaction_start_event(self):
        setattr(TsiConfig, self.config_property_name, not getattr(TsiConfig, self.config_property_name))
        TsiConfig.write_config()