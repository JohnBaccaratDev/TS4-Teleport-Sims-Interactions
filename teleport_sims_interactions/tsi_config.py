import inspect

import os
import sims4


class TsiConfig():
    with sims4.reload.protected(globals()):
        _to_export = list()
        _reading_config = False

    class classproperty:
        def __init__(self, fget=None, fset=None):
            self.fget = fget
            self.fset = fset

        def __get__(self, instance, owner):
            if self.fget is None:
                raise AttributeError("unreadable attribute")
            return self.fget(owner)

        def __set__(self, instance, value):
            if self.fset is None:
                raise AttributeError("can't set attribute")
            return self.fset(type(instance) if instance else instance, value)

        def getter(self, func):
            return type(self)(func, self.fset)

        def setter(self, func):
            return type(self)(self.fget, func)

    _ground_dispersal = True
    _object_dispersal = False

    @classproperty
    def ground_dispersal(cls) -> bool:
        return cls._ground_dispersal
    @ground_dispersal.setter
    def ground_dispersal(cls, value):
        cls._ground_dispersal = value

    @classproperty
    def object_dispersal(cls) -> bool:
        return cls._object_dispersal
    @object_dispersal.setter
    def object_dispersal(cls, value):
        cls._object_dispersal = value


    # Don't ask me why this only returns the proper attributes the first time.
    @classmethod
    def get_to_export(cls):
        if len(cls._to_export) > 0:
            return

        for attr in dir(cls):
            raw_attr = inspect.getattr_static(cls, attr)
            if type(raw_attr).__name__ == "classproperty":
                cls._to_export.append(attr)

    @classmethod
    def get_config_path_folder(cls):
        path = os.path.abspath(__file__)
        while not os.path.isdir(path):
            path = os.path.dirname(path)

        return path

    @classmethod
    def get_config_path(cls):
        return os.path.join(cls.get_config_path_folder(), "JohnBaccarat_TeleportSimsInteractions.ini")

    @classmethod
    def read_config(cls):

        path = cls.get_config_path()

        if not os.path.isfile(path):
            cls.write_config()
            return

        cls._reading_config = True
        with open(cls.get_config_path(), "r") as config:
            for line in config:
                parts = line.split("=")
                if len(parts) > 1 and parts[0] in cls._to_export:
                    s = "=".join(parts[1:])
                    if isinstance(getattr(cls, parts[0]), bool):
                        v = s.lower().strip() in ("true", "1", "y", "yes")
                    else:
                        v = s
                    setattr(cls, parts[0], v)

        cls._reading_config = False


    @classmethod
    def write_config(cls):
        if cls._reading_config:
            return

        with open(cls.get_config_path(), "w") as config:
            for attr in cls._to_export:
                prop = getattr(cls, attr)
                config.writelines(["\n", str(attr) + "=" + str(prop)])
