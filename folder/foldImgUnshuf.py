# --- foldImgUnshuf.py --- #
# reverses character shuffle AND spatial shuffle on encrypted .txt files
# uses forced division with consistent rounding rules

# --- Imports --- #
import os
import re
import math

# Hardcoded variables
VALID_DIRECTORIES = [
    "D:\\",  # Windows Ejectable Drive
    "/run/media/User/PERSONAL3",  # Linux (Ejectable Drive)
    "/Volumes/PERSONAL3",  # Mac (Ejectable Drive)

    "/Volumes/Macintosh HD/Users/User/Directory",  # Mac (Blank)
    "C:\\Users\\User\\OneDrive\\Desktop\\directory\\", # Windows (Blank)

    "/Users/whoshotnate/Desktop/everything/games/DolphinEmulator/etc", # local custom
    "C:\\Users\\davis\\OneDrive\\Desktop\\everything\\games\\DolphinEmulator\\etc\\"  # local custom
]

# --- Unshuffle Configurations --- #

# character shuffle mapping (same as shuffle)
CHAR_SHUFFLE_MAP = {
    'A': 'M', 'B': 'T', 'C': 'Z', 'D': 'P', 'E': 'K',
    'F': 'A', 'G': 'R', 'H': 'U', 'I': 'X', 'J': 'B',
    'K': 'L', 'L': 'C', 'M': 'W', 'N': 'E', 'O': 'S',
    'P': 'D', 'Q': 'G', 'R': 'Y', 'S': 'V', 'T': 'O',
    'U': 'Q', 'V': 'I', 'W': 'N', 'X': 'F', 'Y': 'H',
    'Z': 'J'
}

# create inverse mapping for unshuffling
CHAR_UNSHUFFLE_MAP = {v: k for k, v in CHAR_SHUFFLE_MAP.items()}

# grid configuration (MUST match shuffle configuration)
GRID_ROWS = 8    # num of vertical slices
GRID_COLS = 8    # num of horizontal slices
TOTAL_SLICES = GRID_ROWS * GRID_COLS  # 64 for 8x8

# spatial permutation (same as shuffle)
SPATIAL_PERMUTATION = [
     0, 13, 26, 39, 52,  1, 14, 27,   # row 0
    40, 53,  2, 15, 28, 41, 54,  3,   # row 1
    16, 29, 42, 55,  4, 17, 30, 43,   # row 2
    56,  5, 18, 31, 44, 57,  6, 19,   # row 3
    32, 45, 58,  7, 20, 33, 46, 59,   # row 4
     8, 21, 34, 47, 60,  9, 22, 35,   # row 5
    48, 61, 10, 23, 36, 49, 62, 11,   # row 6
    24, 37, 50, 63, 12, 25, 38, 51    # row 7
]

# calculate inverse permutation for unshuffling
SPATIAL_INVERSE_PERMUTATION = [0] * TOTAL_SLICES
for orig_pos in range(TOTAL_SLICES) :
    target_pos = SPATIAL_PERMUTATION[orig_pos]
    SPATIAL_INVERSE_PERMUTATION[target_pos] = orig_pos

# rounding mode (MUST match shuffle configuration)
ROUNDING_MODE = 'floor'  # Must be same as in shuffle.py!

# --- Helper Functions --- #

def natural_sort_key(s) :
    # function for natural sorting
    # Ex. ['a10.jpg', 'a2.jpg'] -> ['a2.jpg', 'a10.jpg']
    return [int(part) if part.isdigit() else part.lower()
            for part in re.split('([0-9]+)', s)]

def unshuffle_character(char) : 
    # reverse shuffle a single character
    return CHAR_UNSHUFFLE_MAP.get(char, char)

def unshuffle_pixel(pixel_str) :
    # unshuffle a single 6-character shuffled pixel
    # Format: (letter, digit, letter, digit, letter, digit) - 'A1B2C3'
    # only unshuffle the letters (positions 0, 2, 4), leave digits unchanged
    
    if len(pixel_str) != 6 : 
        return pixel_str  # return unchanged if not 6 characters
    
    chars = list(pixel_str)

    # apply unshuffle to letters at positions 0, 2, 4
    chars[0] = unshuffle_character(chars[0])
    chars[2] = unshuffle_character(chars[2])
    chars[4] = unshuffle_character(chars[4])
    
    return ''.join(chars)

