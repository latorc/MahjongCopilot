# 麻将 Copilot / Mahjong Copilot

麻将 AI 助手，基于 mjai (Mortal模型) 实现的机器人。会对游戏对局的每一步进行指导。现支持雀魂三人、四人麻将。
QQ群：834105526 <a target="_blank" href="https://qm.qq.com/cgi-bin/qm/qr?k=Mec5daqIyUsuZjCLojH_t88hQV6luPxl&jump_from=webapi&authKey=nNSpmIQY3ieVau/oLTF9eNO6YTqAm1+Ne3iE3zpqmFrj61iAUDu/GSpA38g93Zlx"><img border="0" src="https://pub.idqqimg.com/wpa/images/group.png" alt="加入QQ群" title="麻将 Copilot"></a>

Mahjong AI Assistant for Majsoul, based on mjai (Mortal model) bot impelementaion. When you are in a Majsoul game, AI will give you step-by-step guidance. Now supports Majsoul 3-person and 4-person game modes.

下载、帮助和更多信息请访问网站 Please see website for download, help, and more information  
<a href="https://mjcopilot.com/help" target="_blank">帮助信息 Help Info </a> | <a href="https://mjcopilot.com" target="_blank">https://mjcopilot.com</a>

---

![](assets/shot3_lower.png)

特性：

- 对局每一步 AI 指导，可在游戏中覆盖显示
- 自动打牌，自动加入游戏
- 多语言支持
- 支持本地 Mortal 模型和在线模型，支持三麻和四麻

Features:

- Step-by-step AI guidance for the game, with optional in-game overlay.
- Auto play & auto joining next game
- Multi-language support
- Supports Mortal local models and online models, 3p and 4p mahjong modes.

<a id="instructions"></a>

## 使用方法 / Instructions

### 开发

1. 克隆 repo
2. 安装 Python 虚拟环境。Python 版本推荐 3.11.
3. 安装 requirements.txt 中的依赖。
4. 安装 Playwright + Chromium
5. 主程序入口: main.py

### To Develope

1. Clone the repo
2. Install Python virtual environment. Python version 3.11 recommended.
3. Install dependencies from requirements.txt
4. Install Playwright + Chromium
5. Main entry: main.py

### 示例脚本 Sample script：
```batch
git clone https://github.com/latorc/MahjongCopilot.git
cd MahjongCopilot
python -m venv venv
CALL venv\Scripts\activate.bat
pip install -r requirements.txt
set PLAYWRIGHT_BROWSERS_PATH=0
playwright install chromium
python main.py
```
### 配置模型
本程序支持几种模型来源。其中，本地模型（Local）是基于 Akagi 兼容的 Mortal 模型。要获取 Akagi 的模型，请参见 <a href="https://github.com/shinkuan/Akagi" target="_blank"> Akagi Github </a> 的说明。

#### 使用 Akagi OT2模型 
如需使用 AkagiOT2 模型，请前往 Akagi 的官方 Discord 频道获取对应的 model.pth 和 riichi3p 包并安装。

第一步：下载模型文件 model.pth 和 riichi3p 包

第二步：将 model.pth 放置到目录 `mjai/bot_3p/` 下

第三步：安装 riichi3p 包
```bash
pip install riichi3p-${version}.whl
```
此处安装对应 python 版本和操作系统的 riichi3p 包。

第四步：运行 main.py，打开设置，在模型类型中选择 AkagiOT2 模型。

第五步：设置 OT2 的 url地址 和 api_key，并保存。

第六步：等待 OT2 模型加载完成，即可开始游戏。

### Model Configuration
This program supports different types of AI models. The 'Local' Model type uses Mortal models compatible with Akagi. To acquire Akagi's models, please refer to <a href="https://github.com/shinkuan/Akagi" target="_blank"> Akagi Github </a>.
To use the AkagiOT2 model, please visit Akagi's official Discord channel to obtain the corresponding model.pth and riichi3p package, and then install them.

#### Using the Akagi OT2 Model
To use the AkagiOT2 model, please visit the official Akagi Discord channel to obtain the corresponding `model.pth` file and `riichi3p` package, and install them.

Step 1: Download the model file `model.pth` and the `riichi3p` package.

Step 2: Place the `model.pth` file in the directory `mjai/bot_3p/`.

Step 3: Install the `riichi3p` package:
```bash
pip install riichi3p-${version}.whl
```
Install the `riichi3p` package appropriate for your Python version and operating system here.

Step 4: Run `main.py`, open the settings, and select the AkagiOT2 model under model type.

Step 5: Set the URL and API key for OT2 and save.

Step 6: Wait for the OT2 model to load completely, then you can start the game.

## 截图 / Screenshots

界面 / GUI

![](assets/shot1.png)
![](assets/settings.png)

游戏中覆盖显示 (HUD）/ In-game Overlay (HUD)

![](assets/shot2.png)

![](assets/shot3.png)

## 设计 / Design

![](assets/design_struct.png)

  
目录说明 Description for folders：
* gui: tkinter GUI 相关类 / tkinter GUI related classes
* game: 雀魂游戏相关类 / classes related to Majsoul game
* bot: AI 模型和机器人实现 / implementations for AI models and bots 
* common: 共同使用的支持代码 commonly used supporting code
* libriichi & libriichi3p: 编译完成的 libriichi 库文件 / For compiled libriichi libraries

## 鸣谢 / Credit

- 基于 Mortal 模型和 MJAI 协议
  Based on Mortal Model an MJAI protocol
  
  Mortal: https://github.com/Equim-chan/Mortal
- 设计和功能实现基于 Akagi
  Design and implementation based on Akagi
  
  Akagi: https://github.com/shinkuan/Akagi
- 参考 Reference
  Mahjong Soul API: https://github.com/MahjongRepository/mahjong_soul_api
- MJAI协议参考 / MJAI Protocol Reference
  
  MJAI: https://mjai.app

## 许可 / License
本项目使用 GNU GPL v3 许可协议。  
协议全文请见 [LICENSE](LICENSE)
