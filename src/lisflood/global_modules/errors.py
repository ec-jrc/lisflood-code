import sys
import os


class LisfloodError(Exception):
    """
    the error handling class
    prints out an error
    """

    def __init__(self, msg):
        header = "\n\n ========================== LISFLOOD ERROR =============================\n"
        try:
            self._msg = header + msg + "\n" + sys.exc_info()[1].message
        except (IndexError, AttributeError):
            self._msg = header + msg + "\n"

    def __str__(self):
        return self._msg


class LisfloodFileError(LisfloodError):
    """
    the error handling class
    prints out an error
    """

    def __init__(self, filename, msg=""):
        path, name = os.path.split(filename)
        path = os.path.normpath(path)
        if os.path.exists(path):
            text1 = "path: " + path + " exists\nbut filename: " + name + " does not\n"
            text1 += "file name extension can be .map or .nc\n"
        else:
            text1 = "searching: " + filename
            text1 += "\npath: " + path + " does not exists\n"

        header = "\n\n ======================== LISFLOOD FILE ERROR ===========================\n"
        self._msg = header + msg + text1


class LisfloodWarning(Warning):
    """
    the error handling class
    prints out an error
    """

    def __init__(self, msg):
        header = "\n\n ========================== LISFLOOD Warning =============================\n"
        self._msg = header + msg

    def __str__(self):
        return self._msg


class LisfloodRunInfo(Warning):
    """
    the error handling class
    prints out an error
    """

    def __init__(self, mode, outputDir, Steps=1, ensMembers=1, Cores=1):
        header = "\n\n ========================== LISFLOOD Simulation Information and Setting =============================\n"
        msg = "   LISFLOOD is used in the " + str(mode) + "\n"
        if ensMembers > 1:
            msg += "   It uses " + str(ensMembers) + " ensemble members for the simulation\n"
        if Steps > 1:
            msg += "   The model will be updated at " + str(Steps) + " time step during the simulation\n"
        if Cores > 1:
            msg += "   The simulation will try to use " + str(Cores) + " processors simultaneous\n"
        msg += "   The simulation output as specified in the settings file can be found in " + str(outputDir) + "\n"
        self._msg = header + msg

    def __str__(self):
        return self._msg
