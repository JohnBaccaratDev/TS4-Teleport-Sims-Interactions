import os
import shutil
import py_compile
import zipfile
import ___manifest as mf

# Copy all files to a build directory and compile if needed
def copyToBuildDirAndCompile(currDir, baseDir, buildDir, debug):
    for item in os.listdir(currDir):
        if item.startswith("___") or item.startswith(".") or (not debug and item.lower().startswith("debug")):
            continue
        path = os.path.join(currDir, item)

        if os.path.isdir(path):
            copyToBuildDirAndCompile(path, baseDir, buildDir, debug)
        else:
            if currDir == baseDir:
                copyToFolder = buildDir
            else:
                copyToFolder = os.path.join(buildDir, currDir.replace(baseDir + os.path.sep, ""))

            if not os.path.exists(copyToFolder):
                os.makedirs(copyToFolder)

            curr_file = os.path.join(currDir,item)
            copy_to_file = os.path.join(copyToFolder, item)
            shutil.copyfile(curr_file, copy_to_file)
            if not debug and copy_to_file.endswith(".py"):
                py_compile.compile(copy_to_file, cfile=(copy_to_file+"c"), dfile=(path.replace(baseDir, mf.project_name + " " + mf.project_version)))
                os.remove(copy_to_file)


def createEmptyInitPycFiles(currDir, baseDir):
    hasInitFile = False
    needsInitFile = False

    for item in os.listdir(currDir):

        path = os.path.join(currDir, item)
        if os.path.isdir(path):
            createEmptyInitPycFiles(path, baseDir)

        if item == "__init__.pyc":
            hasInitFile = True
        elif item.endswith(".pyc"):
            needsInitFile = True

    if needsInitFile and not hasInitFile:
        initFile = os.path.join(currDir, "__init__.py")
        open(initFile, "a").close()
        py_compile.compile(initFile, cfile=(initFile + "c"), dfile=(initFile.replace(baseDir, mf.project_name + " " + mf.project_version)))
        os.remove(initFile)


def createZip(file, currDir, baseDir):

    for item in os.listdir(currDir):
        path_on_os = os.path.join(currDir, item)
        path_in_zip = os.path.join(currDir, item).replace(baseDir + os.path.sep, "")
        if os.path.isdir(path_on_os):
            file.writestr(path_in_zip + "/", "")
            createZip(file, path_on_os, baseDir)
        else:
            file.write(path_on_os, path_in_zip, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)