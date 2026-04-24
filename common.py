# ----- common.py ----- #
# Shared constants, helpers, and configuration loader for the dataProcessingPy project
# Hardcoded config

# ----- Imports ----- #

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re
import logging
from typing import List, Tuple, Any, Dict, Optional

# ----- Logging Setup ----- #

def setup_logging(verbose: bool = False) -> None :
    # Configure logging for the application
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

# ----- Global Constants (loaded from config) ----- #

VALID_DIRECTORIES : List[str] = [
    "D:\\",
    "/run/media/User/PERSONAL3", 
    "/Volumes/PERSONAL3", # specific usb macos
    "/Volumes/Macintosh HD/Users/User/Directory", # blank macos
    "C:\\Users\\User\\OneDrive\\Desktop\\directory\\",
    "/Users/whoshotnate/Desktop/everything/games/DolphinEmulator/etc",
    "C:\\Users\\davis\\OneDrive\\Desktop\\everything\\games\\DolphinEmulator\\etc\\",
    "C:\\Users\\ASUS\\Desktop\\everything\\photos\\draw" # personal win pc
]
IGNORE: set = {"System Volume Information"}
GRID_DIVISOR: int = 8
GRID_ROWS: int = 8
GRID_COLS: int = 8
TOTAL_SLICES: int = GRID_ROWS * GRID_COLS

# Spatial permutation (generated as (i*13) % 64)
SPATIAL_PERMUTATION: List[int] = [
     0, 13, 26, 39, 52,  1, 14, 27,
    40, 53,  2, 15, 28, 41, 54,  3,
    16, 29, 42, 55,  4, 17, 30, 43,
    56,  5, 18, 31, 44, 57,  6, 19,
    32, 45, 58,  7, 20, 33, 46, 59,
     8, 21, 34, 47, 60,  9, 22, 35,
    48, 61, 10, 23, 36, 49, 62, 11,
    24, 37, 50, 63, 12, 25, 38, 51
]

# Inverse permutation (for unshuffle)
SPATIAL_INVERSE_PERMUTATION: List[int] = [0] * TOTAL_SLICES
for orig_pos, target_pos in enumerate(SPATIAL_PERMUTATION) :
    SPATIAL_INVERSE_PERMUTATION[target_pos] = orig_pos

# Character shuffle map
CHAR_SHUFFLE_MAP: Dict[str, str] = {
    'A': 'M', 'B': 'T', 'C': 'Z', 'D': 'P', 'E': 'K',
    'F': 'A', 'G': 'R', 'H': 'U', 'I': 'X', 'J': 'B',
    'K': 'L', 'L': 'C', 'M': 'W', 'N': 'E', 'O': 'S',
    'P': 'D', 'Q': 'G', 'R': 'Y', 'S': 'V', 'T': 'O',
    'U': 'Q', 'V': 'I', 'W': 'N', 'X': 'F', 'Y': 'H',
    'Z': 'J'
}

# Inverse character map
CHAR_UNSHUFFLE_MAP: Dict[str, str] = {v: k for k, v in CHAR_SHUFFLE_MAP.items()}

ROUNDING_MODE: str = 'floor'   # 'floor', 'ceil', or 'round'

# ----- Helper Functions ----- #

def natural_sort_key(s: str) -> List :
    # Generate natural sorting key (e.g., 'a10.jpg' -> ['a', 10, '.jpg'])
    return [int(part) if part.isdigit() else part.lower()
            for part in re.split(r'([0-9]+)', s)]

def validate_dimensions(width: int, height: int, divisor: int = GRID_DIVISOR) -> Tuple[bool, str] :
    # Check if dimensions are divisible by divisor
    if width % divisor == 0 and height % divisor == 0 :
        return True, f"Valid: {width}x{height} divisible by {divisor}"
    else :
        return False, f"Warning: {width}x{height} not divisible by {divisor}"

def select_subfolder(parent_folder: str, suffix: str = "", purpose: str = "process") -> str:
    """
    List subfolders inside parent_folder (optionally filtering by suffix) and let user select one.
    Returns the full path of the selected subfolder.
    """
    subfolders = [f for f in os.listdir(parent_folder)
                  if os.path.isdir(os.path.join(parent_folder, f))
                  and not f.startswith('.')
                  and f not in IGNORE]
    if suffix:
        subfolders = [f for f in subfolders if f.endswith(suffix)]
    subfolders.sort(key=natural_sort_key)

    if not subfolders:
        raise FileNotFoundError(f"No subfolders{f' ending with {suffix}' if suffix else ''} found in {parent_folder}")

    print(f"\nAvailable subfolders to {purpose}:")
    for i, f in enumerate(subfolders):
        print(f"{i+1}. {f}")

    try:
        choice = int(input("\nEnter subfolder number: ")) - 1
        return os.path.join(parent_folder, subfolders[choice])
    except (ValueError, IndexError):
        raise ValueError("Invalid subfolder selection.")
    
    def crop_to_grid(orig_w, orig_h):
        """Return largest dimensions <= original that are multiples of GRID_COLS and GRID_ROWS."""
        new_w = orig_w - (orig_w % GRID_COLS)
        new_h = orig_h - (orig_h % GRID_ROWS)
        return new_w, new_h
    
