""" Common/utility methods
no logging in this file because logging might not have been initialized yet
"""

from enum import Enum, auto
import pathlib
import sys
import ctypes
import time
import subprocess
import threading
import random
import string
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
import requests

from .lan_str import LanStr

# Constants
WEBSITE = "https://mjcopilot.com"

MAJSOUL_DOMAINS = [
    "maj-soul.com",     # China
    "majsoul.com",      # old?
    "mahjongsoul.com",  # Japan
    "yo-star.com"       # English
]

class Folder:
    """ Folder name consts"""
    MODEL = "models"
    BROWSER_DATA = "browser_data"
    RES = 'resources'
    LOG = 'log'
    MITM_CONF = 'mitm_config'
    PROXINJECT = 'proxinject'
    UPDATE = "update"
    TEMP = 'temp'
    CHROME_EXT = 'chrome_ext'


class GameClientType(Enum):
    """ Game client type"""
    PLAYWRIGHT = auto()     # playwright browser
    PROXY = auto()          # other client through mitm proxy


class GameMode(Enum):
    """ Game Modes for bots/models"""
    MJ4P = "4P"
    MJ3P = "3P"


# for automation
GAME_MODES = ['4E', '4S', '3E', '3S']


class UiState(Enum):
    """ UI State for the game"""
    NOT_RUNNING = 0
    MAIN_MENU = 1
    IN_GAME = 10
    GAME_ENDING = 20


# === Exceptions ===    
class LocalModelException(Exception):
    """ Exception for model file error"""

class MITMException(Exception):
    """ Exception for MITM error"""

class MitmCertNotInstalled(Exception):
    """ mitm certificate not installed"""
    
class BotNotSupportingMode(Exception):
    """ Bot not supporting current mode"""
    def __init__(self, mode:GameMode):
        super().__init__(mode)


def error_to_str(error:Exception, lan:LanStr) -> str:
    """ Convert error to language specific string"""
    if isinstance(error, LocalModelException):
        return lan.LOCAL_MODEL_ERROR
    elif isinstance(error, MitmCertNotInstalled):
        return lan.MITM_CERT_NOT_INSTALLED + f"{error.args}"    
    elif isinstance(error, MITMException):
        return lan.MITM_SERVER_ERROR    
    elif isinstance(error, BotNotSupportingMode):
        return lan.MODEL_NOT_SUPPORT_MODE_ERROR + f' {error.args[0].value}'
    elif isinstance(error, requests.exceptions.ConnectionError):
        return lan.CONNECTION_ERROR + f': {error}'
    elif isinstance(error, requests.exceptions.ReadTimeout):
        return lan.CONNECTION_ERROR + f': {error}'
    else:
        return str(error)


def sub_folder(folder_name:str) -> pathlib.Path:
    """ return the subfolder Path, create it if not exists"""
    try:
        # In frozen app, keep read-only assets relative to executable (Contents/MacOS).
        # In source runs, keep legacy behavior (project current directory).
        if getattr(sys, "frozen", False):
            app_base = pathlib.Path(sys.executable).resolve().parent
        else:
            app_base = pathlib.Path(".").resolve()
        if sys.platform == "darwin":
            mac_data_base = pathlib.Path.home() / "Library" / "Application Support" / "mortal_mac_v0.2"
            writable_folders = {
                Folder.MODEL,
                Folder.BROWSER_DATA,
                Folder.LOG,
                Folder.MITM_CONF,
                Folder.PROXINJECT,
                Folder.UPDATE,
                Folder.TEMP,
                Folder.CHROME_EXT,
            }
            base_path = mac_data_base if folder_name in writable_folders else app_base
        else:
            base_path = app_base
    except Exception:  #pylint: disable=broad-except
        base_path = pathlib.Path('.').resolve()

    if folder_name in (".", ""):
        subfolder = base_path
    else:
        subfolder = base_path / folder_name
    if not subfolder.exists():
        subfolder.mkdir(parents=True, exist_ok=True)
    return subfolder.resolve()


