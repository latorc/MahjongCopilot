import os,sys,shutil
from common.utils import ACCOUNT_RECORDS,sub_folder,CHROME_DB,list_folders
from common.log_helper import LOGGER
import plyvel

# 保存当前用户（起个名字）
def saveUserAccount(name):
        newAccountPathStr=ACCOUNT_RECORDS+"/"+name
        if os.path.exists(CHROME_DB):
            try:
                newDB=plyvel.DB(str(sub_folder(newAccountPathStr)),create_if_missing=True)
                chromeDB= plyvel.DB(CHROME_DB,create_if_missing=False)
                for key,value in chromeDB:
                    newDB.put(key,value)
                chromeDB.close()
                newDB.close()
            except Exception as e:
                LOGGER.error(str("save account "+name+" fail",e))
                return
        else:
            LOGGER.info(str("save account "+name+" fail,chrome DB not found"))
            return
        LOGGER.info(str("save account "+name+" success"))    
        return

# 切换账号
def switchAccountLogin(name):
    users=listUser()
    if name not in users:
        LOGGER.error(str("switch "+name+" fail,not found in the list of users"))
        return
    newAccountPathStr=ACCOUNT_RECORDS+"/"+name
    if os.path.exists(newAccountPathStr):
        # shutil.rmtree(CHROME_DB, ignore_errors=True)        
        try:
                oldDB=plyvel.DB(newAccountPathStr,create_if_missing=False)
                chromeDB= plyvel.DB(str(sub_folder(CHROME_DB)),create_if_missing=True)
                for key,value in oldDB:
                    chromeDB.put(key,value)
                chromeDB.close()
                oldDB.close()
        except Exception as e:
                LOGGER.error(str("switch "+name+" fail",e))
                return
    else:
        LOGGER.error(str("switch "+name+" fail,account not found"))
        return

# 列出所有保存的用户
def listUser():
    try:
        return list_folders(str(sub_folder(ACCOUNT_RECORDS).resolve()))
    except:
        LOGGER.error(str("list user fail"))
        return