# ----- Encryption / Decryption ----- 
def value_to_encrypted_string(value: int) -> str :
    # Convert an RGB value (0-255) to a 2-character encrypted string
    char = chr(ord('A') + (value // 10))
    digit = str(value % 10)
    return f"{char}{digit}"

def encrypted_string_to_value(encrypted_str: str) -> int :
    # Convert a 2-character encrypted string back to an RGB value
    char = encrypted_str[0]
    digit = encrypted_str[1]
    return (ord(char) - ord('A')) * 10 + int(digit)

def rgb_to_encrypted_string(r: int, g: int, b: int) -> str :
    # Convert RGB triple to a 6-character encrypted pixel string
    return f"{value_to_encrypted_string(r)}{value_to_encrypted_string(g)}{value_to_encrypted_string(b)}"

def encrypted_pixel_to_rgb(encrypted_pixel: str) -> Tuple[int, int, int] :
    # Convert a 6-character encrypted pixel string back to RGB
    if len(encrypted_pixel) != 6 :
        raise ValueError(f"Invalid encrypted pixel length: {encrypted_pixel}")
    r = encrypted_string_to_value(encrypted_pixel[0:2])
    g = encrypted_string_to_value(encrypted_pixel[2:4])
    b = encrypted_string_to_value(encrypted_pixel[4:6])
    return r, g, b

# ----- Character Shuffle / Unshuffle ----- #

def shuffle_character(char: str) -> str:
    # Apply character shuffle to a single A-Z character
    return CHAR_SHUFFLE_MAP.get(char, char)

def unshuffle_character(char: str) -> str:
    # Reverse character shuffle for a single A-Z character
    return CHAR_UNSHUFFLE_MAP.get(char, char)

def shuffle_pixel(pixel_str: str) -> str:
    # Apply character shuffle to the three letters in a 6-char pixel string
    if len(pixel_str) != 6 :
        return pixel_str
    chars = list(pixel_str)
    chars[0] = shuffle_character(chars[0])
    chars[2] = shuffle_character(chars[2])
    chars[4] = shuffle_character(chars[4])
    return ''.join(chars)

def unshuffle_pixel(pixel_str: str) -> str :
    # Reverse character shuffle on a 6-char pixel string
    if len(pixel_str) != 6 :
        return pixel_str
    chars = list(pixel_str)
    chars[0] = unshuffle_character(chars[0])
    chars[2] = unshuffle_character(chars[2])
    chars[4] = unshuffle_character(chars[4])
    return ''.join(chars)

# ----- Grid Slicing (Forced Division) ----- #

def calculate_slice_dimensions(total_size: int, num_slices: int) -> List[Tuple[int, int]] :
    # Calculate start/end indices for each slice using forced division 

    slices = []
    if ROUNDING_MODE == 'floor' :
        base_size = total_size // num_slices
        remainder = total_size % num_slices
        start = 0
        for i in range(num_slices) :
            size = base_size + (remainder if i == num_slices - 1 else 0)
            end = start + size
            slices.append((start, end))
            start = end
    elif ROUNDING_MODE == 'ceil' :
        base_size = (total_size + num_slices - 1) // num_slices
        start = 0
        for i in range(num_slices) :
            remaining = total_size - start
            size = min(base_size, remaining) if remaining > 0 else 0
            end = start + size
            slices.append((start, end))
            start = end
    elif ROUNDING_MODE == 'round' :
        base_size = round(total_size / num_slices)
        start = 0
        for i in range(num_slices) :
            remaining = total_size - start
            size = min(base_size, remaining) if i < num_slices - 1 else remaining
            end = start + size
            slices.append((start, end))
            start = end
    else :
        raise ValueError(f"Unknown ROUNDING_MODE: {ROUNDING_MODE}")
    # Ensure last slice covers any remaining pixels due to rounding
    if slices and slices[-1][1] < total_size :
        slices[-1] = (slices[-1][0], total_size)
    return slices

def slice_image_data_forced(lines: List[str], total_rows: int, total_cols: int) -> Tuple[List, List, List, List] :
    # Slice image data (list of row strings) into a grid using forced division.
    # Returns (slices, slice_dimensions, row_slices, col_slices)

    row_slices = calculate_slice_dimensions(total_rows, GRID_ROWS)
    col_slices = calculate_slice_dimensions(total_cols, GRID_COLS)

    logging.debug(f"Row slices: {[(s,e) for s,e in row_slices]}")
    logging.debug(f"Col slices: {[(s,e) for s,e in col_slices]}")

    slices = []
    slice_dimensions = []

    for r_start, r_end in row_slices :
        for c_start, c_end in col_slices :
            slice_data = []
            for r in range(r_start, r_end) :
                row = lines[r].strip().split()
                slice_row = row[c_start:c_end]
                slice_data.append(slice_row)
            slices.append(slice_data)
            slice_dimensions.append((r_end - r_start, c_end - c_start))

    return slices, slice_dimensions, row_slices, col_slices

def reconstruct_image_from_slices_forced(
    slices: List,
    slice_dimensions: List[Tuple[int, int]],
    row_slices: List[Tuple[int, int]],
    col_slices: List[Tuple[int, int]],
    inverse: bool = False
) -> List[str] :
    # Reconstruct image data from slices using forced division.
    # If inverse=True, use inverse permutation (for unshuffle).
    # Returns list of row strings.
    
    total_rows = sum(end - start for start, end in row_slices)
    total_cols = sum(end - start for start, end in col_slices)

    # Create empty grid
    image_grid = [[None for _ in range(total_cols)] for _ in range(total_rows)]

    for current_pos, (slice_data, (slice_h, slice_w)) in enumerate(zip(slices, slice_dimensions)):
        # Determine original grid position
        if inverse :
            orig_pos = SPATIAL_INVERSE_PERMUTATION[current_pos]
        else :
            orig_pos = current_pos

        orig_row_idx = orig_pos // GRID_COLS
        orig_col_idx = orig_pos % GRID_COLS

        orig_row_start, _ = row_slices[orig_row_idx]
        orig_col_start, _ = col_slices[orig_col_idx]

        # Place slice into grid
        for r in range(slice_h) :
            for c in range(slice_w) :
                actual_row = orig_row_start + r
                actual_col = orig_col_start + c
                if actual_row < total_rows and actual_col < total_cols :
                    image_grid[actual_row][actual_col] = slice_data[r][c]

    # Convert grid back to row strings
    reconstructed = []
    for row in image_grid :
        reconstructed.append(' '.join(row))
    return reconstructed

# ----- Image Cropping to Divisor ----- #

def crop_to_divisible(width: int, height: int, divisor: int = GRID_DIVISOR) -> Tuple[int, int]:
    # Return new dimensions (w, h) cropped to be divisible by divisor."""
    new_w = width - (width % divisor)
    new_h = height - (height % divisor)
    return new_w, new_h

# ----- Interactive Directory/Folder Selection ----- #

def select_directory_and_folder(base_dirs: List[str] = None, purpose: str = "process") -> Tuple[str, str] :
    # Interactive selection of base directory and folder
    # Returns (base_dir, folder_path)

    if base_dirs is None :
        base_dirs = VALID_DIRECTORIES

    # Filter existing directories
    existing = [d for d in base_dirs if os.path.exists(d)]
    if not existing :
        logging.error("No valid base directories found.")
        raise FileNotFoundError("No valid base directories.")

    print("\nAvailable base directories:")
    for i, d in enumerate(existing) :
        print(f"{i+1}. {d}")
    try :
        choice = int(input("\nSelect base directory number: ")) - 1
        base_dir = existing[choice]
    except (ValueError, IndexError) :
        logging.error("Invalid selection.")
        raise

    # List folders in base_dir
    folders = [f for f in os.listdir(base_dir)
               if os.path.isdir(os.path.join(base_dir, f))
               and not f.startswith('.')
               and f not in IGNORE]
    folders.sort(key=natural_sort_key)

    if not folders :
        logging.error("No folders found in selected directory.")
        raise FileNotFoundError("No folders.")

    print("\nAvailable folders:")
    for i, f in enumerate(folders) :
        print(f"{i+1}. {f}")
    try :
        choice = int(input(f"\nEnter folder number to {purpose}: ")) - 1
        folder_name = folders[choice]
    except (ValueError, IndexError) :
        logging.error("Invalid selection.")
        raise

    folder_path = os.path.join(base_dir, folder_name)
    return base_dir, folder_path