def calculate_slice_dimensions(total_size, num_slices) :
    # calculate slice dimensions with forced division and consistent rounding
    # returns list of (start, end) indices for each slice
    # identical logic reflected in Shuffle.py

    slices = []
    
    if ROUNDING_MODE == 'floor' :
        # Floor rounding: slices get floor(total/num_slices), last slice gets remainder
        base_size = total_size // num_slices
        remainder = total_size % num_slices
        
        start = 0
        for i in range(num_slices) :
            # last slice gets any remainder
            size = base_size + (1 if i == num_slices - 1 else 0) if remainder > 0 else base_size
            if i == num_slices - 1 and remainder > 1 :
                size = base_size + remainder
            end = start + size
            slices.append((start, end))
            start = end
    
    elif ROUNDING_MODE == 'ceil' :

        # ceil rounding: slices get ceil(total/num_slices), adjust last slice
        base_size = math.ceil(total_size / num_slices)
        
        start = 0
        for i in range(num_slices) :
            remaining = total_size - start
            size = min(base_size, remaining) if remaining > 0 else 0
            end = start + size
            slices.append((start, end))
            start = end
    
    elif ROUNDING_MODE == 'round' :
        # round to nearest integer
        base_size = round(total_size / num_slices)
        
        start = 0
        for i in range(num_slices) :
            remaining = total_size - start

            # last slice gets whatever is left
            size = min(base_size, remaining) if i < num_slices - 1 else remaining
            end = start + size
            slices.append((start, end))
            start = end
    
    # ensure cover entire range
    if slices and slices[-1][1] < total_size :
        slices[-1] = (slices[-1][0], total_size)
    
    return slices

def slice_image_data_forced(lines, total_rows, total_cols) :
    # slice the image data (list of rows) into a grid of slices using forced division.
    # returns: list of slices, each slice is a list of rows (list of pixel strings)
    
    # calculate row slices
    row_slices = calculate_slice_dimensions(total_rows, GRID_ROWS)
    col_slices = calculate_slice_dimensions(total_cols, GRID_COLS)
    
    print(f"  Grid division: {len(row_slices)}x{len(col_slices)} slices")
    print(f"  Row slice sizes: {[end-start for start, end in row_slices]}")
    print(f"  Col slice sizes: {[end-start for start, end in col_slices]}")
    
    slices = []
    slice_dimensions = []
    
    # extract each slice
    for row_start, row_end in row_slices :
        for col_start, col_end in col_slices :
            slice_data = []
            slice_height = row_end - row_start
            slice_width = col_end - col_start
            
            # extract rows for this slice
            for r in range(row_start, row_end) :
                row = lines[r]
                pixels = row.strip().split()
                # extract columns for this slice
                slice_row = pixels[col_start:col_end]
                slice_data.append(slice_row)
            
            slices.append(slice_data)
            slice_dimensions.append((slice_height, slice_width))
    
    return slices, slice_dimensions, row_slices, col_slices

def reconstruct_image_from_slices_forced(slices, slice_dimensions, row_slices, col_slices, inverse=True) :
    # reconstruct image data from slices using forced division
    # if inverse=True, use inverse permutation to restore original order
    
    total_rows = sum(end-start for start, end in row_slices)
    total_cols = sum(end-start for start, end in col_slices)
    
    # initialize empty image grid
    image_grid = [[None for _ in range(total_cols)] for _ in range(total_rows)]
    
    # place each slice in its correct position
    for current_pos, (slice_data, (slice_height, slice_width)) in enumerate(zip(slices, slice_dimensions)) :
        # get original position using inverse permutation
        if inverse :
            orig_pos = SPATIAL_INVERSE_PERMUTATION[current_pos]
        else :
            orig_pos = current_pos
        
        # calculate which grid position this corresponds to
        orig_row_idx = orig_pos // GRID_COLS
        orig_col_idx = orig_pos % GRID_COLS
        
        # get the actual pixel coordinates from our row/col slices
        orig_row_start = row_slices[orig_row_idx][0]
        orig_col_start = col_slices[orig_col_idx][0]
        
        # place slice data into image grid at original position
        for r in range(slice_height) :
            for c in range(slice_width) :
                actual_row = orig_row_start + r
                actual_col = orig_col_start + c

                # safety check
                if actual_row < total_rows and actual_col < total_cols :
                    image_grid[actual_row][actual_col] = slice_data[r][c]
    
    # convert grid back to lines
    reconstructed_lines = []
    for row in image_grid:
        reconstructed_lines.append(' '.join(row))
    
    return reconstructed_lines

