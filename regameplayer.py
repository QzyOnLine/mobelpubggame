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
import adb_once
import time, functools
import ADBconnect

run_flag = threading.Event() 
ctypes.windll.user32.SetProcessDPIAware()   # 高 DPI 不缩放

model = YOLO(r"D:\VS_Code\pubggame\runs\train\anquanqu\weights\last.pt") #加载模型
CONF_THRES = 0.4  #模型判断置信度
INTERVAL   = 0.55    #
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

import cv2
from functools import lru_cache

# ========== 内部状态闭包 ==========
# 用 lru_cache 把「上一帧灰度 + 连续计数」包成闭包，外部零可见、零全局变量
@lru_cache(maxsize=1)          # 只缓存 1 次，相当于单例
def _stuck_state():
    """返回 [last_gray, stuck_cnt] 的可变列表，外部无法直接访问"""
    return [None, 0]             # [0] 上一帧灰图  [1] 连续相似帧数


# ========== 角色卡住处理 ==========
def handle_stuck(img_bgr,
                 thres: float = 0.795,
                 frames: int = 30):
    state = _stuck_state()
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # ① 首次或尺寸变化 → 重置
    if state[0] is None or state[0].shape != gray.shape:
        state[0] = gray
        state[1] = 0
        return False

    # ② 保证模板 ≤ 原图（宽高都小于等于）
    h1, w1 = state[0].shape
    h2, w2 = gray.shape
    if h1 > h2 or w1 > w2:
        # 当前帧更小，无法匹配 → 重置
        state[0] = gray
        state[1] = 0
        return False

    # ③ 正常匹配
    diff = cv2.matchTemplate(gray, state[0], cv2.TM_CCOEFF_NORMED)[0][0]
    state[0] = gray

    if diff > thres:
        state[1] += 1
    else:
        state[1] = 0

    if state[1] >= frames:
        state[1] = 0
        ADBconnect.open_pubg()
        touch.swipe(1910, 720, 1500, 700)
        touch.tap(2200, 660)
        print('卡死自救')
        return True
    return False


def get_client_size(hwnd):
    """返回窗口客户区宽高"""
    rect = win32gui.GetClientRect(hwnd)
    return rect[2], rect[3]

'''坐标映射：将投屏在win上的坐标映射回原设备上'''
def map_yolo_to_device(yolo_coords,
                       hwnd,
                       device_w=2412,
                       device_h=1080):
    # 把 Tensor→float，防 round 报错
    x1, y1, x2, y2 = [float(x) for x in yolo_coords]

    window_w, window_h = get_client_size(hwnd)
    sx = device_w / window_w
    sy = device_h / window_h

    return (int(round(x1 * sx)),
            int(round(y1 * sy)),
            int(round(x2 * sx)),
            int(round(y2 * sy)))

'''每隔一段时间截屏用于标注再训练'''
_last_shot = 0          # 时间戳（秒）
_MIN_INTERVAL = 20 * 60  # 20 分钟
def throttle_adb_shot():
    """4 分钟内只允许执行一次"""
    global _last_shot
    now = time.time()
    if now - _last_shot >= _MIN_INTERVAL:
        _last_shot = now
        adb_once.adb_screenshot()
        # 如果想把截图文件也加上时间戳，可在这里做

'''简陋的计时器，每隔一段时间返回true，用于定时任务'''
_last_tick = 0             # 上次执行时刻的全局变量
def should_run(now,INTERVAL = 3 * 60 ):
    """非阻塞定时器：到点返回 True"""
    global _last_tick        #global能修改全局变量
    if now - _last_tick >= INTERVAL:
        _last_tick = now
        return True
    return False

'''检测离开按钮，检测到之后等待一段时间点击该按钮实现跳伞功能'''
def likai():
    hwnd = find_win()
    if not hwnd:
        print("未找到窗口，请先运行 scrcpy"); return
    frame = grab_win(hwnd)          # ← 替换 ImageGrab
    results = model(frame, verbose=False)[0]
    likai = [
    d for d in results.boxes.data
    if model.names[int(d[5])] == 'likai' and d[4] >= CONF_THRES    ]
    if not likai:               # ← 新增
        print("\r未检测到类别 likai", end="")
        return False
    print("\r检测到类别 likai", end="")
    best = max(likai, key=lambda x: x[4])
    x1, y1, x2, y2 = map_yolo_to_device(best[:4], hwnd=hwnd)
    cx = int((x1 + x2) / 2)
    cy = int((y1 + y2) / 2)
    time.sleep(28)
    touch.tap(cx, cy) 
    return True   
    
