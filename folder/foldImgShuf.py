# --- foldImgShuf.py --- #
# applies character shuffle AND spatial shuffle to encrypted .txt files within same directory of folder
# spatial shuffle divides image into N slices (grid) and permutes their positions
# uses forced division with consistent rounding rules

# --- Imports --- #
import os
import re
import math

# Hardcoded variables
VALID_DIRECTORIES = [
    "D:\\",  # Windows Ejectable Drive
    "/run/media/whoshotnate/PERSONAL3",  # Linux
    "/Volumes/PERSONAL3",  # Mac
    "/Volumes/Macintosh HD/Users/User/Directory",  # personal local custom directory
    "/Users/whoshotnate/Desktop/everything/games/DolphinEmulator/etc",
    "C:\\Users\\davis\\OneDrive\\Desktop\\everything\\games\\DolphinEmulator\\etc\\"  # personal local custom
]

# --- Shuffle Configurations --- #

# character shuffle mapping (bijective)
CHAR_SHUFFLE_MAP = {
    'A': 'M', 'B': 'T', 'C': 'Z', 'D': 'P', 'E': 'K',
    'F': 'A', 'G': 'R', 'H': 'U', 'I': 'X', 'J': 'B',
    'K': 'L', 'L': 'C', 'M': 'W', 'N': 'E', 'O': 'S',
    'P': 'D', 'Q': 'G', 'R': 'Y', 'S': 'V', 'T': 'O',
    'U': 'Q', 'V': 'I', 'W': 'N', 'X': 'F', 'Y': 'H',
    'Z': 'J'
}

# grid configuration
GRID_ROWS = 8    # Number of vertical slices
GRID_COLS = 8    # Number of horizontal slices
TOTAL_SLICES = GRID_ROWS * GRID_COLS  # 64 for 8x8

# fixed spatial permutation for deterministic shuffling (generated as (i*13) % 64)
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

# Rounding mode: 'floor', 'ceil', or 'round'
ROUNDING_MODE = 'floor'  # consistent rounding for both shuffle and unshuffle

# --- Helper Functions --- #

def natural_sort_key(s) :
    # function for natural sorting
    # Ex. ['a10.jpg', 'a2.jpg'] -> ['a2.jpg', 'a10.jpg']
    return [int(part) if part.isdigit() else part.lower()
            for part in re.split('([0-9]+)', s)]

def shuffle_character(char) :
    # shuffle a (single) A-Z character
    return CHAR_SHUFFLE_MAP.get(char, char)

def shuffle_pixel(pixel_str) : 
    # shuffle a (single) 6-character encrypted pixel
    # Format : (letter, digit, letter, digit, letter, digit) = (A0B1C2)
    # only shuffle the letters (positions 0, 2, 4), leave digits unchanged
    
    if len(pixel_str) != 6 :
        return pixel_str  # return unchanged if not format
    
    chars = list(pixel_str)
    # apply shuffle
    chars[0] = shuffle_character(chars[0])
    chars[2] = shuffle_character(chars[2])
    chars[4] = shuffle_character(chars[4])
    
    return ''.join(chars)

def calculate_slice_dimensions(total_size, num_slices) :
    # calculate slice dimensions with forced division and consistent rounding
    # returns list of (start, end) indices for each slice

    slices = []
    
    if ROUNDING_MODE == 'floor' :
        # floor rounding: slices get floor(total/num_slices), last slice gets remainder
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

            # last slice gets remainder
            size = min(base_size, remaining) if i < num_slices - 1 else remaining
            end = start + size
            slices.append((start, end))
            start = end
    
    # ensure cover entire range
    if slices and slices[-1][1] < total_size :
        slices[-1] = (slices[-1][0], total_size)
    
    return slices

def slice_image_data_forced(lines, total_rows, total_cols) :
    # slice the image data (list of rows) into a grid of slices using forced division
    # returns : list of slices, each slice is a list of rows (list of pixel strings)

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

def reconstruct_image_from_slices_forced(slices, slice_dimensions, row_slices, col_slices) :
    # reconstruct image data from slices using forced division.
    
    total_rows = sum(end-start for start, end in row_slices)
    total_cols = sum(end-start for start, end in col_slices)
    
    # initialize empty image grid
    image_grid = [[None for _ in range(total_cols)] for _ in range(total_rows)]
    
    # place each slice in its permuted position
    for orig_pos, (slice_data, (slice_height, slice_width)) in enumerate(zip(slices, slice_dimensions)) :
        # get target position from permutation
        target_pos = SPATIAL_PERMUTATION[orig_pos]
        
        # calculate which grid position this target corresponds to
        target_row_idx = target_pos // GRID_COLS
        target_col_idx = target_pos % GRID_COLS
        
        # get the actual pixel coordinates from our row/col slices
        target_row_start = row_slices[target_row_idx][0]
        target_col_start = col_slices[target_col_idx][0]
        
        # place slice data into image grid
        for r in range(slice_height) :
            for c in range(slice_width) :
                actual_row = target_row_start + r
                actual_col = target_col_start + c

                # safety check
                if actual_row < total_rows and actual_col < total_cols :
                    image_grid[actual_row][actual_col] = slice_data[r][c]
    
    # convert grid back to lines
    reconstructed_lines = []
    for row in image_grid :
        reconstructed_lines.append(' '.join(row))
    
    return reconstructed_lines

def shuffle_text_file(text_path) :
    # read encrypted text file, apply both character and spatial shuffle, write back.
    # uses forced division for spatial shuffle

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
    
    # --- Apply Character Shuffle --- #
    char_shuffled_rows = []
    for row in pixel_rows :
        pixels = row.strip().split()
        shuffled_pixels = [shuffle_pixel(p) for p in pixels]
        char_shuffled_rows.append(' '.join(shuffled_pixels))
    
    # --- Apply Spatial Shuffle (Forced Division) --- #
    # always apply spatial shuffle with forced division !!!
    slices_info = slice_image_data_forced(char_shuffled_rows, total_rows, total_cols)
    
    slices, slice_dimensions, row_slices, col_slices = slices_info
    
    # apply permutation to slices
    permuted_slices = [slices[i] for i in range(len(slices))]
    
    # reconstruct image with shuffled slices
    shuffled_rows = reconstruct_image_from_slices_forced(permuted_slices, slice_dimensions, row_slices, col_slices)
    
    # write back to same file
    with open(text_path, 'w') as f :
        f.write('\n'.join(shuffled_rows))
    
    print(f"Shuffled (forced division): {os.path.basename(text_path)}")

# --- Main Entry Point --- #

if __name__ == "__main__" :

    # --- 1. Directory Selection --- #
    
    # filter for existing directories
    existing_dirs = [d for d in VALID_DIRECTORIES if os.path.exists(d)]
    
    if not existing_dirs :
        print("ERROR: No valid directories found from the hardcoded list.")
        exit()
    
    # directory selection menu
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
        selection = int(input("\nEnter folder number to shuffle: ")) - 1
        
        if selection < 0 or selection >= len(folders) : 
            raise ValueError
    
    except ValueError :
        print("Invalid selection.")
        exit()
    
    # process selected folder
    selected_folder = folders[selection]
    folder_path = os.path.join(base_dir, selected_folder)
    
    # get all .txt files in folder
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
    print("Starting shuffle process...\n")
    
    # process each text file
    for txt_file in text_files :
        txt_path = os.path.join(folder_path, txt_file)
        shuffle_text_file(txt_path)
    
    print("\nAll .txt(s) within folder shuffled")
    print("Note: Using forced division with consistent rounding")