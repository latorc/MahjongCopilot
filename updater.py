""" Updater class"""
import threading
import subprocess
import sys
import os
import shutil
import zipfile
from enum import Enum,auto
import requests
from common.utils import TEMP_FOLDER
import common.utils as utils
from common.log_helper import LOGGER

VERSION_FILE = "version"
UPDATE_FILE = "MahjongCopilot.zip"
UPDATE_FOLDER = "update"

""" how to release update:
- Use Pyinstaller to pack to executables.
- select main executable and files needed (like resources folder), zip into archive
- Upload to build_output folder
- Modify version file to reflect new version number"""

class UpdateStatus(Enum):
    NONE = 0
    CHECKING = auto()
    NO_UPDATE = auto()
    NEW_VERSION = auto()
    DOWNLOADING = auto()
    UNZIPPING = auto()
    OK = auto()
    ERROR = auto()
    
class Updater:
    """ handles version check and update"""
    def __init__(self, url:str):
        self.urlbase:str = url
        if not self.urlbase.endswith("/"):
            self.urlbase += "/"
        self.timeout_dl:int = 15
        # read version number from file "version"
        with open(utils.sub_file(".", VERSION_FILE), 'r', encoding='utf-8') as f:
            self.local_version = str(f.read()).strip()
        self.web_version:str = '0'
        self.dl_progress:str = ""               # downloaded percentage
        self.update_status:UpdateStatus = UpdateStatus.NONE
        self.update_exception:Exception = None

    def check_update(self):
        """ check for update in thread. update web version number"""
        def check_ver():
            self.update_status = UpdateStatus.CHECKING
            res = requests.get(self.urlbase + VERSION_FILE, timeout=5)
            self.web_version = res.text
            LOGGER.debug("Local version=%s, Web version=%s", self.local_version, self.web_version)
            if self.is_webversion_newer():
                self.update_status = UpdateStatus.NEW_VERSION
            else:
                self.update_status = UpdateStatus.NO_UPDATE
        
        t = threading.Thread(
            target=check_ver,
            name="Check_update",
            daemon=True
        )
        t.start()
    
    def is_webversion_newer(self) -> bool:
        """ check if web version is newer than local version"""
        # convert a.b.c to 000a000b000c
        try:
            if self.web_version:
                local_v_int = int(''.join(f"{part:0>4}" for part in self.local_version.split(".")))
                web_v_int = int(''.join(f"{part:0>4}" for part in self.web_version.split(".")))
                if web_v_int > local_v_int:
                    return True
        except:
            pass
        return False
        
    def download_file(self, fname:str) -> str:
        """ download file and update progress (blocking)
        returns:
            str: downloaded file path"""        
        save_file = utils.sub_file(TEMP_FOLDER, fname)
        with requests.get(self.urlbase + fname, stream=True, timeout=self.timeout_dl) as res:
            res.raise_for_status()
            total_length = int(res.headers.get('content-length', 0))
            downloaded = 0

            # write in chunks and update progress
            with open(save_file, 'wb') as file:
                for chunk in res.iter_content(chunk_size=8192):
                    file.write(chunk)
                    # update progress
                    downloaded += len(chunk)
                    pct = downloaded/total_length*100 if total_length > 0 else 0
                    self.dl_progress = f"{downloaded/1000/1000:.1f}/{total_length/1000/1000:.1f} MB ({pct:.1f}%)"
        return save_file
                    
    def unzip_file(self, fname:str) -> str:
        """ unzip file to its folder
        returns:
            str: extracted folder path
        """
        f_path = os.path.dirname(fname)
        extract_path = utils.sub_folder(f_path) / UPDATE_FOLDER
        if extract_path.exists():
            shutil.rmtree(extract_path)
        with zipfile.ZipFile(fname, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        return str(extract_path)
                        
    def prepare_update(self):
        """ Prepare update in thread: download and unzip file"""
        if sys.platform == "win32":     # check system support
            pass
        else:
            self.update_status = UpdateStatus.ERROR
            self.update_exception = RuntimeError("Update only supports Windows for now.")
            return
        
        def update_task():
            try:
                self.update_status = UpdateStatus.DOWNLOADING
                fname = self.download_file(UPDATE_FILE)
                self.update_status = UpdateStatus.UNZIPPING
                self.unzip_file(fname)
                # self.start_update()
                self.update_status = UpdateStatus.OK
            except Exception as e:
                self.update_exception = e
                self.update_status = UpdateStatus.ERROR
            
        t = threading.Thread(
            target=update_task,
            name="UpdateThread",
            daemon=True
        )
        t.start()
        
    def start_update(self):
        """ start update"""
        
        if sys.platform == "win32":
            exec_path = sys.executable
            exec_name = os.path.basename(exec_path)
            root_folder = str(utils.sub_folder("."))
            update_folder = str(utils.sub_folder(TEMP_FOLDER)/UPDATE_FOLDER)
            cmd = f"""
            @echo off
            echo Updating {exec_name} in 5 seconds...
            timeout /t 5
            echo Killing program {exec_name}...
            taskkill /IM {exec_name} /F
            timeout /t 3
            echo copying new file...
            set "sourceDir={update_folder}\*"
            set "destDir={root_folder}"
            xcopy %sourceDir% %destDir% /s /e /y
            echo Update completed. Restarting {exec_name} in 3...
            start {exec_name}
            """
            # save it to a batchfile
            batch_file = utils.sub_file(TEMP_FOLDER, "update.bat")
            with open(batch_file, "w", encoding="utf-8") as f:
                f.write(cmd)
            subprocess.Popen(
                ['cmd.exe', '/c', batch_file],
                creationflags=subprocess.CREATE_NEW_CONSOLE)
            sys.exit(0)

        elif sys.platform == "darwin":
            exec_name = os.path.basename(sys.executable)
            root_folder = str(utils.sub_folder("."))
            update_folder = str(utils.sub_folder(TEMP_FOLDER)/UPDATE_FOLDER)
            cmd = f"""
            #!/bin/bash
            echo "Updating {exec_name} in 5 seconds..."
            sleep 5
            echo "Killing program {exec_name}..."
            pkill -f {exec_name}
            sleep 3
            echo "Copying..."
            cp -R "{update_folder}/"* "{root_folder}/"
            echo "Update completed. Restarting {exec_name}..."
            open "{root_folder}/{exec_name}"
            """
            # Save it to a shell script
            script_file = utils.sub_file(TEMP_FOLDER, "update.sh")
            with open(script_file, "w", encoding='utf-8') as f:
                f.write(cmd)
            os.chmod(script_file, 0o755)  # Make the script executable
            
            # Execute the script in a new Terminal window
            subprocess.Popen(["open", "-a", "Terminal.app", script_file])
            
        else:
            # not supported
            pass
