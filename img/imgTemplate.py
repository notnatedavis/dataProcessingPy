# --- imgTemplate.py --- #
# select an img, pass ratios to crop, process (draw lines), return (overwrite)

#  notes : I want to clean up comments + prints + format

# --- Imports --- #
from PIL import Image, ImageDraw
import os
import re

# Hardcoded variables
# location of img(s)
IMG_DIRECTORIES = [
    "C:\\Users\\davis\\OneDrive\\Desktop\\everything\\photos", # Windows
    "/Volumes/Macintosh HD/Users/User/Directory" # personal local custom directory
]

# --- Helper Functions --- #

def natural_sort_key(s) :
    # function for natural sorting
    # Ex. ['a10.jpg', 'a2.jpg'] -> ['a2.jpg', 'a10.jpg']
    return [int(part) if part.isdigit() else part.lower() 
            for part in re.split('([0-9]+)', s)]

def crop_img(image, ratio="1:1") :
    width, height = image.size

    if ratio == "1:1" : # square crop (centered)
        side = min(width, height)

        left = (width - side) // 2
        top = (height - side) // 2

        right = left + side
        bottom = top + side

    elif ratio == "4:3" :
        # rectangle crop (centered)
        target_ratio = 4 / 3
        if width / height > target_ratio :
            new_width = int(height * target_ratio)
            left = (width - new_width) // 2
            top = 0
            right = left + new_width
            bottom = height
        else :
            new_height = int(width / target_ratio)
            top = (height - new_height) // 2
            left = 0
            right = width
            bottom = top + new_height

    else :
        print("Invalid ratio. Defaulting to 1:1.")
        return crop_img(image, "1:1")

    return image.crop((left, top, right, bottom))

def draw_lines(image, color) :
    draw = ImageDraw.Draw(image) # create a drawing context
    width, height = image.size
    
    # calculate the positions for the lines
    quarter_width = width / 4
    quarter_height = height / 4

    # draw three horizontal lines at 1/4, 2/4, and 3/4 of the height
    for i in range(1, 4):
        y = int(quarter_height * i)
        draw.line((0, y, width, y), fill=color, width=1)

    # draw three vertical lines at 1/4, 2/4, and 3/4 of the width
    for i in range(1, 4):
        x = int(quarter_width * i)
        draw.line((x, 0, x, height), fill=color, width=1)

    # calculate the positions for the yellow lines (midpoints between red lines)
    eighth_width = width / 8
    eighth_height = height / 8

    # draw yellow horizontal lines at 1/8, 3/8, 5/8, and 7/8 of the height
    for i in range(1, 8, 2):
        y = int(eighth_height * i)
        draw.line((0, y, width, y), fill=color, width=1)

    # draw yellow vertical lines at 1/8, 3/8, 5/8, and 7/8 of the width
    for i in range(1, 8, 2):
        x = int(eighth_width * i)
        draw.line((x, 0, x, height), fill=color, width=1)
    
    return image

# --- Main Entry Point --- #

if __name__ == "__main__" :

    # 1. Directory Selection
    existing_dirs = [d for d in IMG_DIRECTORIES if os.path.exists(d)]

    if not existing_dirs :
        print("ERROR: No valid directories found from the hardcoded list.")
        exit()

    print("\nAvailable base directories:")
    for i, directory in enumerate(existing_dirs) :
        print(f"{i+1}. {directory}")

    try :
        dir_choice = int(input("\nSelect base directory number: ")) - 1
        if dir_choice < 0 or dir_choice >= len(existing_dirs):
            raise ValueError
        base_dir = existing_dirs[dir_choice]
    except ValueError :
        print("Invalid directory selection.")
        exit()

    # 2. Folder Selection
    folders = [f for f in os.listdir(base_dir)
               if os.path.isdir(os.path.join(base_dir, f))]
    folders.sort(key=natural_sort_key)

    if not folders :
        print("No folders found in directory.")
        exit()

    print("\nAvailable folders:")
    for i, foldername in enumerate(folders):
        print(f"{i+1}. {foldername}")

    try :
        selection = int(input("\nEnter folder number: ")) - 1
        if selection < 0 or selection >= len(folders):
            raise ValueError
        
    except ValueError :
        print("Invalid selection.")
        exit()

    selected_folder = folders[selection]
    folder_path = os.path.join(base_dir, selected_folder)

    # 3. File Selection (JPG only)
    image_files = [f for f in os.listdir(folder_path)
                   if f.lower().endswith('.jpg')]
    image_files.sort(key=natural_sort_key)

    if not image_files:
        print("No image (.jpg) files found in directory.")
        exit()

    print("\nAvailable image files:")
    for i, filename in enumerate(image_files):
        print(f"{i+1}. {filename}")

    try:
        selection = int(input("\nEnter image number: ")) - 1
        if selection < 0 or selection >= len(image_files):
            raise ValueError
    except ValueError:
        print("Invalid selection.")
        exit()

    selected_file = image_files[selection]
    image_path = os.path.join(folder_path, selected_file)

    # 4. Aspect Ratio Selection
    print("\nSelect crop ratio:")
    print("1. Square (1:1)")
    print("2. Rectangle (4:3)")

    try :
        ratio_choice = int(input("Choice: "))
        if ratio_choice == 1 :
            ratio = "1:1"
        elif ratio_choice == 2 :
            ratio = "4:3"
        else :
            raise ValueError
        
    except ValueError :
        print("Invalid ratio selected. Defaulting to 1:1.")
        ratio = "1:1"

    # 4.5 Line Color Selection
    color_options = {
        1: "red",
        2: "blue",
        3: "green",
        4: "yellow",
        5: "white",
        6: "black",
        7: "purple",
        8: "orange"
    }

    print("\nSelect line color:")
    for key, value in color_options.items():
        print(f"{key}. {value}")

    try :
        color_choice = int(input("Choice: "))
        color = color_options.get(color_choice, "red")
    except ValueError :
        print("Invalid color selected. Defaulting to red.")
        color = "red"

    # 5. Load, Crop, Draw, and Save
    with Image.open(image_path) as img :
        cropped = crop_img(img, ratio)
        final_image = draw_lines(cropped, color)
        output_path = os.path.join(folder_path, f"XXX{selected_file}")
        final_image.save(output_path)
        print(f"\nImage saved as: {output_path}")