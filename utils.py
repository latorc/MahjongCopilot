# Common/utility methods
# no logging in this file

import datetime
import logging
import pathlib
import sys
import time
import subprocess
import log_helper

VER_NUMBER = "0.2"
MODEL_FOLDER = "models"

class ModelFileException(Exception):
    """ Exception for model file error"""
    pass

def get_sub_folder(folder_name:str) -> pathlib.Path:
    """ return the subfolder absolute path string, create it if not exists"""
    subfolder = pathlib.Path(__file__).parent / folder_name
    if not subfolder.exists():
        subfolder.mkdir(exist_ok=True)
    return subfolder.resolve()

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

def install_root_cert(cert_file:str) -> bool:
    """ Install Root certificate onto the system
    params:
        cert_file(str): certificate file to be installed
    Returns:
        bool: True if the certificate is installed successfully        
    """
    # Install cert. If the cert exists, system will skip installation
    if sys.platform == "win32":
        result = subprocess.run(['certutil', '-addstore', 'Root', cert_file],
            capture_output=True, text=True)

    elif sys.platform == "darwin":
        # TODO Test on MAC system
        result = subprocess.run(['sudo', 'security', 'add-trusted-cert', '-d', '-r', 'trustRoot', '-k', '/Library/Keychains/System.keychain', cert_file],
            capture_output=True, text=True, check=True)
    else:
        print("Unknown Platform. Please manually install MITM certificate:", cert_file)
        return
    
    # Check if successful
    if result.returncode == 0:  # success     
        return True
    else:   # error        
        return False
    
def list_files(folder:str, full_path:bool=False) -> list[pathlib.Path]:
    """ return the list of files in the folder 
    params:
    folder(str): name of the folder
    full_path(bool): True to return the full path, while False to return only the file name"""
    try:
        files = [f for f in pathlib.Path(folder).iterdir() if f.is_file()]
        if full_path:
            return [str(f.resolve()) for f in files]
        else:
            return [f.name for f in files]
    except:
        return []
    
        

if __name__=='__main__':
    # Test code
    folder = get_sub_folder('log')
    print(folder)
    
    wait_res = wait_for_file("utils.py")
    print("wait file results:", wait_res)    
    
    res = install_root_cert("non_exist.cert")
    print("install cert result:", res)
    
    files = list_files('resources',False)
    print(files)
    files = list_files('resources',True)
    print(files)
    