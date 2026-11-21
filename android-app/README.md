# Android 客户端

客户端使用 uni-app 和 Vue，通过 HBuilderX 在 Android 真机运行。蓝牙和专注模式使用本仓库的 UTS 原生模块。

1. 用 HBuilderX 打开仓库里的 android-app 目录。
2. 如需制作自定义基座或打包，在 manifest.json 中使用您自己的 DCloud AppID。仓库里的 AppID 是占位值。
3. 在 Android 手机上启用开发者选项和 USB 调试，连接电脑并授权。
4. 按 DCloud 的说明制作并选用**自定义 Android 运行基座**，再在 HBuilderX 运行到手机。项目编译和运行基座请使用同一版本的 HBuilderX。
5. 运行桌面端后，从手机连接页选择 Wi-Fi、USB 或蓝牙。

[自定义运行基座说明](https://uniapp.dcloud.net.cn/tutorial/run/run-app)

按功能授权即可。扫码需要相机权限，蓝牙需要附近设备权限，语音需要麦克风权限，专注模式的部分功能需要无障碍和悬浮窗权限。

## 测试

在 android-app 目录中用支持原生 ES 模块的 Node.js 运行 npm test。测试覆盖连接状态、手势、配置等逻辑，真机设备的连接和打包需要单独验证。