'''打开地图并检测安全区位置并标记中心区域'''    
def anquanqu():
    hwnd = find_win()
    if not hwnd:
        print("未找到窗口，请先运行 scrcpy"); return
    
    touch.tap(1560,125)        #小地图坐标，按需更改
    #time.sleep(0.5)
    frame = grab_win(hwnd)       
    results = model(frame, verbose=False)[0]
    anquanqu = [
        d for d in results.boxes.data
        if model.names[int(d[5])] == 'anquanqu' and d[4] >= CONF_THRES    ]
    #print('开始找安全区')
    if not anquanqu:
        #print('没有找到安全区')
        touch.tap(2280,80)
        return False
    else:
        #print('安全区找到了')
        best = max(anquanqu, key=lambda x: x[4])
        x1, y1, x2, y2 = map_yolo_to_device(best[:4], hwnd=hwnd)
        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)
        touch.tap(cx,cy)
    touch.tap(2280,80)        #关闭地图
    return True

'''检测盒子并执行操作，暂时不完善，未启动'''
def boxs():
    for _ in range(3):
        hwnd = find_win()
        if not hwnd:
            print("未找到窗口，请先运行 scrcpy"); return
        
        frame = grab_win(hwnd)          # ← 替换 ImageGrab
        results = model(frame, verbose=False)[0]
        #boxs   = [d for d in results.boxes.data if int(d[5]) == 0 and d[4] >= CONF_THRES]
        boxs = [
        d for d in results.boxes.data
        if model.names[int(d[5])] == 'box' and d[4] >= CONF_THRES    ]
        if not boxs:               # ← 新增
            print("\r未检测到类别 boxs", end="")
            return None
        print("\r检测到类别 boxs", end="")
        best = max(boxs, key=lambda x: x[4])
        x1, y1, x2, y2 = map_yolo_to_device(best[:4], hwnd=hwnd)
        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)
        touch.swipe1(cx, cy)
        touch.swipe(320,770,400,440)
        time.sleep(1)
        touch.tap(320,770)
        touch.tap(1520,440)
        time.sleep(3)
        return True 

'''根据安全区位置标记进行跑图'''
def marks():
    hwnd = find_win()
    if not hwnd:
        print("未找到窗口，请先运行 scrcpy"); return
    
    frame = grab_win(hwnd)          # ← 替换 ImageGrab
    results = model(frame, verbose=False)[0]
    #marks   = [d for d in results.boxes.data if int(d[5]) == 5 and d[4] >= CONF_THRES]
    marks = [
        d for d in results.boxes.data
        if model.names[int(d[5])] == 'mark' and d[4] >= CONF_THRES    ]
    if not marks:               # ← 新增
        print("\r未检测到类别 marks", end="")
        anquanqu()
        return None
    #print("\r检测到类别 marks", end="")
    best = max(marks, key=lambda x: x[4])
    x1, y1, x2, y2 = map_yolo_to_device(best[:4], hwnd=hwnd)
    cx = int((x1 + x2) / 2)
    cy = int((y1 + y2) / 2)
    touch.swipe1(cx, 540)
    touch.swipe(320,770,400,440)
    return True 

'''检测到人之后将准心对准人中心并点击开火键'''
def persons():
    touch.tap(320, 770)
    hwnd = find_win()
    if not hwnd:
        print("未找到窗口，请先运行 scrcpy"); return
    
    frame = grab_win(hwnd)          # ← 替换 ImageGrab
    results = model(frame, verbose=False)[0]
    #persons = [d for d in results.boxes.data if int(d[5]) == 6 and d[4] >= CONF_THRES]
    persons = [
        d for d in results.boxes.data
        if model.names[int(d[5])] == 'person' and d[4] >= CONF_THRES    ]
    if not persons:               # ← 新增
        print("\r未检测到类别 persons", end="")
        return False
    print("\r检测到类别 persons", end="")
    best = max(persons, key=lambda x: x[4])
    x1, y1, x2, y2 = map_yolo_to_device(best[:4], hwnd=hwnd)
    cx = int((x1 + x2) / 2)
    cy = int((y1 + y2) / 2)
    #print(f"中心坐标（相对窗口）: ({cx}, {cy})")
    touch.swipe1(cx, cy)
    touch.tap(400, 220)
    touch.tap(1000,830)    
    return True 

