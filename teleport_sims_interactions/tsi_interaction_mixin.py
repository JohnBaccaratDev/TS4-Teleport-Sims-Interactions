from objects.decorative.rug import Rug
from objects.terrain import TerrainPoint


class TsiInteractionMixin:

    @classmethod
    def has_ground_interactions(cls, obj):
        if hasattr(obj, "__qualname__") and obj.__qualname__ in ("object_terrain", "object_rug"):
            return True

        if hasattr(obj, "provides_terrain_interactions") and obj.provides_terrain_interactions:
            return True

        if isinstance(obj, (TerrainPoint, Rug)):
            return True

        return False