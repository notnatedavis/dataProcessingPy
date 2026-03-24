# --- foldImgShuf.py --- #
# Applies character and spatial shuffle to all .txt files in a folders

# ----- Imports ----- #

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import logging
from typing import List
import common
try :
    from tqdm import tqdm # for progress bar
except ImportError :
    tqdm = None

# ----- Helper Functions ----- #

def shuffle_text_file(text_path: str) -> None :
    # Read, shuffle, and write back a single .txt file
    with open(text_path, 'r') as f :
        lines = f.readlines()

    pixel_rows = [line.strip() for line in lines if line.strip()]
    if not pixel_rows :
        logging.warning(f"Empty file: {os.path.basename(text_path)}")
        return

    total_rows = len(pixel_rows)
    total_cols = len(pixel_rows[0].split())

    # Crop to multiple of GRID_ROWS and GRID_COLS
    new_h, new_w = common.crop_to_divisible(total_rows, total_cols)
    if new_h != total_rows or new_w != total_cols:
        pixel_rows = [row[:new_w] for row in pixel_rows[:new_h]]
        total_rows, total_cols = new_h, new_w

    # Slicing
    slices, dims, row_slices, col_slices = common.slice_image_data_forced(pixel_rows, total_rows, total_cols)

    # Permute using forward map
    permuted_slices = [None] * common.TOTAL_SLICES
    for orig_idx in range(common.TOTAL_SLICES):
        target_idx = common.SPATIAL_PERMUTATION[orig_idx]   # forward map
        permuted_slices[target_idx] = slices[orig_idx]

    # Reconstruct
    shuffled_rows = common.reconstruct_image_from_slices_forced(
       permuted_slices, dims, row_slices, col_slices, inverse=False
    )

    with open(text_path, 'w') as f :
        f.write('\n'.join(shuffled_rows))

    logging.info(f"Shuffled: {os.path.basename(text_path)}")

# ----- Main ----- #

def main() :
    parser = argparse.ArgumentParser(description="Shuffle all .txt files in a folder.")
    parser.add_argument('--dir', help='Base directory path')
    parser.add_argument('--folder', help='Folder name inside base directory')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--no-progress', action='store_true', help='Disable progress bar')
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
            base_dir, folder_path = common.select_directory_and_folder(purpose="shuffle")
        except Exception as e :
            logging.error(e)
            return

    text_files = [f for f in os.listdir(folder_path)
                  if f.lower().endswith('.txt') and not f.startswith('.')]
    text_files.sort(key=common.natural_sort_key)

    if not text_files :
        logging.error("No .txt files found.")
        return

    logging.info(f"Grid: {common.GRID_ROWS}x{common.GRID_COLS}, rounding: {common.ROUNDING_MODE}")
    logging.info(f"Found {len(text_files)} files. Starting shuffle...")

    iterator = text_files
    if tqdm and not args.no_progress :
        iterator = tqdm(text_files, desc="Shuffling", unit="file")

    for txt_file in iterator :
        txt_path = os.path.join(folder_path, txt_file)
        shuffle_text_file(txt_path)

    logging.info("All .txt files shuffled.")

if __name__ == "__main__" :
    main()