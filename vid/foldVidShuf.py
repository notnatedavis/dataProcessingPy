#   vid/foldVidShuf.py

#   Applies character and spatial shuffle to all .txt files (video frames) in a folder
#   Supports selecting a subfolder (e.g., *_frames) inside the chosen folder
#   Reads shuffle parameters from index.txt if present; otherwise uses common constants
#   Spatial shuffle now uses the correct forward permutation (matching image shuffle)

# --- Imports ---
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import logging
import json # for reading index.txt
import common
try :
    from tqdm import tqdm
except ImportError :
    tqdm = None

# --- Helper Functions ---
def load_shuffle_config(folder_path: str) -> dict :
    # Try to load shuffle parameters from index.txt
    # Returns a dictionary with keys:
    #     'spatial_permutation', 'char_shuffle_map'
    # If the file does not exist or is invalid, returns None

    index_path = os.path.join(folder_path, common.INDEX_FILENAME)
    if not os.path.isfile(index_path) :
        return None
    try :
        with open(index_path, 'r') as f :
            data = json.load(f)
        # minimal validation
        if 'spatial_permutation' not in data or 'char_shuffle_map' not in data :
            raise ValueError("index.txt missing required fields")
        return data
    except Exception as e :
        logging.warning(f"Could not load {common.INDEX_FILENAME}: {e}. Falling back to built-in constants.")
        return None

def shuffle_text_file(text_path: str, ref_dims: tuple = None, config: dict = None, verbose: bool = False, use_tqdm: bool = False) -> tuple :
    # Shuffle a single frame file
    # Returns the dimensions (rows, cols) of the frame for consistency checking

    try :
        with open(text_path, 'r') as f :
            lines = f.readlines()
    except Exception as e :
        raise IOError(f"Failed to read {text_path}: {e}")

    # clean and validate lines
    pixel_rows = [line.strip() for line in lines if line.strip()]
    if not pixel_rows :
        raise ValueError(f"Empty file: {text_path}")

    total_rows = len(pixel_rows)
    total_cols = len(pixel_rows[0].split())

    # consistency check with previous frames (if any)
    if ref_dims is not None :
        if (total_rows, total_cols) != ref_dims :
            raise ValueError(f"Dimension mismatch in {os.path.basename(text_path)}: "
                             f"expected {ref_dims}, got ({total_rows}, {total_cols})")
    else :
        # first frame – store dimensions for later checks
        ref_dims = (total_rows, total_cols)

    if verbose :
        logging.debug(f"Frame {os.path.basename(text_path)}: {total_rows}x{total_cols}")

    # --- character shuffle ---
    char_shuffled = []
    # determine character map: from config if available, else use common
    char_map = config['char_shuffle_map'] if config else common.CHAR_SHUFFLE_MAP

    for row in pixel_rows :
        pixels = row.split()
        # validate each pixel length (should be 6)
        for p in pixels :
            if len(p) != 6 :
                raise ValueError(f"Invalid pixel string '{p}' in {text_path}")
        # use a local shuffle function that applies the given map
        shuffled = [_shuffle_pixel_with_map(p, char_map) for p in pixels]
        char_shuffled.append(' '.join(shuffled))

    # --- spatial shuffle (forced division) ---
    slices, dims, row_slices, col_slices = common.slice_image_data_forced(
        char_shuffled, total_rows, total_cols
    )

    # load spatial permutation
    spatial_perm = config['spatial_permutation'] if config else common.SPATIAL_PERMUTATION
    total_slices = len(spatial_perm)

    assert len(slices) == total_slices, \
        f"Expected {total_slices} slices, got {len(slices)}"
    assert len(dims) == total_slices, "Slice dimensions mismatch"

    # verify slices when concatenated would reconstruct original dim
    total_slice_rows = sum(end - start for start, end in row_slices)
    total_slice_cols = sum(end - start for start, end in col_slices)
    assert total_slice_rows == total_rows, f"Row slices sum to {total_slice_rows}, expected {total_rows}"
    assert total_slice_cols == total_cols, f"Col slices sum to {total_slice_cols}, expected {total_cols}"

    # --- apply forward permutation (same logic) ---
    permuted_slices = [None] * total_slices
    for orig_idx in range(total_slices) :
        target_idx = spatial_perm[orig_idx]    # forward map
        permuted_slices[target_idx] = slices[orig_idx]

    shuffled_rows = common.reconstruct_image_from_slices_forced(
        permuted_slices, dims, row_slices, col_slices, inverse=False
    )

    # write back to the same file
    try :
        with open(text_path, 'w') as f :
            f.write('\n'.join(shuffled_rows))
    except Exception as e :
        raise IOError(f"Failed to write shuffled data to {text_path}: {e}")

    if verbose or not use_tqdm :
        logging.info(f"Shuffled: {os.path.basename(text_path)}")

    return ref_dims


