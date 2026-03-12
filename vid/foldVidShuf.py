# --- vid/foldVidShuf.py --- 
# Applies character and spatial shuffle to all .txt files (video frames) in a folder
# Now supports selecting a subfolder (e.g., *_frames) inside the chosen folder

# ----- Imports ----- 
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import logging
from typing import List
import common
try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

# ----- Helper Functions ----- 
def shuffle_text_file(text_path: str) -> None : 
    # Shuffle a single frame file
    with open(text_path, 'r') as f :
        lines = f.readlines()

    pixel_rows = [line.strip() for line in lines if line.strip()]
    if not pixel_rows :
        logging.warning(f"Empty file: {os.path.basename(text_path)}")
        return

    total_rows = len(pixel_rows)
    total_cols = len(pixel_rows[0].split())
    logging.debug(f"Frame {os.path.basename(text_path)}: {total_rows}x{total_cols}")

    # Character shuffle
    char_shuffled = []
    for row in pixel_rows :
        pixels = row.split()
        shuffled = [common.shuffle_pixel(p) for p in pixels]
        char_shuffled.append(' '.join(shuffled))

    # Spatial shuffle (forced division)
    slices, dims, row_slices, col_slices = common.slice_image_data_forced(char_shuffled, total_rows, total_cols)
    permuted_slices = [slices[i] for i in common.SPATIAL_PERMUTATION]
    shuffled_rows = common.reconstruct_image_from_slices_forced(
        permuted_slices, dims, row_slices, col_slices, inverse=False
    )

    with open(text_path, 'w') as f :
        f.write('\n'.join(shuffled_rows))

    logging.info(f"Shuffled: {os.path.basename(text_path)}")

# ----- Main ----- 
def main() :
    parser = argparse.ArgumentParser(description="Shuffle all frame .txt files in a folder (supports subfolder selection).")
    parser.add_argument('--dir', help='Base directory path')
    parser.add_argument('--folder', help='Folder name inside base directory (e.g., containing video folder)')
    parser.add_argument('--subfolder', help='Subfolder name (e.g., video_frames) containing the .txt files')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--no-progress', action='store_true', help='Disable progress bar')
    args = parser.parse_args()

    common.setup_logging(args.verbose)

    # --- Step 1: Determine base directory and main folder ---
    if args.dir and args.folder :
        base_dir = args.dir
        folder_path = os.path.join(base_dir, args.folder)
        if not os.path.isdir(folder_path) :
            logging.error(f"Folder not found: {folder_path}")
            return
    else :
        try :
            base_dir, folder_path = common.select_directory_and_folder(purpose="shuffle frames")
        except Exception as e :
            logging.error(e)
            return

    # --- Step 2: Determine subfolder containing the .txt files ---
    if args.subfolder :
        target_folder = os.path.join(folder_path, args.subfolder)
        if not os.path.isdir(target_folder) :
            logging.error(f"Subfolder not found: {target_folder}")
            return
    else :
        # Look for subfolders ending with '_frames' (common naming from videoToTxt)
        try :
            target_folder = common.select_subfolder(folder_path, suffix="_frames", purpose="shuffle frames")
        except Exception as e :
            logging.error(e)
            return

    # --- Step 3: Find all .txt files in the target folder ---
    text_files = [f for f in os.listdir(target_folder)
                  if f.lower().endswith('.txt') and not f.startswith('.')]
    text_files.sort(key=common.natural_sort_key)

    if not text_files :
        logging.error(f"No .txt files found in {target_folder}.")
        return

    logging.info(f"Grid: {common.GRID_ROWS}x{common.GRID_COLS}, rounding: {common.ROUNDING_MODE}")
    logging.info(f"Found {len(text_files)} frame files in {target_folder}. Starting shuffle...")

    iterator = text_files
    if tqdm and not args.no_progress :
        iterator = tqdm(text_files, desc="Shuffling frames", unit="file")

    for txt_file in iterator :
        txt_path = os.path.join(target_folder, txt_file)
        shuffle_text_file(txt_path)

    logging.info("All frame files shuffled.")

if __name__ == "__main__" :
    main()