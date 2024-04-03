# Mahjong Copilot / 雀魂 Copilot

Mahjong AI Assistant for Maj-soul. When you are in a game in Majsoul, AI will give you step-by-step guidance.

Features:

- Step-by-step AI guidance with in-game overlay.
- Auto play
- Multi-language support
- Supports Mortal local model and online model

雀魂麻将的 AI 助手，基于 Mortal 麻将 AI. 会对你游戏的每一步进行指导。

特性：

- 对局每一步 AI 指导，在游戏中覆盖显示
- 自动打牌
- 多语言支持
- 支持本地 Mortal 模型和在线模型

## Instructions 使用方法

### To Run

1. Download the archive from [Release](https://github.com/latorc/MahjongCopilot/releases) and unzip.
2. Aquire Mortal model file (pth file), and put it into 'models' folder. For model file please refer to [Akagi](https://github.com/shinkuan/Akagi?tab=readme-ov-file#installation).
3. Launch exe file.

Note: Enable autoplay feature at your own risk because it may lead to account suspension. Do not use autoplay for like 24 hours a day.

### 运行方法

1. 从 [Release](https://github.com/latorc/MahjongCopilot/releases) 中下载压缩包并解压。
2. 获取 Mortal 模型文件 （pth 文件），放到 'models' 目录中。模型文件请参见 [Akagi](https://github.com/shinkuan/Akagi?tab=readme-ov-file#installation).
3. 运行 exe 文件。

注意：使用自动打牌有风险，可能导致账户被封。请勿一天 24 小时使用自动打牌。

### To Develope

1. Clone the repo

```
git clone https://github.com/latorc/MahjongCopilot.git
```

2. (optional, recommended) Install Python virtual environment. Python version 3.11 recommended.
3. Install dependencies in requirements.txt
4. Main entrance is: gui.py

### 开发

1. 克隆 repo

```
git clone https://github.com/latorc/MahjongCopilot.git
```

2. (可选，推荐）安装 Python 虚拟环境。Python 版本推荐 3.11.
3. 安装 requirements.txt 中的依赖。
4. 主程序入口: gui.py

## Screenshots 截图

GUI 界面

![](assets/shot1.png)

In-game HUD (Overlay) 游戏中 HUD (覆盖显示）

![](assets/shot2.png)

![](assets/shot3.png)

## Design 设计

![](assets/design_struct.png)

## Credit 鸣谢

- Based on Mortal Model an MJAI protocol
  
  基于 Mortal 模型和 MJAI 协议
  
  Mortal: https://github.com/Equim-chan/Mortal
- Design and implementation based on Akagi
  
  设计和功能实现基于 Akagi
  
  Akagi: https://github.com/shinkuan/Akagi
- 参考 Reference
  Mahjong Soul API: https://github.com/MahjongRepository/mahjong_soul_api


- MJAI Protocol Reference
  
  MJAI协议参考
  
  MJAI: https://mjai.app

