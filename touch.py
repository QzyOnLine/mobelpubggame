import os
import time

x0,y0=1910,720
lmd=0.35

def tap(x, y):
    os.system(f"adb shell input tap {x} {y}")
    time.sleep(3)


def longtap(x, y, t=1500):
    os.system(f"adb shell input swipe {x} {y} {x} {y} {t}")

def swipe(x1, y1,x2,y2, t=500):
    os.system(f"adb shell input swipe {x1} {y1} {x2} {y2} {t}")

def swipe1(x2,y2, t=300):
    x1=x2-1204
    y1=y2-540
    x=x0+x1*lmd
    y=y0+y1*lmd
    os.system(f"adb shell input swipe {x0} {y0} {x} {y} {t}")

def swipe2(x2,y2, t=300):
    x1=x2-2300
    y1=y2-540
    x=x0+x1*lmd
    y=y0+y1*lmd
    os.system(f"adb shell input swipe {x0} {y0} {x} {y} {t}")