""" Updater class"""
import threading
import subprocess
import time
import sys
import os
import shutil
import zipfile
from enum import Enum,auto
import requests
from utils import VER_NUMBER, TEMP_FOLDER
import utils

URL_BASE = "https://mjcopilot.com/update/"
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
    def __init__(self):
        self.timeout_dl:int = 15
        self.web_version:str = '0'
        self.dl_perc:float = 0               # downloaded percentage
        self.update_status:UpdateStatus = UpdateStatus.NONE
        self.update_exception:Exception = None

    def check_update(self):
        """ check for update in thread. update web version number"""
        def check_ver():
            self.update_status = UpdateStatus.CHECKING
            res = requests.get(URL_BASE + VERSION_FILE, timeout=5)
            self.web_version = res.text
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
        if self.web_version:
            local_v_int = int(''.join(f"{part:0>4}" for part in VER_NUMBER.split(".")))
            web_v_int = int(''.join(f"{part:0>4}" for part in self.web_version.split(".")))
            if web_v_int > local_v_int:
                return True
        return False
        
    def download_file(self, fname:str) -> str:
        """ download file and update progress (blocking)
        returns:
            str: downloaded file path"""        
        save_file = utils.sub_file(TEMP_FOLDER, fname)
        with requests.get(URL_BASE + fname, stream=True, timeout=self.timeout_dl) as res:
            res.raise_for_status()
            total_length = int(res.headers.get('content-length', 0))
            downloaded = 0

            # write in chunks and update progress
            with open(save_file, 'wb') as file:
                for chunk in res.iter_content(chunk_size=8192):
                    file.write(chunk)
                    # update progress
                    downloaded += len(chunk)
                    self.dl_perc = (downloaded / total_length) * 100
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
            with open(script_file, "w") as f:
                f.write(cmd)
            os.chmod(script_file, 0o755)  # Make the script executable
            
            # Execute the script in a new Terminal window
            subprocess.Popen(["open", "-a", "Terminal.app", script_file])
            
        else:
            # not supported
            pass


def test_update():
    ud = Updater()
    ud.check_update()
    for _ in range(10):
        if ud.web_version:
            break
        time.sleep(1)
    if ud.is_webversion_newer():
        print(f"New version {ud.web_version} (Local version {VER_NUMBER})")
    else:
        print(f"No new version {ud.web_version} (Local version {VER_NUMBER})")
            
    ud.prepare_update()
    while ud.update_status != UpdateStatus.OK:
        if ud.update_status == UpdateStatus.ERROR:
            print("ERROR: ", ud.update_exception)
            break
        elif ud.update_status == UpdateStatus.DOWNLOADING:
            print(f"download progress: {ud.dl_perc:.1f}%")
        elif ud.update_status == UpdateStatus.UNZIPPING:
            print("unzipping")
        time.sleep(0.5)
        
    print("prepared")
    ud.start_update()
    
    
if __name__ == "__main__":
    test_update()