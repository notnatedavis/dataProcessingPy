# ----- foldImgD.py ----- #
# Decrypts all .txt files in a folder to images (JPEG)
# Uses common.py module

# ----- Imports ----- #

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import logging
from PIL import Image
import common

# ----- Helper Functions ----- #

def decrypt_text_to_image(text_path: str, output_image_path: str) -> None :
    # Convert a single encrypted text file to an image
    with open(text_path, 'r') as f :
        lines = f.readlines()

    height = len(lines)
    width = len(lines[0].strip().split())

    # Validate dimensions
    valid, msg = common.validate_dimensions(width, height)
    logging.info(f"  {msg}")
    if not valid :
        logging.warning("Image may not be compatible with spatial shuffle.")

    img = Image.new('RGB', (width, height))
    pixels = img.load()

    for y in range(height) :
        encrypted_pixels = lines[y].strip().split()
        for x in range(width) :
            r, g, b = common.encrypted_pixel_to_rgb(encrypted_pixels[x])
            pixels[x, y] = (r, g, b)

    img.save(output_image_path, quality=100)
    os.remove(text_path)
    logging.info(f"Decrypted to: {os.path.basename(output_image_path)}")

# ----- Main ----- #

def main() :
    parser = argparse.ArgumentParser(description="Decrypt all .txt files in a folder to images.")
    parser.add_argument('--dir', help='Base directory path')
    parser.add_argument('--folder', help='Folder name inside base directory')
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
            base_dir, folder_path = common.select_directory_and_folder(purpose="decrypt")
        except Exception as e :
            logging.error(e)
            return

    # Find all .txt files
    text_files = [f for f in os.listdir(folder_path)
                  if f.lower().endswith('.txt') and not f.startswith('.')]
    text_files.sort(key=common.natural_sort_key)

    if not text_files :
        logging.error("No text files found.")
        return

    logging.info(f"Grid divisor: {common.GRID_DIVISOR}")
    logging.info("Starting decryption...\n")

    for txt in text_files :
        txt_path = os.path.join(folder_path, txt)
        out = os.path.splitext(txt)[0] + ".jpg"
        decrypt_text_to_image(txt_path, os.path.join(folder_path, out))

    logging.info("All .txt files decrypted.")

if __name__ == "__main__" :
    main()