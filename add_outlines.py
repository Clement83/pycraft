import os
import sys
from PIL import Image, ImageOps

def add_outline_to_textures():
    assets_dir = "assets"
    for filename in os.listdir(assets_dir):
        if filename.endswith(".png"):
            filepath = os.path.join(assets_dir, filename)
            try:
                img = Image.open(filepath)
                # Add a 1-pixel black border
                img_with_border = ImageOps.expand(img, border=1, fill='black')
                img_with_border.save(filepath)
                print(f"Added outline to {filename}")
            except Exception as e:
                print(f"Could not process {filename}: {e}")

if __name__ == "__main__":
    try:
        from PIL import Image, ImageOps
    except ImportError:
        print("Pillow library not found. Please install it by running: pip install Pillow")
        sys.exit(1)
    add_outline_to_textures()
