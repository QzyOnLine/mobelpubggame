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

model = YOLO(r"D:\VS_Code\runs\train\yolo11n_person2\weights\last.pt")
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
    return img

''' 
def detect_one_class(class_id: int):
    """
    通用检测函数
    :param class_id: 要检测的类别下标
    :return: (cx, cy) 相对窗口客户区的中心坐标；None 表示未检测到
    """
    hwnd = find_win()
    if not hwnd:
        print("未找到窗口，请先运行 scrcpy")
        return None
    frame, _, _ = grab_win(hwnd)
    results = model(frame, verbose=False)[0]

    objs = [d for d in results.boxes.data if int(d[5]) == class_id and d[4] >= CONF_THRES]
    if not objs:
        print(f"\r未检测到类别 {class_id}", end="")
        return None
    best = max(objs, key=lambda x: x[4])
    x1, y1, x2, y2 = best[:4]
    cx = int((x1 + x2) / 2)
    cy = int((y1 + y2) / 2)
    print(f"\r类别 {class_id} 中心坐标（相对窗口）: ({cx}, {cy})  conf:{best[4]:.2f}", end="")
    return cx, cy


# ---------- 业务封装 ----------
def boxs():
    """检测类别 0，执行点击序列"""
    for _ in range(3):
        pos = detect_one_class(0)
        if pos:
            cx, cy = pos
            touch.swipe1(cx, cy)
            touch.swipe(320, 770, 400, 440)
            time.sleep(1)
            touch.tap(320, 770)
            touch.tap(1520, 440)
            time.sleep(3)

def marks():
    """检测类别 1"""
    pos = detect_one_class(1)
    if pos:
        cx, cy = pos
        touch.swipe1(cx, 220)
        touch.swipe(320, 770, 400, 440)

def persons():
    """检测类别 2"""
    touch.tap(320, 770)
    pos = detect_one_class(2)
    if pos:
        cx, cy = pos
        touch.swipe1(cx, cy)
        touch.tap(400, 220)

def rooms():
    """检测类别 3"""
    pos = detect_one_class(3)
    if pos:
        cx, cy = pos
        touch.swipe1(cx, cy)
        touch.swipe(320, 770, 400, 440)
'''

def boxs():
    for _ in range(3):
        hwnd = find_win()
        if not hwnd:
            print("未找到窗口，请先运行 scrcpy"); return
        print("按 q 退出")
        frame = grab_win(hwnd)          # ← 替换 ImageGrab
        results = model(frame, verbose=False)[0]
        boxs   = [d for d in results.boxes.data if int(d[5]) == 0 and d[4] >= CONF_THRES]
        if not persons:               # ← 新增
            print("\r未检测到类别 boxs", end="")
            return None
        best = max(boxs, key=lambda x: x[4])
        x1, y1, x2, y2 = best[:4]
        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)
        touch.swipe1(cx, cy)
        touch.swipe(320,770,400,440)
        time.sleep(1)
        touch.tap(320,770)
        touch.tap(1520,440)
        time.sleep(3)

def marks():
    hwnd = find_win()
    if not hwnd:
        print("未找到窗口，请先运行 scrcpy"); return
    print("按 q 退出")
    frame = grab_win(hwnd)          # ← 替换 ImageGrab
    results = model(frame, verbose=False)[0]
    marks   = [d for d in results.boxes.data if int(d[5]) == 1 and d[4] >= CONF_THRES]
    if not marks:               # ← 新增
        print("\r未检测到类别 marks", end="")
        touch.tap(1560,125)
        time.sleep(1)
        x=random.randint(1500,1800)
        y=random.randint(350,650)
        touch.tap(x,y)
        time.sleep(1)
        touch.tap(2280,80)
        return None
    print("\r检测到类别 marks", end="")
    best = max(marks, key=lambda x: x[4])
    x1, y1, x2, y2 = best[:4]
    cx = int((x1 + x2) / 2)
    cy = int((y1 + y2) / 2)
    touch.swipe1(cx, 220)
    touch.swipe(320,770,400,440)

def persons():
    touch.tap(320, 770)
    hwnd = find_win()
    if not hwnd:
        print("未找到窗口，请先运行 scrcpy"); return
    print("按 q 退出")
    frame = grab_win(hwnd)          # ← 替换 ImageGrab
    results = model(frame, verbose=False)[0]
    persons = [d for d in results.boxes.data if int(d[5]) == 2 and d[4] >= CONF_THRES]
    if not persons:               # ← 新增
        print("\r未检测到类别 persons", end="")
        return False
    print("\r检测到类别 persons", end="")
    best = max(persons, key=lambda x: x[4])
    x1, y1, x2, y2 = best[:4]
    cx = int((x1 + x2) / 2)
    cy = int((y1 + y2) / 2)
    #print(f"中心坐标（相对窗口）: ({cx}, {cy})")
    touch.swipe1(cx, cy)
    touch.tap(400, 220)
    touch.tap(1000,830)
    
    return True 


def rooms():
    hwnd = find_win()
    if not hwnd:
        print("未找到窗口，请先运行 scrcpy"); return
    print("按 q 退出")
    frame = grab_win(hwnd)          # ← 替换 ImageGrab
    results = model(frame, verbose=False)[0]
    rooms = [d for d in results.boxes.data if int(d[5]) == 3 and d[4] >= CONF_THRES]
    if not persons:               # ← 新增
        print("\r未检测到类别 roos", end="")
        return None
    best = max(rooms, key=lambda x: x[4])
    x1, y1, x2, y2 = best[:4]
    cx = int((x1 + x2) / 2)
    cy = int((y1 + y2) / 2)
    touch.swipe1(cx, cy)
    touch.swipe(320,770,400,440)


def main():
    hwnd = find_win()
    if not hwnd:
        print("未找到窗口，请先运行 scrcpy"); return
    print("按 q 退出")
    last_t = 0
    while True:
        run_flag.wait()          # ① 等待 OCR 放行
        if run_flag is None:     # ② 彻底退出信号
            break
        t0 = time.time()
        if t0 - last_t < INTERVAL:
            time.sleep(0.05); continue
        last_t = t0
        touch.tap(2240,640)
        per=persons()
        if not per:
            marks()
            touch.tap(880,1020)
            time.sleep(10)
            touch.tap(2240,640)
            xx = random.randint(500, 800)
            touch.swipe1(xx,220)
            time.sleep(3)




if __name__ == "__main__":
    main()

# gameplayer.py  末尾新增
import threading
run_flag = threading.Event()   # 全局开关