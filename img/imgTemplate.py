# --- imgTemplate.py --- #
# Template for processing a single image: crop to ratio, draw grid lines, save as new file

# ----- Imports ----- #

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import logging
from PIL import Image, ImageDraw
import common

# ----- Helper Functions ----- #

def crop_img(image: Image.Image, ratio: str = "1:1") -> Image.Image : 
    # Crop image to given aspect ratio (centered)
    width, height = image.size

    if ratio == "1:1" :
        side = min(width, height)
        left = (width - side) // 2
        top = (height - side) // 2
        right = left + side
        bottom = top + side
    elif ratio == "4:3" :
        target_ratio = 4 / 3
        if width / height > target_ratio :
            new_width = int(height * target_ratio)
            left = (width - new_width) // 2
            top = 0
            right = left + new_width
            bottom = height
        else :
            new_height = int(width / target_ratio)
            top = (height - new_height) // 2
            left = 0
            right = width
            bottom = top + new_height
    else :
        logging.warning(f"Unknown ratio '{ratio}', defaulting to 1:1.")
        return crop_img(image, "1:1")

    return image.crop((left, top, right, bottom))

def draw_lines(image: Image.Image, color: str = "red") -> Image.Image :
    # Draw red (major) and yellow (minor) grid lines on the image
    draw = ImageDraw.Draw(image)
    width, height = image.size

    # Major lines at quarters
    qw = width / 4
    qh = height / 4
    for i in range(1, 4) :
        y = int(qh * i)
        draw.line((0, y, width, y), fill=color, width=1)
        x = int(qw * i)
        draw.line((x, 0, x, height), fill=color, width=1)

    # Minor lines at eighths
    ew = width / 8
    eh = height / 8
    for i in range(1, 8, 2) :
        y = int(eh * i)
        draw.line((0, y, width, y), fill=color, width=1)
        x = int(ew * i)
        draw.line((x, 0, x, height), fill=color, width=1)

    return image

# ----- Main ----- #

def main() :
    parser = argparse.ArgumentParser(description="Crop an image to a ratio and draw grid lines.")
    parser.add_argument('--dir', help='Base directory path')
    parser.add_argument('--folder', help='Folder name inside base directory')
    parser.add_argument('--file', help='Image filename (optional, will prompt if not given)')
    parser.add_argument('--ratio', choices=['1:1', '4:3'], default='1:1', help='Aspect ratio')
    parser.add_argument('--color', default='red', help='Line color (any PIL color name)')
    parser.add_argument('--prefix', default='XXX', help='Prefix for output filename')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    args = parser.parse_args()

    common.setup_logging(args.verbose)

    if args.dir and args.folder :
        base_dir = args.dir
        folder_path = os.path.join(base_dir, args.folder)
        if not os.path.isdir(folder_path) :
            logging.error(f"Folder not found: {folder_path}")
            return
    else :
        try :
            base_dir, folder_path = common.select_directory_and_folder(purpose="select image folder")
        except Exception as e :
            logging.error(e)
            return

    # Find image files (only .jpg for this template)
    image_files = [f for f in os.listdir(folder_path)
                   if f.lower().endswith('.jpg') and not f.startswith('.')]
    image_files.sort(key=common.natural_sort_key)

    if not image_files :
        logging.error("No .jpg files found in folder.")
        return

    if args.file :
        if args.file in image_files :
            selected = args.file
        else :
            logging.error(f"File '{args.file}' not found.")
            return
    else :
        print("\nAvailable .jpg files:")
        for i, f in enumerate(image_files):
            print(f"{i+1}. {f}")
        try :
            choice = int(input("Enter file number: ")) - 1
            selected = image_files[choice]
        except (ValueError, IndexError):
            logging.error("Invalid selection.")
            return

    image_path = os.path.join(folder_path, selected)

    # Load, crop, draw, save
    with Image.open(image_path) as img :
        cropped = crop_img(img, args.ratio)
        final = draw_lines(cropped, args.color)
        output_filename = f"{args.prefix}{selected}"
        output_path = os.path.join(folder_path, output_filename)
        final.save(output_path)
        logging.info(f"Image saved as: {output_path}")

if __name__ == "__main__" :
    main()