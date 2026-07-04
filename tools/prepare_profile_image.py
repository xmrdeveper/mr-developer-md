"""Prepare profile images for Telegram and WhatsApp.
Usage:
  python tools/prepare_profile_image.py input.png

This script produces two files in the current directory:
  - output_512.jpg  (recommended for Telegram/BotFather)
  - output_640.jpg  (recommended for WhatsApp profile)

It crops the image to a centered square and resizes with high-quality resampling.
"""
from PIL import Image
import sys

def make_square(src_path, size, out_path):
    im = Image.open(src_path).convert('RGBA')
    w, h = im.size
    scale = max(size / w, size / h)
    nw, nh = int(w * scale), int(h * scale)
    im = im.resize((nw, nh), Image.LANCZOS)
    left = (nw - size) // 2
    top = (nh - size) // 2
    im = im.crop((left, top, left + size, top + size))
    im.convert('RGB').save(out_path, 'JPEG', quality=90)
    print(f'Wrote {out_path}')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python tools/prepare_profile_image.py input.png')
        sys.exit(1)
    src = sys.argv[1]
    make_square(src, 512, 'output_512.jpg')
    make_square(src, 640, 'output_640.jpg')
