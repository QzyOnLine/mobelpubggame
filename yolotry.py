#!/usr/bin/env python3
import cv2
import numpy as np
import random
import win32gui, win32ui, win32con
from ultralytics import YOLO
import touch
import time
import ctypes
import threading

run_flag = threading.Event() 
ctypes.windll.user32.SetProcessDPIAware()   # 高 DPI 不缩放

model = YOLO(r"D:\VS_Code\pubggame\runs\train\anquanqu\weights\last.pt")
CONF_THRES = 0.4
INTERVAL   = 0.55
WINDOW_TITLE = "PFZM10"      # 窗口标题前缀，按需改

def find_win():
    def _cb(hwnd, lst):
        if win32gui.GetWindowText(hwnd).startswith(WINDOW_TITLE):
            lst.append(hwnd)
    wins = []
    win32gui.EnumWindows(_cb, wins)
    return wins[0] if wins else None

def grab_win(hwnd):
    """抓客户区，返回 BGR 数组"""
    if not hwnd or not win32gui.IsWindow(hwnd):
        raise RuntimeError("窗口无效或已关闭")
    client = win32gui.GetClientRect(hwnd)
    w, h = client[2], client[3]
    if w <= 0 or h <= 0:
        raise RuntimeError("客户区宽高为 0，请确保窗口未最小化")
    left_top = win32gui.ClientToScreen(hwnd, (0, 0))

    hwin = win32gui.GetDesktopWindow()
    hwndDC = win32gui.GetWindowDC(hwin)
    mfcDC  = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()
    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
    saveDC.SelectObject(saveBitMap)
    saveDC.BitBlt((0, 0), (w, h), mfcDC, left_top, win32con.SRCCOPY)

    signedIntsArray = saveBitMap.GetBitmapBits(True)
    img = np.frombuffer(signedIntsArray, dtype='uint8')
    img = img.reshape((h, w, 4))[:, :, :3]  # BGRA → BGR

    # 清理
    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC(); mfcDC.DeleteDC(); win32gui.ReleaseDC(hwin, hwndDC)
    return img.copy()  # 加这一行

def draw_yolo(img, results):
    """在 img 上画 YOLO 检测结果"""
    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            label = f"{model.names[cls]} {conf:.2f}"

            color = (0, 255, 0)
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            cv2.putText(img, label, (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    return img  # 加这一行

if __name__ == "__main__":
    hwnd = find_win()
    if not hwnd:
        print("未找到窗口")
        exit()

    while True:
        try:
            img = grab_win(hwnd)
            results = model(img, conf=CONF_THRES)
            img = draw_yolo(img, results)

            cv2.imshow("YOLO Detection", img)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        except Exception as e:
            print("Error:", e)
            break

    cv2.destroyAllWindows()