'''检测到门之后将门放到侧边，不会进入室内卡住'''
def rooms():
    hwnd = find_win()
    if not hwnd:
        print("未找到窗口，请先运行 scrcpy"); return
    
    frame = grab_win(hwnd)          # ← 替换 ImageGrab
    results = model(frame, verbose=False)[0]
    #rooms = [d for d in results.boxes.data if int(d[5]) == 8 and d[4] >= CONF_THRES]
    rooms = [
        d for d in results.boxes.data
        if model.names[int(d[5])] == 'room' and d[4] >= CONF_THRES    ]
    if not rooms:               # ← 新增
        print("\r未检测到类别 rooms", end="")
        return None
    print("\r检测到类别 rooms", end="")
    best = max(rooms, key=lambda x: x[4])
    x1, y1, x2, y2 = map_yolo_to_device(best[:4], hwnd=hwnd)
    cx = int((x1 + x2) / 2)
    cy = int((y1 + y2) / 2)
    touch.swipe2(cx, cy)
    touch.swipe(320,770,400,440)
    return True 

'''检测开始游戏并点击'''
def kaishiyouxi():
    hwnd = find_win()
    if not hwnd:
        print("未找到窗口，请先运行 scrcpy"); return
    
    frame = grab_win(hwnd)          # ← 替换 ImageGrab
    results = model(frame, verbose=False)[0]
    #kaishiyouxi = [d for d in results.boxes.data if int(d[5]) == 4 and d[4] >= CONF_THRES]
    kaishiyouxi = [
        d for d in results.boxes.data
        if model.names[int(d[5])] == 'kaishiyouxi' and d[4] >= CONF_THRES    ]    
    if not kaishiyouxi:               # ← 新增
        print("\r未检测到类别 kaishiyouxi", end="")
        return None
    print("\r检测到类别 kaishiyouxi", end="")
    best = max(kaishiyouxi, key=lambda x: x[4])
    x1, y1, x2, y2 = map_yolo_to_device(best[:4], hwnd=hwnd)
    cx = int((x1 + x2) / 2)
    cy = int((y1 + y2) / 2)
    print('类别 kaishiyouxi',cx,cy)
    touch.tap(cx, cy)
    return True 

'''检测继续并点击'''
def jixu():
    hwnd = find_win()
    if not hwnd:
        print("未找到窗口，请先运行 scrcpy"); return
    
    frame = grab_win(hwnd)          # ← 替换 ImageGrab
    results = model(frame, verbose=False)[0]
    #jixu = [d for d in results.boxes.data if int(d[5]) == 2 and d[4] >= CONF_THRES]
    jixu = [
        d for d in results.boxes.data
        if model.names[int(d[5])] == 'jixu' and d[4] >= CONF_THRES    ]
    if not jixu:               # ← 新增
        print("\r未检测到类别 jixu", end="")
        return None
    print("\r检测到类别 jixu", end="")
    best = max(jixu, key=lambda x: x[4])
    x1, y1, x2, y2 = map_yolo_to_device(best[:4], hwnd=hwnd)
    cx = int((x1 + x2) / 2)
    cy = int((y1 + y2) / 2)
    print('类别 jixu',cx,cy)
    touch.tap(cx, cy)
    return True 

'''检测继续并点击'''
def jixu1():
    hwnd = find_win()
    if not hwnd:
        print("未找到窗口，请先运行 scrcpy"); return
    
    frame = grab_win(hwnd)          # ← 替换 ImageGrab
    results = model(frame, verbose=False)[0]
    #jixu1 = [d for d in results.boxes.data if int(d[5]) == 3 and d[4] >= CONF_THRES]
    jixu1 = [
        d for d in results.boxes.data
        if model.names[int(d[5])] == 'jixu1' and d[4] >= CONF_THRES    ]
    if not jixu1:               # ← 新增
        print("\r未检测到类别 jixu1", end="")
        return None
    print("\r检测到类别 jixu1", end="")
    best = max(jixu1, key=lambda x: x[4])
    x1, y1, x2, y2 = map_yolo_to_device(best[:4], hwnd=hwnd)
    cx = int((x1 + x2) / 2)
    cy = int((y1 + y2) / 2)
    print('类别 jixu1',cx,cy)
    touch.tap(cx, cy)
    return True 

