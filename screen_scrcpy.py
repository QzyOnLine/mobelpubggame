# record_fixed_window.py
import subprocess
import time

PKG_NAME = "com.tencent.tmgp.pubgmhd"   # 和平精英应用包名
ACTIVITY = "com.epicgames.ue4.SplashActivity"  # 启动 Activity（通常通用）

def open_pubg():
    """打开和平精英并等待完全加载"""
    try:
        # # 1. 唤醒屏幕（若灭屏）
        # subprocess.run(["adb", "shell", "input", "keyevent", "KEYCODE_POWER"], check=False)
        # time.sleep(0.5)

        # # 2. 解锁（若存在滑动锁，可继续追加滑动解锁命令）
        # subprocess.run(["adb", "shell", "input", "swipe", "540", "1500", "540", "800"], check=False)
        # time.sleep(0.5)

        # 3. 启动应用
        cmd = ["adb", "shell", "am", "start", "-n", f"{PKG_NAME}/{ACTIVITY}"]
        subprocess.run(cmd, check=True)
        print("已发送启动命令，等待游戏加载...")
        time.sleep(5)  # 可视机器性能调整
        print("和平精英应已打开！")
    except subprocess.CalledProcessError as e:
        print("adb 执行失败，请检查设备连接与授权：", e)

def record_android():
    cmd = [
        "scrcpy",
        "--window-x", "2189",       # 扔到物理屏外
        "--window-y", "0",
        #"--max-size", "1080",      # 录制分辨率 1080p（可改 720/1440）
        "--window-width", "1000",   # 本地窗口固定数字 px（高自动等比）
        #"--record", "auto.mp4",    # 后台同时录成 mp4
        #"--no-display"             # 可选：不弹窗口，纯后台录
    ]
    subprocess.run(cmd)

if __name__ == "__main__":
     open_pubg()
     record_android()
