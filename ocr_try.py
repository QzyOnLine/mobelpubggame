# -*- coding: utf-8 -*-
"""
adb_fullshot → 全图OCR → 关键字匹配 → 返回中心坐标
"""
import os
import subprocess
from paddleocr import PaddleOCR
from PIL import Image

# ---------- 配置 ----------
SAVE_DIR   = "Screenshots"
FULL_PATH  = os.path.join(SAVE_DIR, "capture.png")   # adb 拉取后保存的完整图
ocr = PaddleOCR(lang='ch', device='cpu')
REMOTE_TMP = "/sdcard/screen.png"
# --------------------------

def adb_fullshot():
    """保证生成 FULL_PATH"""
    os.makedirs(SAVE_DIR, exist_ok=True)
    subprocess.run(["adb", "shell", "screencap", "-p", REMOTE_TMP], check=True)
    subprocess.run(["adb", "pull", REMOTE_TMP, FULL_PATH], check=True)
    subprocess.run(["adb", "shell", "rm", REMOTE_TMP], check=False)
    print(f"[adb] 完整图 → {FULL_PATH}")

def find_keyword_coords(keyword):
    adb_fullshot()
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

# ---------- 测试 ----------
if __name__ == "__main__":
    kw = "活动"
    coord = find_keyword_coords(kw)
    if coord:
        print("可直接 touch.tap：", coord)