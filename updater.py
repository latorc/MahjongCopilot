""" Updater class"""
import threading
import time
import sys
import os
import shutil
from enum import Enum
import requests
import zipfile
from utils import VER_NUMBER, TEMP_FOLDER
import utils
from log_helper import LOGGER

URL_BASE = "https://maco.clandoom.com/build_output/"
VERSION_FILE = "version"
UPDATE_FILE = "MahjongCopilot.zip"
UPDATE_FOLDER = "update"


class UpdateStatus(Enum):
    NONE = 0
    DOWNLOADING = 1
    UNZIPPING = 2
    OK = 3
    ERROR = -1
    
class Updater:
    """ handles version check and update"""
    def __init__(self):
        self.timeout_dl:int = 15
        self.web_version:str = None
        self.dl_perc:float = 0               # downloaded percentage
        self.update_status:UpdateStatus = UpdateStatus.NONE
        self.update_exception:Exception = None
        self.check_update()

    def check_update(self):
        """ check for update in thread. update web version number"""
        def check_ver():
            res = requests.get(URL_BASE + VERSION_FILE, timeout=5)
            self.web_version = res.text
        
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
            
    def start_update(self):
        """ generate update script"""
        
        if sys.platform == "win32":
            exec_path = sys.executable
            exec_name = os.path.basename(exec_path)
            cmd = f"""
@echo off
echo "Updating {exec_name} in 5 seconds..."
timeout /t 5
echo "killing program {exec_name}..."
taskkill /IM {exec_name} /F
timeout /t 3
set "sourceDir=.\{UPDATE_FOLDER}\*"
set "destDir=.."
xcopy %sourceDir% %destDir% /s /e /y

copy /Y MahjongCopilot.exe ..\
echo "Update completed. Restarting MahjongCopilot..."
cd ..
MahjongCopilot.exe
pause
"""
        elif sys.platform == "darwin":
            pass
            
        else:
            # not supported
            pass
        
        
                        
    def prepare_update(self):
        """ Prepare update in thread"""
        
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
    
    
if __name__ == "__main__":
    test_update()