from PIL import Image, ImageDraw
import os
import sys
from pathlib import Path


def generate_default_icon():
    # Use absolute path of the current script's parent (scripts directory)
    current_dir = Path(__file__).parent.resolve()
    project_root = current_dir.parent
    resources_dir = project_root / "resources"

    if not resources_dir.exists():
        resources_dir.mkdir(parents=True)

    icon_path = resources_dir / "icon.ico"

    print(f"Generating icon at: {icon_path}")

    # 256x256 の赤い円を描画
    img = Image.new('RGB', (256, 256), color='white')
    draw = ImageDraw.Draw(img)

    # 円を描画
    draw.ellipse([10, 10, 246, 246], fill='red', outline='darkred', width=5)

    # テキストを描画したかったが、フォント周りが環境依存なのでシンプルに図形のみにする
    # 中心に四角を描く（ATMっぽい？）
    draw.rectangle([80, 100, 176, 180], fill='white', outline='black', width=3)

    # ICO形式で保存
    img.save(icon_path, format='ICO')
    print("✓ Icon generated successfully")


if __name__ == '__main__':
    generate_default_icon()
