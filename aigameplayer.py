#!/usr/bin/env python3
# coding: utf-8
"""
可直接运行的 PUBG 自动化脚本（原 regameplayer.py 精简并可执行）
将文件保存为 aigameplayer.py 后运行：python aigameplayer.py
"""
import argparse
import ctypes
import threading
import time
import sys
from functools import lru_cache

import cv2
import numpy as np
from ultralytics import YOLO

import win32gui
import win32ui
import win32con

import touch
import adb_once
import ADBconnect
import screen_scrcpy   # 新增：用于自动打开 scrcpy

# 高 DPI 不缩放
ctypes.windll.user32.SetProcessDPIAware()

# 全局默认配置（可通过命令行覆盖）
DEFAULT_MODEL_PATH = r"D:\VS_Code\pubggame\runs\train\anquanqu\weights\last.pt"
CONF_THRES = 0.4
INTERVAL = 0.55
WINDOW_TITLE = "PFZM10"

run_flag = threading.Event()

# ========== 模型加载 ==========
model = None


def load_model(path: str):
    global model
    try:
        model = YOLO(path)
        print(f"模型已加载: {path}")
    except Exception as e:
        print(f"无法加载模型 ({path})：{e}")
        sys.exit(1)


# ========== 窗口与截屏 ==========
def find_win(window_title_prefix: str):
    def _cb(hwnd, lst):
        if win32gui.GetWindowText(hwnd).startswith(window_title_prefix):
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
    mfcDC = win32ui.CreateDCFromHandle(hwndDC)
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
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win32gui.ReleaseDC(hwin, hwndDC)
    return img


def get_client_size(hwnd):
    """返回窗口客户区宽高"""
    rect = win32gui.GetClientRect(hwnd)
    return rect[2], rect[3]


# ========== 卡住检测闭包 ==========
@lru_cache(maxsize=1)
def _stuck_state():
    return [None, 0]


def handle_stuck(img_bgr, thres: float = 0.795, frames: int = 30):
    state = _stuck_state()
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    if state[0] is None or state[0].shape != gray.shape:
        state[0] = gray
        state[1] = 0
        return False

    h1, w1 = state[0].shape
    h2, w2 = gray.shape
    if h1 > h2 or w1 > w2:
        state[0] = gray
        state[1] = 0
        return False

    diff = cv2.matchTemplate(gray, state[0], cv2.TM_CCOEFF_NORMED)[0][0]
    state[0] = gray

    if diff > thres:
        state[1] += 1
    else:
        state[1] = 0

    if state[1] >= frames:
        state[1] = 0
        try:
            ADBconnect.open_pubg()
        except Exception:
            pass
        try:
            touch.swipe(1910, 720, 1500, 700)
            touch.tap(2200, 660)
        except Exception:
            pass
        print('卡死自救')
        return True
    return False


# ========== 坐标映射 ==========
def map_yolo_to_device(yolo_coords, hwnd, device_w=2412, device_h=1080):
    x1, y1, x2, y2 = [float(x) for x in yolo_coords]
    window_w, window_h = get_client_size(hwnd)
    sx = device_w / window_w
    sy = device_h / window_h
    return (int(round(x1 * sx)), int(round(y1 * sy)),
            int(round(x2 * sx)), int(round(y2 * sy)))


# ========== 截图节流 & 定时器 ==========
_last_shot = 0
_MIN_INTERVAL = 20 * 60


def throttle_adb_shot():
    global _last_shot
    now = time.time()
    if now - _last_shot >= _MIN_INTERVAL:
        _last_shot = now
        adb_once.adb_screenshot()


_last_tick = 0


def should_run(now, INTERVAL=3 * 60):
    global _last_tick
    if now - _last_tick >= INTERVAL:
        _last_tick = now
        return True
    return False


# ========== 目标检测与动作 ==========
def _detect_and_get(results, name, conf=CONF_THRES):
    boxes = [
        d for d in results.boxes.data
        if model.names[int(d[5])] == name and d[4] >= conf
    ]
    return boxes


def likai(window_title):
    hwnd = find_win(window_title)
    if not hwnd:
        print("未找到窗口，请先运行 scrcpy")
        return False
    frame = grab_win(hwnd)
    results = model(frame, verbose=False)[0]
    likai_boxes = _detect_and_get(results, 'likai', 0.8)
    if not likai_boxes:
        print("\r未检测到类别 likai", end="")
        return False
    print("\r检测到类别 likai", end="")
    best = max(likai_boxes, key=lambda x: x[4])
    x1, y1, x2, y2 = map_yolo_to_device(best[:4], hwnd=hwnd)
    cx = int((x1 + x2) / 2)
    cy = int((y1 + y2) / 2)
    time.sleep(28)
    touch.tap(cx, cy)
    return True


