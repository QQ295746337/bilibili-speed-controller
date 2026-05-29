# B站倍速控制

突破Bilibili桌面客户端最高2倍速限制，支持 **0.1x ~ 16.0x** 任意倍速播放。

## 原理

B站桌面客户端基于 Electron 构建。本工具通过修改 `app.asar` 开启 Chrome DevTools Protocol 调试端口(9222)，再通过 WebSocket 向 `<video>` 元素注入 `playbackRate` 控制指令，实现任意倍速。

## 功能

- 浮动置顶窗口，不遮挡视频画面
- 8 档预设速度：1x / 1.5x / 2x / 2.5x / 3x / 3.5x / 4x / 5x
- 自定义倍速输入：支持 0.1 ~ 16.0，精确到小数点后一位
- 一键注入 CDP 调试开关，自动备份原版 `app.asar`
- 一键恢复原版
- 自动检测 B站安装位置和运行状态
- 启动时自动居中屏幕

## 环境要求

- Windows 10+
- B站桌面客户端
- Node.js / npm（仅注入 CDP 时需要）

## 快速开始

### 下载 exe（推荐）

从 [Releases](https://github.com/NCEPUljxx/bilibili-speed-controller/releases) 下载最新版 `B站倍速控制.exe`，双击即用。

### 或从源码运行

```bash
pip install -r requirements.txt
python main.py
```

### 使用步骤

1. 启动程序，点击 **"一键注入CDP"**（仅首次需要）
2. 打开 B站客户端，播放视频
3. 点击 **"连接B站"**
4. 点击预设速度按钮，或输入自定义速度后回车

如需还原 B站客户端，点击 **"恢复原版"**。

## 文件说明

| 文件 | 说明 |
|------|------|
| `main.py` | tkinter GUI |
| `cdp_controller.py` | CDP WebSocket 通信 |
| `bilibili_manager.py` | B站进程与端口检测 |
| `asar_patcher.py` | app.asar 注入/恢复 |
| `requirements.txt` | Python 依赖 |

## 注意事项

- 注入过程中会自动备份原版 `app.asar.bak`，可随时恢复
- 注入前需关闭 B站客户端
- B站更新后需重新注入
- 仅供学习研究使用
