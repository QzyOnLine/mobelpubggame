# -*- coding: utf-8 -*-
"""
只换截图来源：adb → 本地 → 原有函数裁剪/识别
"""
import threading
import os
import subprocess
import datetime
import gameplayer
from PIL import Image
from PIL import ImageGrab   # 保留，因为 shot_area 内部仍用 ImageGrab.grab(bbox=...)
from paddleocr import PaddleOCR
import touch
import time

# ========== 原参数 ==========
SAVE_DIR = "Screenshots"
FILE_NAME = "capture.png"
FILE_NAME1 = "capture1.png"
#ocr = PaddleOCR(lang='ch', device='cpu')
ocr = PaddleOCR(lang='ch', device='cpu', use_angle_cls=False)
running = True          # True 表示 gameplayer 当前正在跑
REMOTE_TMP = "/sdcard/screen.png"   # 设备端临时路径
FULL_PATH = os.path.join(SAVE_DIR, FILE_NAME)  # 本地完整图固定路径
FULL_PATH1= os.path.join(SAVE_DIR, FILE_NAME1) 
# ============================

def adb_fullshot():
    """保证生成 FULL_PATH，否则抛异常"""
    os.makedirs(SAVE_DIR, exist_ok=True)
    tmp = os.path.join(SAVE_DIR, "capture.png")   # 临时文件

    # 0. 如果临时文件已存在，先删掉（避免 adb pull 提示覆盖）
    if os.path.isfile(tmp):
        os.remove(tmp)

    # 1. 截屏
    subprocess.run(["adb", "shell", "screencap", "-p", REMOTE_TMP], check=True)
    # 2. 拉取（用绝对路径，避免空格/中文干扰）
    subprocess.run(["adb", "pull", REMOTE_TMP, tmp], check=True)
    # 3. 可选：删除设备端
    subprocess.run(["adb", "shell", "rm", REMOTE_TMP], check=False)

    print(f"[adb] 完整图已更新 → {tmp}")


def find_keyword_coords1(keyword):
    result = ocr.predict(FULL_PATH)   # 返回 [dict]
    if not result:                    # 空 list
        print("OCR 未返回任何结果")
        return None

    data = result[0]                  # 真正的字典
    texts  = data.get('rec_texts', [])
    boxes  = data.get('rec_boxes', [])  # shape=(N,4)  [[x1,y1,x2,y2], ...]

    for text, box in zip(texts, boxes):
        if keyword in text:
            # box 是 [x1,y1,x2,y2] → 取中心
            x1, y1, x2, y2 = box
            cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
            print(f"找到关键字『{keyword}』中心坐标：{cx, cy}")
            return cx, cy

    print(f"关键字『{keyword}』未找到")
    return None

def shot_area(x1, y1, x2, y2, delete_old=True):
    """依旧读 FULL_PATH，再裁剪指定 bbox 并覆盖 FILE_NAME"""
    AREA = (x1, y1, x2, y2)
    os.makedirs(SAVE_DIR, exist_ok=True)
    save_path = os.path.join(SAVE_DIR, FILE_NAME1)

    if delete_old and os.path.isfile(save_path):
        os.remove(save_path)

    # 从完整图里裁剪，而不是 ImageGrab.grab 屏幕
    img = Image.open(FULL_PATH).crop(AREA)
    img.save(save_path)
    print(f"截图已保存 → {save_path}")


def myocr(target_text):
    result = list(ocr.predict(os.path.join(SAVE_DIR, FILE_NAME1)))  # 目录里只有 FILE_NAME
    if result:
        texts = result[0]['rec_texts']
        if target_text in texts:
            print(f"找到关键字：{target_text}")
            return True
        print(f"未找到关键字：{target_text}")
    else:
        print("未检测到文字")


def myocr1():
    result = list(ocr.predict(os.path.join(SAVE_DIR, FILE_NAME1)))
    if not result:
        return []
    texts = result[0].get('rec_texts', [])
    numbers = [float(t) for t in texts if t.replace('.', '', 1).isdigit()]
    print(numbers)
    return numbers