def sub_file(folder:str, file:str) -> str:
    """ return the file absolute path string, given folder and filename, create the folder if not exists"""
    subfolder = sub_folder(folder)
    file_str = str((subfolder / file).resolve())
    return file_str


def wait_for_file(file:str, timeout:int=5) -> bool:
    """ Wait for file creation (blocking until the file exists) for {timeout} seconds
    returns:
        bool: True if file exists within timeout, False otherwise
    """
    # keep checking if the file exists until timeout
    start_time = time.time()
    while not pathlib.Path(file).exists():
        if time.time() - start_time > timeout:
            return False
        time.sleep(0.5)
    return True


def sub_run_args() -> dict:
    """ return **args for subprocess.run"""
    args = {
        'capture_output':True,
        'text': True,
        'check': False,
    }
    if sys.platform == "win32":
        startup_info = subprocess.STARTUPINFO()
        startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup_info.wShowWindow = subprocess.SW_HIDE
        args['startupinfo'] = startup_info
    return args


def get_cert_serial_number(cert_file:str) ->str:
    """Extract the serial number as a hexadecimal string from a certificate."""
    with open(cert_file, 'rb') as file:
        cert_data = file.read()
    cert = x509.load_pem_x509_certificate(cert_data, default_backend())
    # Convert serial number to hex, remove leading zeroes for consistent comparison
    hex_serial = format(cert.serial_number, 'X').lstrip("0")
    return hex_serial


def get_cert_sha1_fingerprint(cert_file:str) -> str:
    """Extract certificate SHA1 fingerprint as uppercase hex string."""
    with open(cert_file, 'rb') as file:
        cert_data = file.read()
    cert = x509.load_pem_x509_certificate(cert_data, default_backend())
    return cert.fingerprint(hashes.SHA1()).hex().upper()


def is_certificate_installed(cert_file:str) -> tuple[bool, str]:
    """Check if the given certificate is installed in the system certificate store.
    Returns:
        (bool, str): True if the certificate is found in the system store, str is the stdout"""
    try:
        if sys.platform == "win32":
            serial_number = get_cert_serial_number(cert_file)
            # Use certutil to look up the certificate by its serial number in the Root store
            cmd = ['certutil', '-store', 'Root', serial_number]
            result = subprocess.run(cmd, **sub_run_args())    #pylint:disable=subprocess-run-check
            output = result.stdout + result.stderr
            if result.returncode == 0 and serial_number.upper() in output.upper():
                return True, output
            return False, output
        elif sys.platform == "darwin":
            cert_sha1 = get_cert_sha1_fingerprint(cert_file)
            keychains = [
                pathlib.Path('/Library/Keychains/System.keychain'),
                pathlib.Path.home() / 'Library' / 'Keychains' / 'login.keychain-db',
                pathlib.Path.home() / 'Library' / 'Keychains' / 'login.keychain',
            ]
            outputs = []
            for keychain in keychains:
                if not keychain.exists():
                    continue
                cmd = ['security', 'find-certificate', '-a', '-Z', str(keychain)]
                result = subprocess.run(cmd, **sub_run_args())    #pylint:disable=subprocess-run-check
                output = f"keychain={keychain}\n{result.stdout}{result.stderr}"
                outputs.append(output)
                if result.returncode == 0 and cert_sha1 in result.stdout.upper():
                    return True, output
            if outputs:
                return False, "\n".join(outputs)
            return False, "No keychain found for certificate lookup"
        else:   # unsupported platform
            return False, f"Unsupported platform: {sys.platform}"
    except subprocess.SubprocessError as e:
        # error occured while running the command
        return False, str(e)
    except Exception as e:
        return False, str(e)
    