def unshuffle_text_file(text_path) :
    # read shuffled text file, apply spatial unshuffle then character unshuffle, write back.
    # uses forced division for spatial unshuffle.

    # read the entire file
    with open(text_path, 'r') as f :
        lines = f.readlines()
    
    # remove newlines and split into pixel lists
    pixel_rows = [line.strip() for line in lines if line.strip()]
    
    if not pixel_rows : 
        print(f"Empty file: {os.path.basename(text_path)}")
        return
    
    # get image dimensions
    total_rows = len(pixel_rows)
    total_cols = len(pixel_rows[0].split())
    
    print(f"\nProcessing {os.path.basename(text_path)}: {total_rows}x{total_cols} pixels")
    
    # --- Apply Spatial Unshuffle (Forced Division) --- #
    slices_info = slice_image_data_forced(pixel_rows, total_rows, total_cols)
    
    slices, slice_dimensions, row_slices, col_slices = slices_info
    
    # Reconstruct image with inverse permutation
    spatially_unshuffled_rows = reconstruct_image_from_slices_forced(
        slices, slice_dimensions, row_slices, col_slices, inverse=True
    )
    
    # --- Apply Character Unshuffle --- #
    fully_unshuffled_rows = []
    for row in spatially_unshuffled_rows :
        pixels = row.strip().split()
        unshuffled_pixels = [unshuffle_pixel(p) for p in pixels]
        fully_unshuffled_rows.append(' '.join(unshuffled_pixels))
    
    # write back to same file
    with open(text_path, 'w') as f :
        f.write('\n'.join(fully_unshuffled_rows))
    
    print(f"Unshuffled (forced division): {os.path.basename(text_path)}")

# --- Main Entry Point --- #

if __name__ == "__main__" :

    # --- 1. Directory Selection --- #
    
    # filter for existing directories
    existing_dirs = [d for d in VALID_DIRECTORIES if os.path.exists(d)]
    
    if not existing_dirs :
        print("ERROR: No valid directories found from the hardcoded list.")
        exit()
    
    # Directory selection menu
    print("\nAvailable base directories:")
    for i, directory in enumerate(existing_dirs) :
        print(f"{i+1}. {directory}")
    
    try :
        dir_choice = int(input("\nSelect base directory number: ")) - 1
        
        if dir_choice < 0 or dir_choice >= len(existing_dirs) :
            raise ValueError
            
        base_dir = existing_dirs[dir_choice]
        
    except ValueError :
        print("Invalid directory selection.")
        exit()
    
    # --- 2. Folder Selection --- #
    
    # set of folders to ignore
    IGNORE = {"System Volume Information"}
    
    # get all folders in hardcoded directory
    folders = [f for f in os.listdir(base_dir)
               if os.path.isdir(os.path.join(base_dir, f))
               and not f.startswith('.')  # skip .*
               and f not in IGNORE]  # skip predefined
    folders.sort(key=natural_sort_key)
    
    if not folders :
        print("No folders found in directory.")
        exit()
    
    # display folder selection menu
    print("Available folders:")
    for i, foldername in enumerate(folders) : 
        print(f"{i+1}. {foldername}")
    
    # get user selection
    try :
        selection = int(input("\nEnter folder number to unshuffle: ")) - 1
        
        if selection < 0 or selection >= len(folders) :
            raise ValueError
    
    except ValueError :
        print("Invalid selection.")
        exit()
    
    # Process selected folder
    selected_folder = folders[selection]
    folder_path = os.path.join(base_dir, selected_folder)
    
    # Get all .txt files in folder
    text_files = [
        f for f in os.listdir(folder_path)
        if f.lower().endswith('.txt')
        and not f.startswith('.')
    ]
    text_files.sort(key=natural_sort_key)
    
    if not text_files :
        print("No text files found in selected folder.")
        exit()
    
    print(f"\nGrid configuration: {GRID_ROWS}x{GRID_COLS} ({TOTAL_SLICES} slices)")
    print(f"Rounding mode: {ROUNDING_MODE}")
    print("Starting unshuffle process...\n")
    
    # process each text file
    for txt_file in text_files :
        txt_path = os.path.join(folder_path, txt_file)
        unshuffle_text_file(txt_path)
    
    print("\nAll .txt(s) within folder unshuffled")
    print("Note: Using forced division with consistent rounding")