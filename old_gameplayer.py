#!/usr/bin/env python3
import cv2
import numpy as np
from PIL import ImageGrab
#from PIL import Image
from ultralytics import YOLO
import time
import touch

model = YOLO("yolo11n.pt")
ROI = (580, 500, 1580, 940)          # 屏幕裁剪区域
CONF_THRES = 0.4                     # 置信度门槛
INTERVAL   = 0.55                       # 秒，检测间隔

def main():
    print("按 q 退出")
    last_t = 0
    while True:
        t0 = time.time()
        if t0 - last_t < INTERVAL:          # 限速：1 秒 1 帧
            time.sleep(0.05)
            continue
        last_t = t0

        # ① 截屏并裁剪 ROI
        img = ImageGrab.grab(bbox=ROI)
        frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

        # ② YOLO 推理（返回所有类别框）
        results = model(frame, verbose=False)[0]
        annotated = results.plot()          # 画所有框

        # ③ 只找 person（class 0）且置信度 ≥ 0.4
        persons = [d for d in results.boxes.data if int(d[5]) == 0 and d[4] >= CONF_THRES]
        if persons:
            best = max(persons, key=lambda x: x[4])   # 取置信度最高
            x1, y1, x2, y2, conf = best[:5]
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)
            touch.swipe1(cx, cy)  
            touch.tap(400,220)
            #touch.tap(2024,175)
            #touch.longtap(400,220)                    # 触发点击/滑动
            #touch.tap(2024,175)
            cv2.circle(annotated, (cx, cy), 5, (0, 0, 255), -1)
            print(f"\r高可信 person 中心: ({cx}, {cy})  conf:{conf:.2f}", end="")
        else:
            print("\r未检测到高可信 person", end="")

        # ④ 显示
        cv2.imshow("YOLO 全框 + person 中心", annotated)
        #Image.fromarray(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)).show()
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()