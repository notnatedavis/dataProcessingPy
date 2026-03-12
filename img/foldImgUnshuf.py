# --- foldImgUnshuf.py --- #
# Reverses character and spatial shuffle on all .txt files in a folder
# Uses forced division with consistent rounding

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

def unshuffle_text_file(text_path: str) -> None :
    # Read, unshuffle (spatial then character), and write back a single .txt file
    with open(text_path, 'r') as f :
        lines = f.readlines()

    pixel_rows = [line.strip() for line in lines if line.strip()]
    if not pixel_rows :
        logging.warning(f"Empty file: {os.path.basename(text_path)}")
        return

    total_rows = len(pixel_rows)
    total_cols = len(pixel_rows[0].split())
    logging.debug(f"Processing {os.path.basename(text_path)}: {total_rows}x{total_cols}")

    # --- Spatial unshuffle (forced division) ---
    # Slice the current (shuffled) image data
    slices, dims, row_slices, col_slices = common.slice_image_data_forced(pixel_rows, total_rows, total_cols)
    # Reconstruct using inverse permutation to restore original slice order
    spatially_unshuffled = common.reconstruct_image_from_slices_forced(
        slices, dims, row_slices, col_slices, inverse=True
    )

    # --- Character unshuffle ---
    fully_unshuffled = []
    for row in spatially_unshuffled:
        pixels = row.split()
        unshuffled = [common.unshuffle_pixel(p) for p in pixels]
        fully_unshuffled.append(' '.join(unshuffled))

    with open(text_path, 'w') as f :
        f.write('\n'.join(fully_unshuffled))

    logging.info(f"Unshuffled: {os.path.basename(text_path)}")

# ----- Main ----- #

def main() :
    parser = argparse.ArgumentParser(description="Unshuffle all .txt files in a folder.")
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
            base_dir, folder_path = common.select_directory_and_folder(purpose="unshuffle")
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
    logging.info(f"Found {len(text_files)} files. Starting unshuffle...")

    iterator = text_files
    if tqdm and not args.no_progress :
        iterator = tqdm(text_files, desc="Unshuffling", unit="file")

    for txt_file in iterator :
        txt_path = os.path.join(folder_path, txt_file)
        unshuffle_text_file(txt_path)

    logging.info("All .txt files unshuffled.")

if __name__ == "__main__" :
    main()