def anquanqu(window_title):
    hwnd = find_win(window_title)
    if not hwnd:
        print("未找到窗口，请先运行 scrcpy")
        return False
    touch.tap(1560, 125)
    frame = grab_win(hwnd)
    results = model(frame, verbose=False)[0]
    boxes = _detect_and_get(results, 'anquanqu', CONF_THRES)
    if not boxes:
        touch.tap(2280, 80)
        return False
    best = max(boxes, key=lambda x: x[4])
    x1, y1, x2, y2 = map_yolo_to_device(best[:4], hwnd=hwnd)
    cx = int((x1 + x2) / 2)
    cy = int((y1 + y2) / 2)
    touch.tap(cx, cy)
    touch.tap(2280, 80)
    return True


def marks(window_title):
    hwnd = find_win(window_title)
    if not hwnd:
        print("未找到窗口，请先运行 scrcpy")
        return False
    frame = grab_win(hwnd)
    results = model(frame, verbose=False)[0]
    boxes = _detect_and_get(results, 'mark', CONF_THRES)
    if not boxes:
        print("\r未检测到类别 marks", end="")
        anquanqu(window_title)
        return False
    best = max(boxes, key=lambda x: x[4])
    x1, y1, x2, y2 = map_yolo_to_device(best[:4], hwnd=hwnd)
    cx = int((x1 + x2) / 2)
    touch.swipe1(cx, 540)
    touch.swipe(320, 770, 400, 440)
    return True


def persons(window_title):
    touch.tap(320, 770)
    hwnd = find_win(window_title)
    if not hwnd:
        print("未找到窗口，请先运行 scrcpy")
        return False
    frame = grab_win(hwnd)
    results = model(frame, verbose=False)[0]
    boxes = _detect_and_get(results, 'person', CONF_THRES)
    if not boxes:
        print("\r未检测到类别 persons", end="")
        return False
    print("\r检测到类别 persons", end="")
    best = max(boxes, key=lambda x: x[4])
    x1, y1, x2, y2 = map_yolo_to_device(best[:4], hwnd=hwnd)
    cx = int((x1 + x2) / 2)
    cy = int((y1 + y2) / 2)
    touch.swipe1(cx, cy)
    touch.tap(400, 220)
    touch.tap(1000, 830)
    return True


def rooms(window_title):
    hwnd = find_win(window_title)
    if not hwnd:
        print("未找到窗口，请先运行 scrcpy")
        return False
    frame = grab_win(hwnd)
    results = model(frame, verbose=False)[0]
    boxes = _detect_and_get(results, 'room', CONF_THRES)
    if not boxes:
        print("\r未检测到类别 rooms", end="")
        return False
    print("\r检测到类别 rooms", end="")
    best = max(boxes, key=lambda x: x[4])
    x1, y1, x2, y2 = map_yolo_to_device(best[:4], hwnd=hwnd)
    cx = int((x1 + x2) / 2)
    cy = int((y1 + y2) / 2)
    touch.swipe2(cx, cy)
    touch.swipe(320, 770, 400, 440)
    return True


def kaishiyouxi(window_title):
    hwnd = find_win(window_title)
    if not hwnd:
        print("未找到窗口，请先运行 scrcpy")
        return False
    frame = grab_win(hwnd)
    results = model(frame, verbose=False)[0]
    boxes = _detect_and_get(results, 'kaishiyouxi', CONF_THRES)
    if not boxes:
        print("\r未检测到类别 kaishiyouxi", end="")
        return False
    best = max(boxes, key=lambda x: x[4])
    x1, y1, x2, y2 = map_yolo_to_device(best[:4], hwnd=hwnd)
    cx = int((x1 + x2) / 2)
    cy = int((y1 + y2) / 2)
    print('类别 kaishiyouxi', cx, cy)
    touch.tap(cx, cy)
    return True


def jixu(window_title):
    hwnd = find_win(window_title)
    if not hwnd:
        print("未找到窗口，请先运行 scrcpy")
        return False
    frame = grab_win(hwnd)
    results = model(frame, verbose=False)[0]
    boxes = _detect_and_get(results, 'jixu', CONF_THRES)
    if not boxes:
        print("\r未检测到类别 jixu", end="")
        return False
    best = max(boxes, key=lambda x: x[4])
    x1, y1, x2, y2 = map_yolo_to_device(best[:4], hwnd=hwnd)
    cx = int((x1 + x2) / 2)
    cy = int((y1 + y2) / 2)
    print('类别 jixu', cx, cy)
    touch.tap(cx, cy)
    return True


def jixu1(window_title):
    hwnd = find_win(window_title)
    if not hwnd:
        print("未找到窗口，请先运行 scrcpy")
        return False
    frame = grab_win(hwnd)
    results = model(frame, verbose=False)[0]
    boxes = _detect_and_get(results, 'jixu1', CONF_THRES)
    if not boxes:
        print("\r未检测到类别 jixu1", end="")
        return False
    best = max(boxes, key=lambda x: x[4])
    x1, y1, x2, y2 = map_yolo_to_device(best[:4], hwnd=hwnd)
    cx = int((x1 + x2) / 2)
    cy = int((y1 + y2) / 2)
    print('类别 jixu1', cx, cy)
    touch.tap(cx, cy)
    return True