def yolo_start():
    global running
    if not running:
        gameplayer.run_flag.set()
        print("[OCR] gameplayer 已开启")
        running = True

def yolo_stop():
    global running
    if running:
        gameplayer.run_flag.clear()
        print("[OCR] gameplayer 已暂停")
        running = False

def yolo_quit():
    """彻底结束 gameplayer 线程"""
    gameplayer.run_flag.set()        # 先放行
    gameplayer.run_flag = None       # 让循环 break
    gameplayer._thread.join()
    print("[OCR] gameplayer 线程已退出")

def ocr_once():
    """返回 texts, boxes 两个列表"""
    result = ocr.predict(FULL_PATH)
    if not result:
        return [], []
    data = result[0]
    return data.get('rec_texts', []), data.get('rec_boxes', [])

def find_keywords_coords(keywords):
    texts, boxes = ocr_once()          # 只跑一次模型
    hits = {}
    for kw in keywords:
        for text, box in zip(texts, boxes):
            if kw in text:
                x1, y1, x2, y2 = box
                hits[kw] = (int((x1 + x2) / 2), int((y1 + y2) / 2))
                break      # 每个关键字只取第一个匹配
    return hits

def main():
    while True:
        adb_fullshot()
        hits = find_keywords_coords(("开始游戏", "继续", "返回", "确定"))
        if "开始游戏" in hits:
            touch.tap(*hits["开始游戏"]); yolo_start()
        elif "继续" in hits:
            yolo_stop(); touch.tap(*hits["继续"])
        elif "返回" in hits:
            yolo_stop(); touch.tap(*hits["返回"])
        elif "确定" in hits:
            touch.tap(*hits["确定"])
        else:
            print('没有找到')
            time.sleep(5)


if __name__ == "__main__":
    main()

'''
def main():
    keywords = ("开始游戏", "继续", "返回", "确定")   # 顺序不可变
    while True:
        adb_fullshot()
        coords = {kw: find_keyword_coords1(kw) for kw in keywords}

        if coords["开始游戏"]:
            cx, cy = coords["开始游戏"]
            touch.tap(cx, cy)
            time.sleep(1)
            yolo_start()
        elif coords["继续"]:
            yolo_stop()
            cx, cy = coords["继续"]
            touch.tap(cx, cy)
        elif coords["返回"]:
            yolo_stop()
            cx, cy = coords["返回"]
            touch.tap(cx, cy)
        elif coords["确定"]:
            cx, cy = coords["确定"]
            touch.tap(cx, cy)
        else:
            print("未命中任何关键字，5 秒后重试")
            time.sleep(5)

if __name__ == "__main__":
    main()
'''

'''
# ============== 主循环也保持原样 ==============
def main():
    while True:
        loop = True
        while loop:
            adb_fullshot()          # ① 先更新完整图
            shot_area(0,0,460,140)  # ② 裁剪→识别
            rul = myocr('开始游戏')
            if rul:
                touch.tap(260, 80)
                loop = not rul

        loop1 = True
        while loop1:
            adb_fullshot()
            shot_area(1520,130, 1590,210)
            nums = myocr1()
            if nums:
                first = nums[0] + 50
                touch.tap(1200,780)   #小黑屋点击
                time.sleep(first)
                touch.tap(440, 440)
                loop1 = False
                yolo_start() 
            time.sleep(3)

        time.sleep(300)
        loop2 = True
        while loop2:
            time.sleep(20)
            adb_fullshot()          # ① 先更新完整图
            shot_area(1540,960,1970,1048)  # ② 裁剪→识别
            rul = myocr('继续')
            if rul:
                yolo_stop()
                #touch.tap(1900,1000)
                time.sleep(3)
                touch.tap(1600,1000)
                time.sleep(3)
                touch.tap(2100,1000)
                time.sleep(3)
                touch.tap(1600,1000)
                time.sleep(25)
                touch.tap(1200,1000)
                loop2 = not rul
'''

