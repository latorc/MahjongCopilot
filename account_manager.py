import os,sys,shutil
from common.utils import sub_folder,list_folders,Folder
from common.log_helper import LOGGER
import plyvel

# 保存当前用户（起个名字）
def saveUserAccount(name):
        newAccountPathStr=Folder.ACCOUNT_RECORDS+"/"+name
        if os.path.exists(Folder.CHROME_DB):
            newDB_init=False
            try:
                newDB=plyvel.DB(str(sub_folder(newAccountPathStr)),create_if_missing=True)
                newDB_init=True
                chromeDB= plyvel.DB(Folder.CHROME_DB,create_if_missing=False)
                for key,value in chromeDB:
                    newDB.put(key,value)
                chromeDB.close()
                newDB.close()
            except Exception as e:
                if newDB_init:
                    LOGGER.error("save account %s fail,chrome db exception %s",name,str(e))
                else:
                    LOGGER.error("save account %s fail,new DB exception %s",name,str(e))
                return
        else:
            LOGGER.info("save account %s fail,chrome DB not found",name)
            return 
        return

# 切换账号
def switchAccountLogin(name):
    users=listUser()
    if name not in users:
        LOGGER.error("switch %s fail,not found in the list of users",name)
        return
    newAccountPathStr=Folder.ACCOUNT_RECORDS+"/"+name
    if os.path.exists(newAccountPathStr):
        # shutil.rmtree(Folder.CHROME_DB, ignore_errors=True)        
        try:
                oldDB=plyvel.DB(newAccountPathStr,create_if_missing=False)
                chromeDB= plyvel.DB(str(sub_folder(Folder.CHROME_DB)),create_if_missing=True)
                for key,value in oldDB:
                    chromeDB.put(key,value)
                chromeDB.close()
                oldDB.close()
        except Exception as e:
                LOGGER.error("switch %s fail,exception=%s",name,str(e))
                return
    else:
        LOGGER.error("switch %s fail,account not found",name)
        return

# 列出所有保存的用户
def listUser():
    try:
        return list_folders(str(sub_folder(Folder.ACCOUNT_RECORDS).resolve()))
    except:
        LOGGER.error("list user fail")
        return