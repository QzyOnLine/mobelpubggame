# background_scrcpy.py
# 无需虚拟显示器，把 scrcpy 窗口扔到屏幕外实现“后台”抓图
import subprocess
import time
import win32gui
import win32gui, win32ui, win32con, win32api
import win32con
import cv2
import numpy as np
from pathlib import Path

# ========== 参数区 ==========
WINDOW_TITLE = "PFZM10"          # scrcpy 窗口标题前缀
SCRCPY_CMD = [
    "scrcpy",
    "--window-x", "3000",       # 扔到物理屏外
    "--window-y", "0",
    "--window-width", "1080",
    "--window-height", "2412",
    "--always-on-top",          # 防止被遮挡
    "--no-window-decor",        # 去掉标题栏
    "--max-size", "960",        # 降低 CPU 压力（可选）
    "--bit-rate", "4M"
]
LOCK_POS = True                # 是否锁定窗口位置
TEST_GRAB = True               # 是否验证抓图
# ============================

def find_win(title=WINDOW_TITLE):
    """根据标题前缀找窗口句柄"""
    def _cb(hwnd, lst):
        if win32gui.GetWindowText(hwnd).startswith(title):
            lst.append(hwnd)
    wins = []
    win32gui.EnumWindows(_cb, wins)
    return wins[0] if wins else None

def wait_for_window(timeout=10):
    """等 scrcpy 窗口出现"""
    t0 = time.time()
    while time.time() - t0 < timeout:
        hwnd = find_win()
        if hwnd:
            return hwnd
        time.sleep(0.5)
    raise RuntimeError("scrcpy 窗口未出现，请确认设备已连接")

def lock_window_pos(hwnd):
    """锁定窗口位置 & 去掉边框"""
    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
    style &= ~win32con.WS_THICKFRAME   # 禁止拖动边框
    win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
    win32gui.SetWindowPos(hwnd, 0, 3000, 0, 0, 0,
                          win32con.SWP_NOZORDER | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)

def grab_win(hwnd):
    """你的抓图函数，简化版"""
    client = win32gui.GetClientRect(hwnd)
    w, h = client[2], client[3]
    left_top = win32gui.ClientToScreen(hwnd, (0, 0))

    hwin = win32gui.GetDesktopWindow()
    hwndDC = win32gui.GetWindowDC(hwin)
    mfcDC = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()
    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
    saveDC.SelectObject(saveBitMap)
    saveDC.BitBlt((0, 0), (w, h), mfcDC, left_top, win32con.SRCCOPY)

    signed = saveBitMap.GetBitmapBits(True)
    img = np.frombuffer(signed, dtype='uint8').reshape((h, w, 4))[:, :, :3]

    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC(); mfcDC.DeleteDC(); win32gui.ReleaseDC(hwin, hwndDC)
    return img

def main():
    # 1. 启动 scrcpy
    proc = subprocess.Popen(SCRCPY_CMD, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        # 2. 等窗口出现
        hwnd = wait_for_window()
        print(f"[+] scrcpy 窗口句柄: {hwnd}")

        # 3. 锁定位置
        if LOCK_POS:
            lock_window_pos(hwnd)
            print("[+] 窗口已锁定到屏幕外")

        # 4. 验证抓图
        if TEST_GRAB:
            time.sleep(2)  # 等画面稳定
            img = grab_win(hwnd)
            cv2.imwrite("test_bg.jpg", img)
            print("[+] 抓图测试已保存为 test_bg.jpg")

        # 5. 这里你可以继续跑 YOLO 循环
        # while True:
        #     img = grab_win(hwnd)
        #     ...
    finally:
        proc.terminate()

if __name__ == "__main__":
    main()