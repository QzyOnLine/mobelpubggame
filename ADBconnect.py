#!/usr/bin/env python3
# adb_scan_big_port.py
import ipaddress
import subprocess
import concurrent.futures
import socket
import subprocess
import time

PKG_NAME = "com.tencent.tmgp.pubgmhd"   # 和平精英应用包名
ACTIVITY = "com.epicgames.ue4.SplashActivity"  # 启动 Activity（通常通用）
SUBNET      = "192.168.137.42"      #IP地址
PORT_RANGE  = range(29999, 49999)   #端口号
THREADS     = 1000                   # 并发数，可按机器性能调整
TIMEOUT     = 0.3                   # TCP 连通性超时（秒）


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
        "--window-width", "1080",   # 本地窗口固定数字 px（高自动等比）
        #"--record", "auto.mp4",    # 后台同时录成 mp4
        #"--no-display"             # 可选：不弹窗口，纯后台录
    ]
    subprocess.run(cmd)

def tcp_open(ip, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(TIMEOUT)
        return s.connect_ex((str(ip), port)) == 0

def adb_connect(addr):
    rc, out, _ = subprocess.run(f"adb connect {addr}", shell=True,
                                capture_output=True, text=True).returncode, "", ""
    return rc == 0 and "connected to" in out

def job(ip, port):
    addr = f"{ip}:{port}"
    if tcp_open(ip, port) and adb_connect(addr):
        print(f"[+] 成功连接 {addr}")
        return addr
    return None

def main():
    network = ipaddress.ip_network(SUBNET, strict=False)
    print(f"开始扫描 {SUBNET} 端口 {PORT_RANGE.start}-{PORT_RANGE.stop - 1} …")
    ok = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=THREADS) as pool:
        futures = [pool.submit(job, ip, port)
                   for ip in network.hosts()
                   for port in PORT_RANGE]
        for f in concurrent.futures.as_completed(futures):
            addr = f.result()
            if addr:
                ok.append(addr)

# -------------- 扫描结束 --------------
    print("\n=== 最终已连接 ===")
    if ok:
        for a in ok:
            print(" ", a)
    else:
        print("  本次未发现任何设备")

    # ===== 新增：批量断开所有 offline 的无线设备 =====
    print("\n=== 清理 offline 无线连接 ===")
    cp = subprocess.run("adb devices", shell=True, capture_output=True, text=True)
    for line in cp.stdout.splitlines():
        if ":" in line and "offline" in line:
            addr = line.split()[0]
            subprocess.run(f"adb disconnect {addr}", shell=True)
            print(f" 已断开 offline 设备 {addr}")
        # =================================================

    print("已连接设备:")
    subprocess.run("adb devices", shell=True)

if __name__ == "__main__":
     main()
     open_pubg()
     record_android()