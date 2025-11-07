from ultralytics import YOLO
import pathlib, sys

# ========== ① 用户只需要改这里 ==========
weight_path = r"D:\VS_Code\pubggame\runs\train\yolo11n_person\weights\last.pt"  # 你的权重
image_path  = r"D:\VS_Code\person\val\images"                               # 单张或文件夹
# ========================================

# 加载模型（自动下载 yolo11n 骨架）
model = YOLO(weight_path)

# 推理 + 保存结果
results = model.predict(
    source=image_path,
    imgsz=1280,        # 与训练一致即可
    conf=0.25,         # 置信度阈值
    iou=0.45,          # NMS 阈值
    device='cpu',      # 有 GPU 可改 '0'
    save=True,         # 保存画框图
    project='runs/infer',
    name='yolo11_infer'
)

# （可选）弹窗看第一张结果
if __name__ == '__main__':
    import cv2
    cv2.imshow('YOLO11 Result', cv2.imread(results[0].save_path))
    cv2.waitKey(0)
    cv2.destroyAllWindows()