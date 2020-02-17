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
            self._msg = '{}{}\n{}'.format(header, msg, sys.exc_info()[1].message)
        except (IndexError, AttributeError):
            self._msg = self._msg = '{}{}\n'.format(header, msg)

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
            text1 = "path: {} exists\nbut filename: {} does not\nfile name extension can be .map or .nc\n".format(path, name)
        else:
            text1 = "searching: {}\npath: {} does not exists\n".format(filename, path)

        header = "======================== LISFLOOD FILE ERROR ==========================="
        self._msg = '\n\n {}\n{}{}'.format(header, msg, text1)


class LisfloodWarning(UserWarning):
    """
    the error handling class
    prints out an error
    """

    def __init__(self, msg):
        header = "========================== LISFLOOD Warning ============================="
        self._msg = '\n\n {}\n{}'.format(header, msg)

    def __str__(self):
        return self._msg
