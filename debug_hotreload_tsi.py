import traceback
import os
import sims4.commands, sims4.reload

@sims4.commands.Command('reload_tsi', command_type=sims4.commands.CommandType.Live)
def reload_submodules(_connection=None):
    output = sims4.commands.CheatOutput(_connection)
    output('reloading')

    base_dir: str = os.path.dirname(os.path.realpath(__file__))
    try:
        for root, dirs, files in os.walk(base_dir):
            for file in files:
                if file.endswith(".py"):
                    if os.path.join(root, file) != __file__:
                        short_path = os.path.join(root, file).split("Mods")[1]
                        output(short_path)
                        sims4.reload.reload_file(os.path.join(root, file))
    except:
        output(traceback.format_exc())