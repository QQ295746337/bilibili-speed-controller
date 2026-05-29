# B站倍速控制

Bilibili桌面客户端倍速控制工具，**突破官方最高2倍速限制**，支持最高5倍速播放。

## 原理

B站桌面客户端基于Electron构建。本工具通过修改`app.asar`，在启动时开启Chrome DevTools Protocol调试端口(9222)，然后通过CDP协议向播放页面的 `<video>` 元素注入 `playbackRate` 控制指令，实现任意倍速播放。

## 功能

- 浮动置顶窗口，不影响视频观看
- 7档速度切换：1x / 1.5x / 2x / 2.5x / 3x / 4x / 5x
- 自动检测B站安装位置和运行状态
- 一键注入/恢复 CDP 调试开关，无需手动操作文件
- 启动时自动居中屏幕

## 环境要求

- Windows 10+
- B站桌面客户端（需在常见安装位置或运行时可自动检测）
- Node.js / npm（用于注入CDP时自动调用的打包工具）

## 使用方式

### 方法一：下载exe直接运行

从 [Releases](../../releases) 下载 `B站倍速控制.exe`，双击运行。

### 方法二：Python脚本运行

```bash
pip install -r requirements.txt
python main.py
```

### 操作步骤

1. 运行 `B站倍速控制.exe`
2. 点击 **"一键注入CDP"** 按钮（首次使用需要，仅需一次）
3. 打开B站客户端，播放一个视频
4. 点击 **"连接B站"**
5. 点击任意速度按钮调节倍速

如需恢复原版B站客户端，点击 **"恢复原版"** 按钮即可。

## 文件说明

| 文件 | 说明 |
|------|------|
| `main.py` | tkinter GUI主程序 |
| `cdp_controller.py` | Chrome DevTools Protocol通信层 |
| `bilibili_manager.py` | B站进程与端口检测 |
| `asar_patcher.py` | app.asar注入/恢复 |
| `requirements.txt` | Python依赖 |

## 注意事项

- 注入CDP需要关闭B站客户端，注入完成后重新打开
- 注入过程中会自动备份原版 `app.asar.bak`
- B站更新后需要重新注入
- 仅供学习研究使用
