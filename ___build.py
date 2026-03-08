from pathlib import Path
from zipfile import ZipFile
from ___build_functions import *
import sys

debug = "-d" in sys.argv
base_dir: str = os.path.dirname(os.path.realpath(__file__))
ts4_mods_dir = os.path.join(Path.home(), "Documents", "Electronic Arts", "The Sims 4", "Mods")
debug_dir = os.path.join(ts4_mods_dir, mf.project_name)
build_dir = os.path.join(base_dir, ".temp_to_build")

if not os.path.exists(build_dir):
    os.mkdir(build_dir)

# Copy the files to a build directory and compile
copyToBuildDirAndCompile(base_dir, base_dir, build_dir, debug)
# Create __init__.pyc files where needed
createEmptyInitPycFiles(build_dir, build_dir)

ts4script_file_path = os.path.join(ts4_mods_dir, mf.project_author.replace(" ", "") + "_" + mf.project_name.replace(" ", "") + ".ts4script")
if not debug:
    print("Outputting .ts4script")
    # Create zip file (.ts4script files are just that)
    zFile = ZipFile(ts4script_file_path, mode="w")
    # Add the files from the build directory to the zip file
    createZip(zFile, build_dir, build_dir)
    zFile.close()

    # Remove build directory
    shutil.rmtree(build_dir)
    # Remove debug dir
    if os.path.exists(debug_dir):
        shutil.rmtree(debug_dir)
else:
    print("Outputting for Debug")
    if os.path.isfile(ts4script_file_path):
        os.remove(ts4script_file_path)

    if os.path.exists(debug_dir):
        shutil.rmtree(debug_dir)

    debug_dir = os.path.join(debug_dir, "Scripts")
    shutil.move(build_dir, debug_dir)