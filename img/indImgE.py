#   img/indImgE.py

#   Encrypts a single image to a .txt file, cropping dimensions if necessary.

# --- Imports --- 
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import logging
from PIL import Image
import common

# --- Helper Functions --- 
def encrypt_image_to_text(image_path: str, output_text_path: str) -> None :
    # convert an image to encrypted text, cropping dimensions if needed
    img = Image.open(image_path)
    if img.mode != 'RGB' :
        img = img.convert('RGB')

    orig_w, orig_h = img.size
    new_w, new_h = common.crop_to_divisible(orig_w, orig_h)

    if (new_w, new_h) != (orig_w, orig_h) :
        # crop from bottom-right
        img = img.crop((0, 0, new_w, new_h))
        logging.info(f"  Cropped: {orig_w}x{orig_h} → {new_w}x{new_h}")

    width, height = new_w, new_h

    with open(output_text_path, 'w') as f :
        for y in range(height) :
            for x in range(width) :
                r, g, b = img.getpixel((x, y))
                encrypted = common.rgb_to_encrypted_string(r, g, b)
                f.write(encrypted + ' ')
            f.write("\n")

    os.remove(image_path)
    logging.info(f"Encrypted to: {output_text_path}")

# --- Main --- 
def main() :
    parser = argparse.ArgumentParser(description="Encrypt a single image to a .txt file.")
    parser.add_argument('--dir', help='Base directory path')
    parser.add_argument('--folder', help='Folder name inside base directory')
    parser.add_argument('--file', help='Image filename (optional, will prompt if not given)')
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
            base_dir, folder_path = common.select_directory_and_folder(purpose="encrypt")
        except Exception as e :
            logging.error(e)
            return

    # find image files
    image_files = [f for f in os.listdir(folder_path)
                   if not f.startswith('.')
                   and f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff'))]
    image_files.sort(key=common.natural_sort_key)

    if not image_files :
        logging.error("No image files found in folder.")
        return

    if args.file :
        if args.file in image_files :
            selected = args.file
        else :
            logging.error(f"File '{args.file}' not found in folder.")
            return
    else :
        print("\nAvailable image files:")
        for i, f in enumerate(image_files):
            print(f"{i+1}. {f}")
        try :
            choice = int(input("Enter file number to encrypt: ")) - 1
            selected = image_files[choice]
        except (ValueError, IndexError) :
            logging.error("Invalid selection.")
            return

    image_path = os.path.join(folder_path, selected)
    output_filename = os.path.splitext(selected)[0] + ".txt"
    output_path = os.path.join(folder_path, output_filename)

    encrypt_image_to_text(image_path, output_path)

if __name__ == "__main__" :
    main()