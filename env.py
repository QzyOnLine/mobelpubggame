# -------------- 用户填写 --------------
VENV_DIR = r"D:\VS_Code\pubggame\yolo_env"  # ←←← 改成你的虚拟环境路径
# -------------- 用户填写 --------------

import os
import sys
import subprocess
import argparse

def main():
    # 检测平台
    is_win = sys.platform.startswith("win")

    # 构造激活命令
    if is_win:
        activate_script = os.path.join(VENV_DIR, "Scripts", "activate.bat")
        cmd = [activate_script]
        if not os.path.isfile(activate_script):
            print(f"激活脚本不存在：{activate_script}")
            return
        # 让激活后的 cmd 保持打开
        subprocess.run(f'start cmd /k "{activate_script}"', shell=True)
    else:
        activate_script = os.path.join(VENV_DIR, "bin", "activate")
        if not os.path.isfile(activate_script):
            print(f"激活脚本不存在：{activate_script}")
            return
        # Linux/macOS 用 bash 保持交互
        subprocess.run(["bash", "--rcfile", activate_script, "-i"])

if __name__ == "__main__":
    main()