'''检测确定并点击'''
def queding():
    hwnd = find_win()
    if not hwnd:
        print("未找到窗口，请先运行 scrcpy"); return
    
    frame = grab_win(hwnd)          # ← 替换 ImageGrab
    results = model(frame, verbose=False)[0]
    #queding = [d for d in results.boxes.data if int(d[5]) == 7 and d[4] >= CONF_THRES]
    queding = [
        d for d in results.boxes.data
        if model.names[int(d[5])] == 'queding' and d[4] >= CONF_THRES    ]
    if not queding:               # ← 新增
        print("\r未检测到类别 queding", end="")
        return None
    print("\r检测到类别 queding", end="")
    best = max(queding, key=lambda x: x[4])
    x1, y1, x2, y2 = map_yolo_to_device(best[:4], hwnd=hwnd)
    cx = int((x1 + x2) / 2)
    cy = int((y1 + y2) / 2)
    print('类别 queding',cx,cy)
    touch.tap(cx, cy)
    return True 

'''检测分享游戏并点击左边的按钮'''
def fenxiangzhanji():
    hwnd = find_win()
    if not hwnd:
        print("未找到窗口，请先运行 scrcpy"); return
    frame = grab_win(hwnd)          # ← 替换 ImageGrab
    results = model(frame, verbose=False)[0]
    #fenxiangzhanji = [d for d in results.boxes.data if int(d[5]) == 1 and d[4] >= CONF_THRES]
    fenxiangzhanji = [
        d for d in results.boxes.data
        if model.names[int(d[5])] == 'fenxiangzhanji' and d[4] >= CONF_THRES    ]
    if not fenxiangzhanji:               # ← 新增
        print("\r未检测到类别 fenxiangzhanji", end="")
        return None
    print("\r检测到类别 fenxiangzhanji", end="")
    best = max(fenxiangzhanji, key=lambda x: x[4])
    x1, y1, x2, y2 = map_yolo_to_device(best[:4], hwnd=hwnd)
    cx = int(((x1 + x2) / 2)-250)
    cy = int((y1 + y2) / 2)
    print('类别 fenxiangzhanji',cx,cy)
    touch.tap(cx, cy)
    return True 

'''状态机重置'''
class State:
    def __init__(self):
        self.in_game   = True      # 是否在游戏内
        self.did_likai = False      # 本局是否已点离开
        self.anquan_ts = 0          # 上次 anquanqu 时间戳

def main():
    # ---------- 配置 ----------
    ANQUAN_INTERVAL = 3 * 60       # 3 分钟
    # --------------------------

    state = State()                # 统一状态机

    while True:
        hwnd = find_win()
        if not hwnd:
            print("未找到窗口，请先运行 scrcpy"); return

        frame = grab_win(hwnd)

        '''不在对局内就点击开始游戏，在对局内就点击确定，继续等，判断安全区并跑毒'''
        # 事件表（顺序 = 优先级）
        events = [
            # 0️⃣ 每局首次离屏
            (lambda: state.in_game and not state.did_likai and likai(), "likai",
             lambda: setattr(state, 'did_likai', True)),

            # 1️⃣ 正常按钮链
            (lambda: not state.in_game and kaishiyouxi(), "kaishiyouxi",
            lambda: (setattr(state, 'in_game', True),
                     setattr(state, 'did_likai', False))),
            (lambda: state.in_game and rooms(),         "rooms",        lambda: None),
            (jixu,          "jixu",         lambda: setattr(state, 'in_game', False)),
            (jixu1,         "jixu1",        lambda: setattr(state, 'in_game', False)),
            (queding,       "queding",      lambda: None),
            (fenxiangzhanji,"fenxiangzhanji",lambda: setattr(state, 'in_game', False)),
            (lambda: state.in_game and marks(), "marks", lambda: None),
        ]

        # 执行第一个命中事件
        for detect, name, action in events:
            if detect():
                #print(f'点击 {name}')
                action()
                break

        # 3 分钟安全区
        now = time.time()
        if state.in_game and now - state.anquan_ts >= ANQUAN_INTERVAL:
            anquanqu()
            print('每三分钟一次安全区')
            state.anquan_ts = now

        # 卡住保护
        handle_stuck(frame)  # 返回 True → 已强制点击



if __name__ == "__main__":
        main()
