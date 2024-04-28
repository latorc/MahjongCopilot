""" Import libriichi3p module """
import sys
import os
import platform
import importlib.util
from common.utils import sub_file

assert (3,10)<=sys.version_info[:2] <= (3,12), "Python version must be between 3.10 and 3.12"

def load_module():
    """ Determine system specifics and load the appropriate module file"""
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"

    if platform.processor() == "arm":
        proc_str = "aarch64"
    else:
        proc_str = "x86_64"

    if platform.system() == "Windows":
        os_ext_str = "pc-windows-msvc.pyd"
    elif platform.system() == "Darwin":
        os_ext_str = "apple-darwin.so"
    elif platform.system() == "Linux":
        os_ext_str = "unknown-linux-gnu.so"
    else:
        raise EnvironmentError(f"Unsupported OS: {platform.system()}")

    # Adjust the path to the directory where the .pyd file is stored
    filename = f"libriichi3p-{python_version}-{proc_str}-{os_ext_str}"
    file_path = sub_file("libriichi3p", filename)
    if not os.path.exists(file_path):
        raise ImportError(f"Could not find file: {file_path}")
    
    # Attempt to load the .pyd file
    spec = importlib.util.spec_from_file_location("libriichi3p", file_path)
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    else:
        raise ImportError(f"Could not import: {file_path}")
    
libriichi3p = load_module()