def queding(window_title):
    hwnd = find_win(window_title)
    if not hwnd:
        print("未找到窗口，请先运行 scrcpy")
        return False
    frame = grab_win(hwnd)
    results = model(frame, verbose=False)[0]
    boxes = _detect_and_get(results, 'queding', CONF_THRES)
    if not boxes:
        print("\r未检测到类别 queding", end="")
        return False
    best = max(boxes, key=lambda x: x[4])
    x1, y1, x2, y2 = map_yolo_to_device(best[:4], hwnd=hwnd)
    cx = int((x1 + x2) / 2)
    cy = int((y1 + y2) / 2)
    print('类别 queding', cx, cy)
    touch.tap(cx, cy)
    return True


def fenxiangzhanji(window_title):
    hwnd = find_win(window_title)
    if not hwnd:
        print("未找到窗口，请先运行 scrcpy")
        return False
    frame = grab_win(hwnd)
    results = model(frame, verbose=False)[0]
    boxes = _detect_and_get(results, 'fenxiangzhanji', CONF_THRES)
    if not boxes:
        print("\r未检测到类别 fenxiangzhanji", end="")
        return False
    best = max(boxes, key=lambda x: x[4])
    x1, y1, x2, y2 = map_yolo_to_device(best[:4], hwnd=hwnd)
    cx = int(((x1 + x2) / 2) - 250)
    cy = int((y1 + y2) / 2)
    print('类别 fenxiangzhanji', cx, cy)
    touch.tap(cx, cy)
    return True


# ========== 状态机 ==========
class State:
    def __init__(self):
        self.in_game = False
        self.did_likai = False
        self.anquan_ts = 0


# 新增：后台启动 scrcpy（只启动一次）
_scrcpy_thread = None
def ensure_scrcpy(window_title):
    """若未运行 scrcpy，则异步启动（先尝试打开游戏，再运行 scrcpy）"""
    global _scrcpy_thread
    if _scrcpy_thread and _scrcpy_thread.is_alive():
        return
    def _start():
        try:
            screen_scrcpy.open_pubg()
        except Exception:
            pass
        try:
            screen_scrcpy.record_android()
        except Exception as e:
            print(f"启动 scrcpy/record 失败: {e}")
    t = threading.Thread(target=_start, daemon=True)
    t.start()
    _scrcpy_thread = t


def main_loop(window_title):
    ANQUAN_INTERVAL = 3 * 60
    state = State()

    try:
        while True:
            hwnd = find_win(window_title)
            if not hwnd:
                print("未找到窗口，请先运行 scrcpy")
                ensure_scrcpy(window_title)
                time.sleep(1)
                continue

            frame = grab_win(hwnd)

            events = [
                (lambda: state.in_game and not state.did_likai and likai(window_title), "likai",
                 lambda: setattr(state, 'did_likai', True)),
                (lambda: kaishiyouxi(window_title), "kaishiyouxi",
                 lambda: (setattr(state, 'in_game', True), setattr(state, 'did_likai', False))),
                (lambda: state.in_game and rooms(window_title), "rooms", lambda: None),
                (lambda: jixu(window_title), "jixu", lambda: setattr(state, 'in_game', False)),
                (lambda: jixu1(window_title), "jixu1", lambda: setattr(state, 'in_game', False)),
                (lambda: queding(window_title), "queding", lambda: None),
                (lambda: fenxiangzhanji(window_title), "fenxiangzhanji", lambda: setattr(state, 'in_game', False)),
                (lambda: state.in_game and marks(window_title), "marks", lambda: None),
            ]

            for detect, name, action in events:
                try:
                    if detect():
                        action()
                        break
                except Exception:
                    # 单个检测函数出错不应终止主循环
                    pass

            now = time.time()
            if state.in_game and now - state.anquan_ts >= ANQUAN_INTERVAL:
                try:
                    anquanqu(window_title)
                except Exception:
                    pass
                print('每三分钟一次安全区')
                state.anquan_ts = now

            if handle_stuck(frame):
                state.in_game = True

            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\n已停止运行")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="运行 AI PUBG 自动化 (aigameplayer)")
    parser.add_argument("--model", "-m", default=DEFAULT_MODEL_PATH, help="YOLO 模型路径")
    parser.add_argument("--window-title", "-w", default=WINDOW_TITLE, help="窗口标题前缀")
    args = parser.parse_args()

    WINDOW_TITLE = args.window_title
    load_model(args.model)
    main_loop(WINDOW_TITLE)