#   img/indImgD.py

#   Decrypts a single encrypted .txt file to an image (JPEG)
#   Uses common module

# --- Imports ---
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import logging
from PIL import Image
import common

# --- Helper Functions ---
def decrypt_text_to_image(text_path: str, output_image_path: str) -> None :
    # convert a single encrypted text file to an image
    with open(text_path, 'r') as f :
        lines = f.readlines()

    height = len(lines)
    width = len(lines[0].strip().split())

    # validate dimensions (optional, just info)
    valid, msg = common.validate_dimensions(width, height)
    logging.info(f"  {msg}")

    img = Image.new('RGB', (width, height))
    pixels = img.load()

    for y in range(height) :
        encrypted_pixels = lines[y].strip().split()
        for x in range(width) :
            r, g, b = common.encrypted_pixel_to_rgb(encrypted_pixels[x])
            pixels[x, y] = (r, g, b)

    img.save(output_image_path, quality=100)
    os.remove(text_path)
    logging.info(f"Decrypted to: {output_image_path}")

# --- Main --- 
def main() :
    parser = argparse.ArgumentParser(description="Decrypt a single .txt file to an image.")
    parser.add_argument('--dir', help='Base directory path')
    parser.add_argument('--folder', help='Folder name inside base directory')
    parser.add_argument('--file', help='Text filename (optional, will prompt if not given)')
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

    # find .txt files
    text_files = [f for f in os.listdir(folder_path)
                  if f.lower().endswith('.txt') and not f.startswith('.')]
    text_files.sort(key=common.natural_sort_key)

    if not text_files :
        logging.error("No .txt files found in folder.")
        return

    # If file specified, check it exists
    if args.file :
        if args.file in text_files :
            selected = args.file
        else :
            logging.error(f"File '{args.file}' not found in folder.")
            return
    else :
        print("\nAvailable .txt files:")
        for i, f in enumerate(text_files) :
            print(f"{i+1}. {f}")
        try : 
            choice = int(input("Enter file number to decrypt: ")) - 1
            selected = text_files[choice]
        except (ValueError, IndexError) :
            logging.error("Invalid selection.")
            return

    text_path = os.path.join(folder_path, selected)
    output_filename = os.path.splitext(selected)[0] + ".jpg"
    output_path = os.path.join(folder_path, output_filename)

    decrypt_text_to_image(text_path, output_path)

if __name__ == "__main__" :
    main()