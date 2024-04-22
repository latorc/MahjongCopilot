""" Updater class for getting update info from website and update the main program"""
import threading
import subprocess
import sys
import os
import re
import shutil
import zipfile
from enum import Enum,auto
import requests

from common.utils import Folder, WEBSITE
import common.utils as utils
from common.log_helper import LOGGER

VERSION_FILE = "version"
UPDATE_FILE = "MahjongCopilot.zip"
HELP_PATH = r"/help"

""" how to release update:
- Use Pyinstaller to pack to executables.
- select main executable and files needed (like resources folder), zip into archive
- Upload zip and version file to website update folder
"""

class UpdateStatus(Enum):
    """ Update status enum"""
    NONE = 0
    CHECKING = auto()
    NO_UPDATE = auto()
    NEW_VERSION = auto()
    DOWNLOADING = auto()
    UNZIPPING = auto()
    PREPARED = auto()           # update download/unzipped and ready to apply
    ERROR = auto()

    
class Updater:
    """ handles version check and update"""
    def __init__(self, update_url:str):
        self.urlbase:str = update_url
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
        
        self.help_html:str = None       # help html text from web
        self.help_exception:Exception = None
        
    
    def load_help(self):
        """ update html in thread"""
        def task_update():
            url = WEBSITE + HELP_PATH
            LOGGER.info("Loading help html from %s", url)
            html_text = self.get_html(url)
            if html_text is None:
                self.help_html = f"""Help Information: <a href="{url}">{url}</a><br>Error loading help.<br>{self.help_exception}"""
                LOGGER.warning(self.help_html)
            else:
                self.help_html = html_text
                LOGGER.info("Finished loading help html")
                
        threading.Thread(
            name="UpdateHTML",
            target=task_update,
            daemon=True
        ).start()
        
    
    def get_html(self, url:str) -> str:
        """ get html text from url, and process it"""
        try:
            self.help_exception = None        
            response = requests.get(url, timeout=15) # Send a GET request to the URL
            # Check if the request was successful (HTTP status code 200)
            if response.status_code != 200:
                response.raise_for_status()
            
            # process text: remove/replace some tags
            res_text = response.text
            rm_patterns = [
                r'<script[^>]*>.*?</script>',
                r'<meta[^>]*>',
                r'<title[^>]*>.*?</title>',
                r'<link[^>]*>',
                r'<img[^>]*>',
                r'<nav[^>]*>',
            ]   # patterns to remove
            for p in rm_patterns:
                res_text = re.sub(p, '', res_text, flags=re.DOTALL)
            rep_patterns = {
                r'<code[^>]*>(.*?)</code>': lambda m: f'<i>{m.group(1)}</i>',
            }
            for p, r in rep_patterns.items():
                res_text = re.sub(p, r, res_text, flags=re.DOTALL)            
            return res_text
                
        except Exception as e:
            self.help_exception = e
            return None
    
    
    def check_update(self):
        """ check for update in thread. update web version number"""
        def check_ver():
            try:
                self.update_status = UpdateStatus.CHECKING
                res = requests.get(self.urlbase + VERSION_FILE, timeout=5)
                self.web_version = res.text
                LOGGER.debug("Check update: Local version=%s, Web version=%s", self.local_version, self.web_version)
                if self.is_webversion_newer():
                    self.update_status = UpdateStatus.NEW_VERSION
                else:
                    self.update_status = UpdateStatus.NO_UPDATE
            except Exception as e:
                self.update_exception = e
                self.update_status = UpdateStatus.ERROR
                LOGGER.error(e)
        
        t = threading.Thread(
            target=check_ver,
            name="Check_update",
            daemon=True
        )
        t.start()
        
    
    def is_webversion_newer(self) -> bool:
        """ check if web version is newer than local version"""        
        try:
            if self.web_version:
                # convert a.b.c to 000a000b000c and compare
                local_v_int = int(''.join(f"{part:0>4}" for part in self.local_version.split(".")))
                web_v_int = int(''.join(f"{part:0>4}" for part in self.web_version.split(".")))
                if web_v_int > local_v_int:
                    return True
        except: #pylint:disable=bare-except
            return False
        
        
    def download_file(self, fname:str) -> str:
        """ download file and update progress (blocking)
        Params:
            fname (str): file name to download
        returns:
            str: downloaded file path"""        
        save_file = utils.sub_file(Folder.TEMP, fname)
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
        extract_path = utils.sub_folder(f_path) / Folder.UPDATE
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
                LOGGER.debug("Downloading update: %s", UPDATE_FILE)
                fname = self.download_file(UPDATE_FILE)
                self.update_status = UpdateStatus.UNZIPPING
                self.unzip_file(fname)
                # self.start_update()
                self.update_status = UpdateStatus.PREPARED
                LOGGER.debug("Update prepared, status OK")
            except Exception as e:
                self.update_exception = e
                self.update_status = UpdateStatus.ERROR
                LOGGER.error(e)
            
        t = threading.Thread(
            target=update_task,
            name="UpdateThread",
            daemon=True
        )
        t.start()
        
        
    def start_update(self):
        """ Call batch command to start update and then restart main program """
        
        if sys.platform == "win32":
            exec_path = sys.executable
            exec_name = os.path.basename(exec_path)
            root_folder = str(utils.sub_folder("."))
            update_folder = str(utils.sub_folder(Folder.TEMP)/Folder.UPDATE)
            cmd = f"""
            @echo off
            echo Updating {exec_name} ...
            timeout /t 3 /nobreak
            echo Killing process {exec_name}...
            taskkill /IM {exec_name} /F
            timeout /t 3 /nobreak
            echo copying new file...
            set "sourceDir={update_folder}\*"
            set "destDir={root_folder}"
            xcopy %sourceDir% %destDir% /s /e /y
            echo Update completed. Restarting {exec_name}...            
            start {exec_name}
            timeout /t 5 /nobreak
            """
            # save it to a batchfile
            batch_file = utils.sub_file(Folder.TEMP, "update.bat")
            with open(batch_file, "w", encoding="utf-8") as f:
                f.write(cmd)
            subprocess.Popen(
                ['cmd.exe', '/c', batch_file],
                creationflags=subprocess.CREATE_NEW_CONSOLE)
            sys.exit(0)

        elif sys.platform == "darwin":
            exec_name = os.path.basename(sys.executable)
            root_folder = str(utils.sub_folder("."))
            update_folder = str(utils.sub_folder(Folder.TEMP)/Folder.UPDATE)
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
            script_file = utils.sub_file(Folder.TEMP, "update.sh")
            with open(script_file, "w", encoding='utf-8') as f:
                f.write(cmd)
            os.chmod(script_file, 0o755)  # Make the script executable
            
            # Execute the script in a new Terminal window
            subprocess.Popen(["open", "-a", "Terminal.app", script_file])
            
        else:
            # not supported
            pass
