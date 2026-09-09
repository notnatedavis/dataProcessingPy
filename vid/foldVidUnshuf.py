#   vid/foldVidUnshuf.py 

#   Reverses character and spatial shuffle on all .txt files (video frames) in a folder.
#   Supports selecting a subfolder (e.g., *_frames) inside the chosen folder.
#   Reads shuffle parameters from index.txt if present; otherwise uses common constants.
#   Spatial unshuffle now uses the correct inverse permutation (matching image unshuffle).

# --- Imports ---
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import logging
import json
import common
try :
    from tqdm import tqdm
except ImportError :
    tqdm = None

# --- Helper Functions ---
def load_unshuffle_config(folder_path: str) -> dict :
    # Try to load shuffle parameters from index.txt
    # Returns a dictionary with keys :
    #     'spatial_permutation', 'char_shuffle_map'
    # Also computes the inverse permutation
    # If the file does not exist or is invalid, returns None

    index_path = os.path.join(folder_path, common.INDEX_FILENAME)
    if not os.path.isfile(index_path):
        return None
    try :
        with open(index_path, 'r') as f :
            data = json.load(f)
        if 'spatial_permutation' not in data or 'char_shuffle_map' not in data:
            raise ValueError("index.txt missing required fields")
        # compute inverse spatial permutation
        perm = data['spatial_permutation']
        inv_perm = [0] * len(perm)
        for orig, target in enumerate(perm):
            inv_perm[target] = orig
        data['spatial_inverse_permutation'] = inv_perm
        return data
    except Exception as e :
        logging.warning(f"Could not load {common.INDEX_FILENAME}: {e}. Falling back to built-in constants.")
        return None

def unshuffle_text_file(text_path: str, ref_dims: tuple = None, config: dict = None,
                        verbose: bool = False, use_tqdm: bool = False) -> tuple :
    # Unshuffle a single frame file
    # Returns the dimensions (rows, cols) of the frame for consistency checking
    
    try :
        with open(text_path, 'r') as f :
            lines = f.readlines()
    except Exception as e :
        raise IOError(f"Failed to read {text_path}: {e}")

    pixel_rows = [line.strip() for line in lines if line.strip()]
    if not pixel_rows :
        raise ValueError(f"Empty file: {text_path}")

    total_rows = len(pixel_rows)
    total_cols = len(pixel_rows[0].split())

    if ref_dims is not None :
        if (total_rows, total_cols) != ref_dims :
            raise ValueError(f"Dimension mismatch in {os.path.basename(text_path)}: "
                             f"expected {ref_dims}, got ({total_rows}, {total_cols})")
    else :
        ref_dims = (total_rows, total_cols)

    if verbose :
        logging.debug(f"Frame {os.path.basename(text_path)}: {total_rows}x{total_cols}")

    # --- Spatial unshuffle (forced division) ---
    slices, dims, row_slices, col_slices = common.slice_image_data_forced(
        pixel_rows, total_rows, total_cols
    )

    # determine inverse permutation
    if config and 'spatial_inverse_permutation' in config:
        inv_perm = config['spatial_inverse_permutation']
    else:
        inv_perm = common.SPATIAL_INVERSE_PERMUTATION
    total_slices = len(inv_perm)

    assert len(slices) == total_slices, \
        f"Expected {total_slices} slices, got {len(slices)}"
    total_slice_rows = sum(end - start for start, end in row_slices)
    total_slice_cols = sum(end - start for start, end in col_slices)
    assert total_slice_rows == total_rows, f"Row slices sum to {total_slice_rows}, expected {total_rows}"
    assert total_slice_cols == total_cols, f"Col slices sum to {total_slice_cols}, expected {total_cols}"

    # --- build original slice order using inverse permutation ---
    original_slices = [None] * total_slices
    for shuffled_idx in range(total_slices):
        orig_idx = inv_perm[shuffled_idx]
        original_slices[orig_idx] = slices[shuffled_idx]

    spatially_unshuffled = common.reconstruct_image_from_slices_forced(
        original_slices, dims, row_slices, col_slices, inverse=False
    )

    # --- character unshuffle ---
    char_map = config['char_shuffle_map'] if config else common.CHAR_SHUFFLE_MAP
    # build inverse character map
    inv_char_map = {v: k for k, v in char_map.items()}

    fully_unshuffled = []
    for row in spatially_unshuffled:
        pixels = row.split()
        for p in pixels:
            if len(p) != 6:
                raise ValueError(f"Invalid pixel string '{p}' in {text_path}")
        unshuffled = [_unshuffle_pixel_with_map(p, inv_char_map) for p in pixels]
        fully_unshuffled.append(' '.join(unshuffled))

    try:
        with open(text_path, 'w') as f:
            f.write('\n'.join(fully_unshuffled))
    except Exception as e:
        raise IOError(f"Failed to write unshuffled data to {text_path}: {e}")

    if verbose or not use_tqdm:
        logging.info(f"Unshuffled: {os.path.basename(text_path)}")

    return ref_dims

