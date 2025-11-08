#!/usr/bin/env python3
# adb_scan_big_port.py
import ipaddress
import subprocess
import concurrent.futures
import socket
import time
import sys

PKG_NAME = "com.tencent.tmgp.pubgmhd"   # 和平精英应用包名
ACTIVITY = "com.epicgames.ue4.SplashActivity"  # 启动 Activity（通常通用）
SUBNET      = "192.168.137.42"      #IP地址（保留旧功能）
PORT_RANGE  = range(29999, 49999)   #端口号
THREADS     = 1000                   # 并发数，可按机器性能调整
TIMEOUT     = 0.3                   # TCP 连通性超时（秒)


def _list_adb_devices(timeout: float = 2.0):
    """返回 adb devices -l 的每一行（列表），异常时返回空列表"""
    try:
        cp = subprocess.run(["adb", "devices", "-l"], capture_output=True, text=True, check=True, timeout=timeout)
        return cp.stdout.splitlines()
    except Exception as e:
        print(f"查询 adb 设备失败: {e}")
        return []


def find_device_serial_by_name(device_name: str, timeout: float = 2.0):
    """通过 adb devices -l 查找包含 device_name 的可用设备 serial（优先状态为 'device'）"""
    lines = _list_adb_devices(timeout)
    candidates = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("List of devices"):
            continue
        # 只考虑包含空格分隔字段的行
        parts = line.split()
        if len(parts) < 2:
            continue
        serial = parts[0]
        status = parts[1]
        if device_name in line:
            candidates.append((serial, status, line))
    # 优先返回状态为 device 的设备
    for serial, status, line in candidates:
        if status == "device":
            return serial
    # 否则返回第一个候选（即可能为 offline/emulator 等）
    if candidates:
        return candidates[0][0]
    return None


def adb_connect(addr: str):
    """执行 adb connect addr，并根据输出判断是否成功"""
    try:
        rp = subprocess.run(["adb", "connect", addr], capture_output=True, text=True)
        out = (rp.stdout or "") + (rp.stderr or "")
        ok = ("connected to" in out.lower()) or ("already connected" in out.lower())
        return rp.returncode == 0 and ok
    except Exception as e:
        print(f"adb connect 执行异常: {e}")
        return False


def ensure_connect_by_name(device_name: str = "PFZM10"):
    """确保与指定名字的设备建立连接，返回找到的 serial 或 None。
    逻辑：
      - 先查 adb devices -l 中是否已有匹配 serial（优先状态 device）
      - 若找到且为 network addr (包含 ':' ) 且未 connected，则尝试 adb connect serial
      - 若找到并状态为 device，直接返回 serial
    """
    serial = find_device_serial_by_name(device_name)
    if not serial:
        print(f"未在 adb devices 中找到包含名字 '{device_name}' 的设备")
        return None

    # 如果 serial 包含 ':'（可能是 tcpip 地址），尝试 adb connect 确保连接
    if ":" in serial:
        # 如果已是 device 状态就可以直接返回
        lines = _list_adb_devices()
        for line in lines:
            if serial in line and " device " in line:
                return serial
        # 否则尝试连接
        print(f"尝试 adb connect {serial} …")
        if adb_connect(serial):
            # 等待短时间再确认
            time.sleep(0.5)
            lines = _list_adb_devices()
            for line in lines:
                if serial in line and " device " in line:
                    print(f"已连接 {serial}")
                    return serial
            print(f"adb connect 返回成功但未在 devices 列表中看到 device 状态：\n{lines}")
            return serial
        else:
            print(f"adb connect {serial} 失败")
            return None
    else:
        # 本地 USB/非 tcpip serial，检查状态是否为 device
        lines = _list_adb_devices()
        for line in lines:
            if serial in line and " device " in line:
                return serial
        print(f"找到 serial={serial} 但状态不是 device，请检查设备：\n{lines}")
        return None


# ---------- 保留原有扫描功能（可选） ----------
def tcp_open(ip, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(TIMEOUT)
        try:
            return s.connect_ex((str(ip), port)) == 0
        except Exception:
            return False


def adb_connect_simple(addr):
    """原先简单版本，保留但内部使用新的 adb_connect"""
    return adb_connect(addr)


def job(ip, port):
    addr = f"{ip}:{port}"
    if tcp_open(ip, port) and adb_connect(addr):
        print(f"[+] 成功连接 {addr}")
        return addr
    return None


def main_scan():
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
    # 支持两种用法：
    # 1) 指定设备名连接： python ADBconnect.py connect PFZM10
    # 2) 扫描子网并尝试连接（原功能）： python ADBconnect.py scan
    if len(sys.argv) >= 2 and sys.argv[1] == "connect":
        name = sys.argv[2] if len(sys.argv) >= 3 else "PFZM10"
        print(f"尝试按名字连接设备: {name}")
        s = ensure_connect_by_name(name)
        if s:
            print(f"连接成功: {s}")
        else:
            print("连接失败")
    else:
        # 默认运行原扫描逻辑
        main_scan()