def _shuffle_pixel_with_map(pixel_str: str, char_map: dict) -> str :
    # apply character shuffle using the provided map (same logic)
    if len(pixel_str) != 6 :
        return pixel_str
    chars = list(pixel_str)
    chars[0] = char_map.get(chars[0], chars[0])
    chars[2] = char_map.get(chars[2], chars[2])
    chars[4] = char_map.get(chars[4], chars[4])
    return ''.join(chars)

# --- main ---
def main() :
    parser = argparse.ArgumentParser(description="Shuffle all frame .txt files in a folder (w/ subfolder selection)")
    parser.add_argument('--dir', help='Base directory path')
    parser.add_argument('--folder', help='Folder name inside base directory (e.g., containing video folder)')
    parser.add_argument('--subfolder', help='Subfolder name (e.g., video_frames) containing the .txt files')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--no-progress', action='store_true', help='Disable progress bar')
    args = parser.parse_args()

    common.setup_logging(args.verbose)

    # --- 1 : determine base directory and main folder ---
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
            logging.error(f"Directory selection failed: {e}")
            return

    # --- 2: determine subfolder containing the .txt files ---
    if args.subfolder :
        target_folder = os.path.join(folder_path, args.subfolder)
        if not os.path.isdir(target_folder) :
            logging.error(f"Subfolder not found: {target_folder}")
            return
    else :
        try :
            target_folder = common.select_subfolder(folder_path, suffix="_frames", purpose="shuffle frames")
        except Exception as e :
            logging.error(f"Subfolder selection failed: {e}")
            return

    # --- load shuffle configuration from index.txt (if present) ---
    config = load_shuffle_config(target_folder)

    # --- 3: find all .txt files in the target folder, EXCLUDING metadata.txt and index.txt ---
    text_files = [f for f in os.listdir(target_folder)
                  if f.lower().endswith('.txt')
                  and not f.startswith('.')
                  and f not in ('metadata.txt', common.INDEX_FILENAME)]
    text_files.sort(key=common.natural_sort_key)

    if not text_files :
        logging.error(f"No .txt files found in {target_folder}.")
        return

    # log which grid using
    if config :
        logging.info(f"Using shuffle parameters from {common.INDEX_FILENAME}")
        grid_rows = config.get('grid_rows', common.GRID_ROWS)
        grid_cols = config.get('grid_cols', common.GRID_COLS)
    else :
        grid_rows, grid_cols = common.GRID_ROWS, common.GRID_COLS
    logging.info(f"Grid: {grid_rows}x{grid_cols}, rounding: {common.ROUNDING_MODE}")
    logging.info(f"Found {len(text_files)} frame files in {target_folder}. Starting shuffle...")

    use_tqdm = tqdm is not None and not args.no_progress
    iterator = text_files
    if use_tqdm :
        iterator = tqdm(text_files, desc="Shuffling frames", unit="file")

    ref_dims = None
    failed_files = []

    for txt_file in iterator :
        txt_path = os.path.join(target_folder, txt_file)
        try :
            ref_dims = shuffle_text_file(txt_path, ref_dims, config, args.verbose, use_tqdm)
        except Exception as e :
            logging.error(f"Error processing {txt_file}: {e}")
            failed_files.append(txt_file)
            continue

    if failed_files :
        logging.warning(f"Completed with errors on {len(failed_files)} files: {failed_files}")
    else :
        logging.info("All frame files shuffled successfully.")

if __name__ == "__main__" :
    main()