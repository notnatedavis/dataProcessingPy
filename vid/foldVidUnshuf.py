# --- vid/foldVidUnshuf.py ---
# Reverses character and spatial shuffle on all .txt files (video frames) in a folder
# Supports selecting a subfolder (e.g., *_frames) inside the chosen folder.
# Includes robust error handling, dimension consistency checks, and slicing assertions.

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import logging
import common
try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

# ----- Helper Functions -----
def unshuffle_text_file(text_path: str, ref_dims: tuple = None, verbose: bool = False, use_tqdm: bool = False) -> tuple:
    """
    Unshuffle a single frame file.
    Returns the dimensions (rows, cols) of the frame for consistency checking.
    """
    try:
        with open(text_path, 'r') as f:
            lines = f.readlines()
    except Exception as e:
        raise IOError(f"Failed to read {text_path}: {e}")

    pixel_rows = [line.strip() for line in lines if line.strip()]
    if not pixel_rows:
        raise ValueError(f"Empty file: {text_path}")

    total_rows = len(pixel_rows)
    total_cols = len(pixel_rows[0].split())

    if ref_dims is not None:
        if (total_rows, total_cols) != ref_dims:
            raise ValueError(f"Dimension mismatch in {os.path.basename(text_path)}: "
                             f"expected {ref_dims}, got ({total_rows}, {total_cols})")
    else:
        ref_dims = (total_rows, total_cols)

    if verbose:
        logging.debug(f"Frame {os.path.basename(text_path)}: {total_rows}x{total_cols}")

    # --- Spatial unshuffle (forced division) ---
    slices, dims, row_slices, col_slices = common.slice_image_data_forced(
        pixel_rows, total_rows, total_cols
    )
    # Assertions
    assert len(slices) == common.TOTAL_SLICES, \
        f"Expected {common.TOTAL_SLICES} slices, got {len(slices)}"
    total_slice_rows = sum(end - start for start, end in row_slices)
    total_slice_cols = sum(end - start for start, end in col_slices)
    assert total_slice_rows == total_rows, f"Row slices sum to {total_slice_rows}, expected {total_rows}"
    assert total_slice_cols == total_cols, f"Col slices sum to {total_slice_cols}, expected {total_cols}"

    # Apply inverse permutation to restore original slice order
    spatially_unshuffled = common.reconstruct_image_from_slices_forced(
        slices, dims, row_slices, col_slices, inverse=True
    )

    # --- Character unshuffle ---
    fully_unshuffled = []
    for row in spatially_unshuffled:
        pixels = row.split()
        for p in pixels:
            if len(p) != 6:
                raise ValueError(f"Invalid pixel string '{p}' in {text_path}")
        unshuffled = [common.unshuffle_pixel(p) for p in pixels]
        fully_unshuffled.append(' '.join(unshuffled))

    try:
        with open(text_path, 'w') as f:
            f.write('\n'.join(fully_unshuffled))
    except Exception as e:
        raise IOError(f"Failed to write unshuffled data to {text_path}: {e}")

    if verbose or not use_tqdm:
        logging.info(f"Unshuffled: {os.path.basename(text_path)}")

    return ref_dims

# ----- Main -----
def main():
    parser = argparse.ArgumentParser(description="Unshuffle all frame .txt files in a folder (supports subfolder selection).")
    parser.add_argument('--dir', help='Base directory path')
    parser.add_argument('--folder', help='Folder name inside base directory (e.g., containing video folder)')
    parser.add_argument('--subfolder', help='Subfolder name (e.g., video_frames) containing the .txt files')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--no-progress', action='store_true', help='Disable progress bar')
    args = parser.parse_args()

    common.setup_logging(args.verbose)

    # --- Step 1: Determine base directory and main folder ---
    if args.dir and args.folder:
        base_dir = args.dir
        folder_path = os.path.join(base_dir, args.folder)
        if not os.path.isdir(folder_path):
            logging.error(f"Folder not found: {folder_path}")
            return
    else:
        try:
            base_dir, folder_path = common.select_directory_and_folder(purpose="unshuffle frames")
        except Exception as e:
            logging.error(f"Directory selection failed: {e}")
            return

    # --- Step 2: Determine subfolder containing the .txt files ---
    if args.subfolder:
        target_folder = os.path.join(folder_path, args.subfolder)
        if not os.path.isdir(target_folder):
            logging.error(f"Subfolder not found: {target_folder}")
            return
    else:
        try:
            target_folder = common.select_subfolder(folder_path, suffix="_frames", purpose="unshuffle frames")
        except Exception as e:
            logging.error(f"Subfolder selection failed: {e}")
            return

    # --- Step 3: Find all .txt files in the target folder, EXCLUDING metadata.txt ---
    text_files = [f for f in os.listdir(target_folder)
                  if f.lower().endswith('.txt')
                  and not f.startswith('.')
                  and f != 'metadata.txt']
    text_files.sort(key=common.natural_sort_key)

    if not text_files:
        logging.error(f"No .txt files found in {target_folder}.")
        return

    logging.info(f"Grid: {common.GRID_ROWS}x{common.GRID_COLS}, rounding: {common.ROUNDING_MODE}")
    logging.info(f"Found {len(text_files)} frame files in {target_folder}. Starting unshuffle...")

    use_tqdm = tqdm is not None and not args.no_progress
    iterator = text_files
    if use_tqdm:
        iterator = tqdm(text_files, desc="Unshuffling frames", unit="file")

    ref_dims = None
    failed_files = []

    for txt_file in iterator:
        txt_path = os.path.join(target_folder, txt_file)
        try:
            ref_dims = unshuffle_text_file(txt_path, ref_dims, args.verbose, use_tqdm)
        except Exception as e:
            logging.error(f"Error processing {txt_file}: {e}")
            failed_files.append(txt_file)
            continue

    if failed_files:
        logging.warning(f"Completed with errors on {len(failed_files)} files: {failed_files}")
    else:
        logging.info("All frame files unshuffled successfully.")

if __name__ == "__main__":
    main()