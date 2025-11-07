#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
adb_once_dir.py
一键截图：运行一次截一次，保存到当前目录的 screenshots/ 文件夹
"""

import subprocess
import datetime
import os
import sys

SAVE_DIR = "screenshots"          # 当前目录下的子文件夹
REMOTE_TMP = "/sdcard/screen.png" # 设备端临时路径

def adb_screenshot():
    # 1. 确保保存目录存在
    os.makedirs(SAVE_DIR, exist_ok=True)

    # 2. 生成文件名
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    local_file = os.path.join(SAVE_DIR, f"screenshot_{timestamp}.png")

    # 3. 截屏 → 拉取 → 删除临时文件
    subprocess.run(["adb", "shell", "screencap", "-p", REMOTE_TMP], check=True)
    subprocess.run(["adb", "pull", REMOTE_TMP, local_file], check=True)
    subprocess.run(["adb", "shell", "rm", REMOTE_TMP], check=False)

    print(f"截图已保存：{os.path.abspath(local_file)}")

if __name__ == "__main__":
    try:
        adb_screenshot()
    except subprocess.CalledProcessError as e:
        print("adb 执行失败，请检查设备是否已连接并授权：", e)
        sys.exit(1)