def _unshuffle_pixel_with_map(pixel_str: str, inv_char_map: dict) -> str:
    # apply character unshuffle using the provided inverse map."""
    if len(pixel_str) != 6:
        return pixel_str
    chars = list(pixel_str)
    chars[0] = inv_char_map.get(chars[0], chars[0])
    chars[2] = inv_char_map.get(chars[2], chars[2])
    chars[4] = inv_char_map.get(chars[4], chars[4])
    return ''.join(chars)

# --- Main ---
def main() :
    parser = argparse.ArgumentParser(description="Unshuffle all frame .txt files in a folder (supports subfolder selection).")
    parser.add_argument('--dir', help='Base directory path')
    parser.add_argument('--folder', help='Folder name inside base directory (e.g., containing video folder)')
    parser.add_argument('--subfolder', help='Subfolder name (e.g., video_frames) containing the .txt files')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--no-progress', action='store_true', help='Disable progress bar')
    args = parser.parse_args()

    common.setup_logging(args.verbose)

    # --- 1: determine base directory and main folder ---
    if args.dir and args.folder :
        base_dir = args.dir
        folder_path = os.path.join(base_dir, args.folder)
        if not os.path.isdir(folder_path):
            logging.error(f"Folder not found: {folder_path}")
            return
    else :
        try :
            base_dir, folder_path = common.select_directory_and_folder(purpose="unshuffle frames")
        except Exception as e :
            logging.error(f"Directory selection failed: {e}")
            return

    # --- 2: determine subfolder containing the .txt files ---
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

    # --- load unshuffle configuration from index.txt (if present) ---
    config = load_unshuffle_config(target_folder)

    # --- 3: find all .txt files in the target folder, EXCLUDING metadata.txt and index.txt ---
    text_files = [f for f in os.listdir(target_folder)
                  if f.lower().endswith('.txt')
                  and not f.startswith('.')
                  and f not in ('metadata.txt', common.INDEX_FILENAME)]
    text_files.sort(key=common.natural_sort_key)

    if not text_files :
        logging.error(f"No .txt files found in {target_folder}.")
        return

    if config :
        logging.info(f"Using unshuffle parameters from {common.INDEX_FILENAME}")
        grid_rows = config.get('grid_rows', common.GRID_ROWS)
        grid_cols = config.get('grid_cols', common.GRID_COLS)
    else :
        grid_rows, grid_cols = common.GRID_ROWS, common.GRID_COLS
    logging.info(f"Grid: {grid_rows}x{grid_cols}, rounding: {common.ROUNDING_MODE}")
    logging.info(f"Found {len(text_files)} frame files in {target_folder}. Starting unshuffle...")

    use_tqdm = tqdm is not None and not args.no_progress
    iterator = text_files
    if use_tqdm :
        iterator = tqdm(text_files, desc="Unshuffling frames", unit="file")

    ref_dims = None
    failed_files = []

    for txt_file in iterator :
        txt_path = os.path.join(target_folder, txt_file)
        try :
            ref_dims = unshuffle_text_file(txt_path, ref_dims, config, args.verbose, use_tqdm)
        except Exception as e :
            logging.error(f"Error processing {txt_file}: {e}")
            failed_files.append(txt_file)
            continue

    if failed_files :
        logging.warning(f"Completed with errors on {len(failed_files)} files: {failed_files}")
    else :
        logging.info("All frame files unshuffled successfully")

if __name__ == "__main__" :
    main()