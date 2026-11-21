# Windows 接收端

建议使用 Windows 和 64 位 Python 3.12。以下命令在仓库根目录下执行。

```powershell
cd desktop
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

首次启动会生成本机配对信息并显示配对二维码。请只将配对码提供给自己信任的设备。

## 连接

- **Wi-Fi**。手机与电脑接入同一个可信局域网，手机端切到 Wi-Fi 后扫码。不能扫码时可手输电脑 IP 和配对码。Windows 防火墙如询问放行，选择适合可信局域网的专用网络。
- **USB**。从 Android SDK 安装 Platform Tools，把 adb 加进 PATH。在手机启用 USB 调试，用数据线连接并确认授权。接收端可以自动寻找 adb。如果连接页提示转发未就绪，可在电脑执行 adb reverse tcp:9877 tcp:9877，再用手机端 USB 模式输入配对码。
- **蓝牙**。先在 Windows 和 Android 系统里配对，再在手机端切到蓝牙。经典蓝牙串口模式依赖 Windows 提供兼容的串口。

Wi-Fi 和 USB 接收端会监听 Windows 的网络接口。请勿把 9876、9877 端口转发到公网。关闭程序时可从系统托盘退出。

## 测试

在 desktop 目录中，用安装了上述依赖的 Python 执行 python -m unittest discover -p "test_*.py"。
