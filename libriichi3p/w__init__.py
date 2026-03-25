import sys
import platform

assert sys.version_info >= (3, 10), f"Python version must be 3.10 or higher"
assert sys.version_info <= (3, 12), f"Python version must be 3.12 or lower"

if platform.system() == "Windows":
    if sys.version_info[1] == 10:
        from .libriichi310x8664pcwindowsmsvc import *
    elif sys.version_info[1] == 11:
        from .libriichi311x8664pcwindowsmsvc import *
    elif sys.version_info[1] == 12:
        from .libriichi312x8664pcwindowsmsvc import *
    else:
        raise Exception("Not supported Python version on Windows")
elif platform.system() == "Darwin":
    if platform.processor() == "arm":
        if sys.version_info[1] == 10:
            from .libriichi310aarch64appledarwin import *
        elif sys.version_info[1] == 11:
            from .libriichi311aarch64appledarwin import *
        elif sys.version_info[1] == 12:
            from .libriichi312aarch64appledarwin import *
        else:
            raise Exception("Not supported Python version on macOS")
    else:
        if sys.version_info[1] == 10:
            from .libriichi310x8664appledarwin import *
        elif sys.version_info[1] == 11:
            from .libriichi311x8664appledarwin import *
        elif sys.version_info[1] == 12:
            from .libriichi312x8664appledarwin import *
        else:
            raise Exception("Not supported Python version on macOS")
elif platform.system() == "Linux":
    if sys.version_info[1] == 10:
        from .libriichi310x8664unknownlinuxgnu import *
    elif sys.version_info[1] == 11:
        from .libriichi311x8664unknownlinuxgnu import *
    elif sys.version_info[1] == 12:
        from .libriichi312x8664unknownlinuxgnu import *
    else:
        raise Exception("Not supported Python version on Linux")
    