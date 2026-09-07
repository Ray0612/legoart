import numpy as np
from PIL import Image, ImageFilter
import sys
import os

# ================== 参数（与问题一完全一致） ==================
mm_per_pixel = 0.5                           # 输出精度 (mm/pixel)
OUTPUT_DIR = r"outcomes"                     # 输出文件夹
fill_color = (255, 255, 255)                 # 空白填充色：白色（事实上加粗不会产生新空白）

# ================== 线条加粗函数 ==================
def thicken_paper(paper_img, radius_mm):
    """
    对纸面图中的黑色线条进行加粗（全向均匀加粗）。
    
    参数：
        paper_img : numpy array (H x W x 3) 或 (H, W)
        radius_mm : 加粗半径 (mm)，线条向两侧各扩展 radius_mm
    返回：
        加粗后的图像 (numpy array)，尺寸与原图相同
    """
    # 计算像素半径，并转为奇数（MinFilter 要求奇数尺寸）
    radius_pix = radius_mm / mm_per_pixel
    # 取最近的奇数，且至少为3
    size = int(round(radius_pix * 2 + 1))   # 直径
    if size % 2 == 0:
        size += 1
    size = max(3, size)

    pil_img = Image.fromarray(paper_img)
    # 使用最小值滤波器（腐蚀），黑色线条会变粗
    # 若原图为彩色，先转为灰度再处理可能更好，但保持RGB模式直接滤波也可
    # 注意：MinFilter 在 RGB 图像上对每个通道独立做最小值滤波，效果等同于整体变暗
    thickened = pil_img.filter(ImageFilter.MinFilter(size))
    return np.array(thickened)

# ================== 命令行入口 ==================
if __name__ == "__main__":
    # 灵活选择：命令行参数 或 直接写死
    if len(sys.argv) == 3:
        # python thicken_perturb.py <输入图> <加粗半径_mm>
        input_path = sys.argv[1]
        radius = float(sys.argv[2])
    else:
        # 默认参数模式（方便调试）
        input_path = r"pic\图3.png"          # 👈 修改你的输入路径
        radius = 3.0                         # 加粗半径 (mm)

    # 读取纸面图
    paper = np.array(Image.open(input_path).convert('RGB'))

    # 执行加粗
    paper_thick = thicken_paper(paper, radius)

    # 生成输出文件名
    desc = f"thicken={radius}mm"
    out_name = f"paper_thickened_{desc}.png"

    # 保存到输出目录
    full_out_path = os.path.join(OUTPUT_DIR, out_name)
    os.makedirs(os.path.dirname(full_out_path), exist_ok=True)
    Image.fromarray(paper_thick).save(full_out_path)
    print(f"加粗扰动纸面图已保存至 {full_out_path}")