# --- indImgD.py --- #
# decrypts (specific format) .txt files into images within same directory

# notes : I want to clean up comments + prints + format

# --- Imports --- #
import os
import re
from PIL import Image

# Hardcoded variables
VALID_DIRECTORIES = [
    "C:\\Users\\davis\\OneDrive\\Desktop\\everything\\photos", # Windows
    "/run/media/whoshotnate/PERSONAL3", # Linux
    "/Volumes/PERSONAL3", # Mac
    "/Volumes/Macintosh HD/Users/User/Directory" # personal local custom directory
]

# --- Helper Functions --- #

def natural_sort_key(s) :
    # function for natural sorting
    # Ex. ['a10.txt', 'a2.txt'] -> ['a2.txt', 'a10.txt']
    return [int(part) if part.isdigit() else part.lower() 
            for part in re.split('([0-9]+)', s)]

def encrypted_string_to_value(encrypted_str) :
    # extract the character and digit
    char = encrypted_str[0]
    digit = encrypted_str[1]

    # calculate the original value
    value = (ord(char) - ord('A')) * 10 + int(digit)

    return value # alt : return (ord(char) - ord('A')) * 10 + int(digit)

def encrypted_pixel_to_rgb(encrypted_pixel) :
    # split the encrypted pixel into RGB components
    red_str = encrypted_pixel[0:2]
    green_str = encrypted_pixel[2:4]
    blue_str = encrypted_pixel[4:6]

    # convert each component back to an RGB value
    r = encrypted_string_to_value(red_str)
    g = encrypted_string_to_value(green_str)
    b = encrypted_string_to_value(blue_str)

    return r, g, b

def decrypt_text_to_image(text_path, output_image_path) :
    # read encrypted text file
    with open(text_path, 'r') as f :
        lines = f.readlines()
    
    # determine the image dimensions
    height = len(lines)
    width = len(lines[0].strip().split()) # number of pixels in the 1st row

    # create new image
    img = Image.new('RGB', (width, height))
    pixels = img.load()

    # process each line (row of pixels)
    for y in range(height) :
        # split the line into individual encrypted pixels
        encrypted_pixels = lines[y].strip().split()
        for x in range(width) :
            # convert the encrypted pixel back to RGB values
            r, g, b = encrypted_pixel_to_rgb(encrypted_pixels[x])

            # set the pixel in the image
            pixels[x, y] = (r, g, b)
    
    # save the reconstructed image
    img.save(output_image_path, quality=100) # high quality output
    os.remove(text_path) # remove original .txt
    print(f"Image D&^S to : {output_image_path}")

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

    # get all folders in hardcoded directory
    folders = [f for f in os.listdir(base_dir)
        if os.path.isdir(os.path.join(base_dir, f))]
    folders.sort(key=natural_sort_key)

    if not folders :
        print("No folders found in directory.")
        exit()

    # display folder selection menu
    print("Available folders:")
    for i, foldername in enumerate(folders):
        print(f"{i+1}. {foldername}")

    # get user selection
    try :
        selection = selection = int(input("\nEnter folder number to decrypt: ")) - 1

        if selection < 0 or selection >= len(folders) :
            raise ValueError

    except ValueError :
        print("Invalid selection.")
        exit()

    # process selected folder
    selected_folder = folders[selection]
    folder_path = os.path.join(base_dir, selected_folder)

    # --- 3. File Selection --- #

    # get all .txt files in hardcoded directory
    text_files = [f for f in os.listdir(folder_path)
        if f.lower().endswith('.txt')]
    
    text_files.sort(key=natural_sort_key) # (natural) sort files
    
    if not text_files :
        print("No text files found in directory.")
        exit()
    
    # display file selection menu
    print("Available text files:")
    for i, filename in enumerate(text_files):
        print(f"{i+1}. {filename}")
    
    # get user selection
    try :
        selection = int(input("\nEnter file number to decrypt: ")) - 1

        if selection < 0 or selection >= len(text_files) :
            raise ValueError
        
    except ValueError :
        print("Invalid selection.")
        exit()
    
    # process selected file
    selected_file = text_files[selection]
    text_path = os.path.join(folder_path, selected_file)
    output_filename = os.path.splitext(selected_file)[0] + ".jpg"
    output_path = os.path.join(folder_path, output_filename)
    
    decrypt_text_to_image(text_path, output_path)