def install_root_cert(cert_file:str):
    """ Install Root certificate onto the system
    params:
        cert_file(str): certificate file to be installed
    Returns:
        (bool, str): True if the certificate is installed successfully, str is the stdout
    """
    # Install cert. If the cert exists, system will skip installation
    if sys.platform == "win32":
        print(f'"{cert_file}"')
        full_command = ["certutil","-addstore","Root",cert_file]
        # full_command = [
        #     'powershell', '-Command', 
        #     f"Start-Process 'certutil' -ArgumentList '-addstore', 'Root', '{cert_file}' -Wait -Verb 'RunAs';"
        #     f"exit $LASTEXITCODE"
        # ]
        p=subprocess.run(full_command, **sub_run_args())
        stdout, stderr = p.stdout, p.stderr
    elif sys.platform == "darwin":
        login_keychain = pathlib.Path.home() / 'Library' / 'Keychains' / 'login.keychain-db'
        if not login_keychain.exists():
            login_keychain = pathlib.Path.home() / 'Library' / 'Keychains' / 'login.keychain'
        cmd = ['security', 'add-trusted-cert', '-d', '-r', 'trustRoot', '-k', str(login_keychain), cert_file]
        p = subprocess.run(cmd, **sub_run_args())
        stdout, stderr = p.stdout, p.stderr
    else:
        print("Unknown Platform. Please manually install MITM certificate:", cert_file)
        return False, ""
    
    # Check if successful
    text = f"{stdout}\n{stderr}"
    if p.returncode == 0:  # success     
        return True, text
    else:   # error        
        return False, text

    
def list_children(folder:str, full_path:bool=False, incl_file:bool=True, incl_dir:bool=False) -> list[pathlib.Path]:
    """ return the list of children in the folder 
    params:
        folder(str): name of the folder
        full_path(bool): True to return the full path, while False to return only the file name
        incl_file(bool): True to include files in the list
        incl_dir(bool): True to include directories in the list"""
    try:
        def to_include(f:pathlib.Path) -> bool:
            return (incl_file and f.is_file()) or (incl_dir and f.is_dir())
        target = pathlib.Path(folder)
        if not target.exists() and not target.is_absolute():
            target = sub_folder(folder)
        files = [f for f in target.iterdir() if to_include(f)]
        files.sort(key=lambda x: x.name.lower())
        if full_path:
            return [str(f.resolve()) for f in files]
        else:
            return [f.name for f in files]
    except: #pylint:disable=bare-except
        return []

    
def random_str(length:int) -> str:
    """ Generate random string with specified length"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def set_dpi_awareness():
    """ Set DPI Awareness """
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # for Windows 8.1 and later
        except AttributeError:
            ctypes.windll.user32.SetProcessDPIAware()       # for Windows Vista and later
        except: #pylint:disable=bare-except
            pass
        

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002      
def prevent_sleep():
    """ prevent system going into sleep/screen saver"""
    if sys.platform == "win32":        
        ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | 
            ES_SYSTEM_REQUIRED | 
            ES_DISPLAY_REQUIRED
        )
        
        
class FPSCounter:
    """Class for counting frames and calculating fps."""
    
    def __init__(self):
        self.lock = threading.Lock()
        self.timestamps = []  # List to hold timestamps of frame calls
        self.last_calc_time = time.time()  # Last time fps was calculated
        self.last_fps = 0  # Last calculated fps value
        
    def frame(self):
        """Indicates that a frame has been rendered or processed. Adds the current time to timestamps."""
        with self.lock:
            self.timestamps.append(time.time())

    def reset(self):
        """Resets the counter by clearing all recorded timestamps."""
        with self.lock:
            self.timestamps.clear()
        
    @property
    def fps(self):
        """Returns the current frames per second, calculated as the number of frames in the past second."""
        if time.time() - self.last_calc_time < 0.5:
            return self.last_fps
        with self.lock:
            # Filter out timestamps that are older than 1 second from the current time
            cur_time = time.time()
            self.timestamps = [t for t in self.timestamps if cur_time - t < 1]
            self.last_fps = len(self.timestamps)
            self.last_calc_time = cur_time
            return self.last_fps
            
