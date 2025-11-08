# record_fixed_window.py
import subprocess
import time

PKG_NAME = "com.tencent.tmgp.pubgmhd"   # 和平精英应用包名
ACTIVITY = "com.epicgames.ue4.SplashActivity"  # 启动 Activity（通常通用)

def find_device_serial_by_name(device_name: str, timeout: float = 2.0):
    """通过 adb devices -l 查找包含 device_name 的可用设备 serial（只返回状态为 'device' 的那一项）"""
    try:
        p = subprocess.run(["adb", "devices", "-l"], capture_output=True, text=True, check=True, timeout=timeout)
        out = p.stdout.splitlines()
    except Exception as e:
        print(f"查询 adb 设备失败: {e}")
        return None
    for line in out:
        line = line.strip()
        if not line or line.startswith("List of devices"):
            continue
        # 示例行: "192.168.137.42:35043 device product:... model:PFZM10 ..."
        if " device " not in line:
            continue
        if device_name in line:
            serial = line.split()[0]
            return serial
    return None

def open_pubg(device_name: str = "PFZM10", serial: str = None):
    """打开和平精英并等待完全加载，优先使用 serial，如果未传则按 device_name 查找"""
    try:
        if serial is None and device_name:
            serial = find_device_serial_by_name(device_name)
            if serial is None:
                print(f"未找到状态为 'device' 且包含名字 '{device_name}' 的设备，请检查 adb 连接")
                return
        cmd = ["adb", "-s", serial, "shell", "am", "start", "-n", f"{PKG_NAME}/{ACTIVITY}"] if serial else ["adb", "shell", "am", "start", "-n", f"{PKG_NAME}/{ACTIVITY}"]
        subprocess.run(cmd, check=True)
        print(f"已发送启动命令（serial={serial}），等待游戏加载...")
        time.sleep(5)
        print("和平精英应已打开！")
    except subprocess.CalledProcessError as e:
        print("adb 执行失败，请检查设备连接与授权：", e)
    except Exception as e:
        print("open_pubg 异常：", e)

def record_android(device_name: str = "PFZM10", serial: str = None):
    """启动 scrcpy 并指定 -s serial（若未传 serial 会按 device_name 查找）"""
    try:
        if serial is None and device_name:
            serial = find_device_serial_by_name(device_name)
            if serial is None:
                print(f"未找到状态为 'device' 且包含名字 '{device_name}' 的设备，scrcpy 无法指定设备")
                # 仍然尝试不带 -s 启动 scrcpy（可修改为直接返回）
                cmd = [
                    "scrcpy",
                    "--window-x", "2189",
                    "--window-y", "0",
                    "--window-width", "1000",
                ]
            else:
                cmd = [
                    "scrcpy",
                    "-s", serial,
                    "--window-x", "2189",
                    "--window-y", "0",
                    "--window-width", "1000",
                ]
        else:
            cmd = [
                "scrcpy",
                "-s", serial,
                "--window-x", "2189",
                "--window-y", "0",
                "--window-width", "1000",
            ]
        print(f"启动 scrcpy：{' '.join(cmd)}")
        subprocess.run(cmd)
    except Exception as e:
        print(f"启动 scrcpy/record 失败: {e}")

if __name__ == "__main__":
     open_pubg()
     record_android()
