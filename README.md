# B站倍速控制

Bilibili桌面客户端倍速控制工具，**突破官方最高2倍速限制**，支持最高5倍速播放。

https://github.com/user-attachments/assets/6a3b8f7c-2d4e-4f1a-9c5e-b8d2f0a4e6c1

## 原理

B站桌面客户端基于Electron构建。本工具通过修改`app.asar`，在启动时开启Chrome DevTools Protocol调试端口(9222)，然后通过CDP协议向播放页面的 `<video>` 元素注入 `playbackRate` 控制指令，实现任意倍速播放。

## 功能

- 浮动置顶窗口，不影响视频观看
- 7档速度切换：1x / 1.5x / 2x / 2.5x / 3x / 4x / 5x
- 自动检测B站运行状态和视频页面
- 启动时自动居中屏幕

## 环境要求

- Windows 10+
- Python 3.10+
- B站桌面客户端 v1.17.x

## 安装与使用

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 修改B站客户端

备份原版文件，然后用注入CDP调试开关的版本替换：

```powershell
# 备份原版
copy "E:\B站\bilibili\resources\app.asar" "E:\B站\bilibili\resources\app.asar.bak"

# 解包 → 注入 → 重新打包
npx @electron/asar extract "E:\B站\bilibili\resources\app.asar" ./asar_temp
# 在 ./asar_temp/index.js 最开头插入以下代码：
# (function(){try{require('electron').app.commandLine.appendSwitch('remote-debugging-port','9222')}catch(e){}})();
npx @electron/asar pack ./asar_temp "E:\B站\bilibili\resources\app.asar"
```

### 3. 启动

```bash
# 先手动打开B站客户端
# 然后运行倍速控制器
python main.py
```

点击 **"连接B站"** → 打开一个视频 → 点击任意速度按钮即可。

### 4. 恢复原版

```powershell
copy "E:\B站\bilibili\resources\app.asar.bak" "E:\B站\bilibili\resources\app.asar"
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `main.py` | tkinter GUI主程序 |
| `cdp_controller.py` | Chrome DevTools Protocol通信层 |
| `bilibili_manager.py` | B站进程与端口检测 |
| `requirements.txt` | Python依赖 |

## 注意事项

- 使用前必须先手动打开B站客户端
- B站更新后需要重新修改`app.asar`
- 仅供学习研究使用
