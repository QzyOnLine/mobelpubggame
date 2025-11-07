# train_yolo11n.py
from ultralytics import YOLO
import os

# 1. 基础路径
data_root = r"D:\VS_Code\qzy\anquanqu"         # 你的训练集根目录
data_yaml = os.path.join(data_root, "data.yaml")  # 数据集配置文件
modelname="yolo11n.pt"    #加载模型名字
yourname="anquanqu"           #保存的文件夹名字
# 2. 若第一次跑，自动生成最小 data.yaml（单类示例）
if not os.path.exists(data_yaml):
    with open(data_yaml, "w", encoding="utf-8") as f:
        f.write(f"""
path: {data_root}       # 数据集根目录
train: train/images     # 训练图片相对路径
val: train/images       # 没单独验证集时复用训练集
nc:   11                 # 类别数
names: [anquanqu,
box,
fenxiangzhanji,
jixu,
jixu1,
kaishiyouxi,
likai,
mark,
person,
queding,
room]        # 类别名称
""")
    print("✅ 已生成 data.yaml，请检查路径/类别是否正确！")

# 3. 加载模型（自动下载 yolo11n.pt）
model = YOLO(modelname)

# 4. 开始训练
model.train(
    data=data_yaml,
    epochs=500,        # 训练轮数，可改成 50/200，过多训练慢和过拟合
    imgsz=1280,        #训练照片尺寸
    batch=4,          # -1 自动根据内存调
    device='cpu',      # 有 GPU 改成 device=0
    workers=0,         # CPU 训练时设 0 避免多线程错误
    project=r"D:\VS_Code\pubggame\runs\train",
    name=yourname
)