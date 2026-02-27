# --- videoToTxt.py --- #
# deconstructs a video into ecrypted text files (one per frame)

# notes : 
# I want to clean up comments + prints + format
# - fix naming of processed files
# - update corresponding txtToVideo.py

# --- Imports --- #
import os
import re
from PIL import Image # not needed ?

import cv2
import numpy as np

# Hardcoded variables
VALID_DIRECTORIES = [
    "D:\\", # Windows
    "/run/media/whoshotnate/PERSONAL3", # Linux
    "/Volumes/PERSONAL3", # Mac
    "/Volumes/Macintosh HD/Users/User/Directory" # personal local custom directory
]

# --- Helper Functions --- #

def natural_sort_key(s) :
    # Function for natural sorting
    
    return [int(part) if part.isdigit() else part.lower() 
            for part in re.split('([0-9]+)', s)]

def value_to_encrypted_string(value) :
    # converts a RGB value to encrypted string (specific format)
    # encrypts a single RGB value (0-255) to 2-character string
    
    char = chr(ord('A') + (value // 10))
    digit = str(value % 10)
    
    return f"{char}{digit}"

def rgb_to_encrypted_string(r, g, b) :
    # converts a RGB tuple to encrypted string
    
    red_str = value_to_encrypted_string(r)
    green_str = value_to_encrypted_string(g)
    blue_str = value_to_encrypted_string(b)
    
    return f"{red_str}{green_str}{blue_str}"

def process_frame(frame, frame_index, output_folder) :
    # process a single frame and save as encrypted text file
    # returns path to generated .txt file

    # 1. convert from BGR to RGB
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    height, width, _ = frame_rgb.shape
    
    # 2. create output filename
    output_filename = f"frame_{frame_index:04d}.txt"
    output_path = os.path.join(output_folder, output_filename)
    
    # 3. write encrypted pixel data
    with open(output_path, 'w') as f :
        for y in range(height) :
            for x in range(width) :
                r, g, b = frame_rgb[y, x]
                encrypted_pixel = rgb_to_encrypted_string(r, g, b)
                f.write(encrypted_pixel + ' ')
                
            f.write("\n")
    
    return output_path

def video_to_frames(video_path, output_folder) :
    # extract frames from a video and save as encrypted text files

    # 0.1 create output directory if needed
    os.makedirs(output_folder, exist_ok=True)

    # 0.2 declare variable for video capture
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened( ):
        raise ValueError("error opening video file")
    
    # 1. get video properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"Processing video: {os.path.basename(video_path)}") # optional
    print(f"Resolution: {width}x{height}, FPS: {fps:.2f}, Frames: {frame_count}") # optional
    
    # 2. save metadata
    metadata_path = os.path.join(output_folder, "metadata.txt")
    with open(metadata_path, 'w') as f :
        f.write(f"{width},{height},{fps}")
    
    # 3. process each frame for all frames in 'cap'
    success, frame = cap.read()
    frame_index = 0
    
    while success :
        output_path = process_frame(frame, frame_index, output_folder)
        print(f"Processed frame {frame_index+1}/{frame_count} -> {os.path.basename(output_path)}") # optional
        
        # read next frame
        success, frame = cap.read()
        frame_index += 1
    
    cap.release() # resource cleanup
    
    print(f"\nVideo processing complete! {frame_index} frames saved to {output_folder}") # optional
    
    return frame_index

# --- Main Entry Point --- #

if __name__ == "__main__" :

    # --- 1. Directory Selection --- #

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
        if dir_choice < 0 or dir_choice >= len(existing_dirs):
            raise ValueError
        base_dir = existing_dirs[dir_choice]
    except ValueError :
        print("Invalid directory selection.")
        exit()

    # --- 2. Folder Selection --- #

    folders = [f for f in os.listdir(base_dir) 
        if os.path.isdir(os.path.join(base_dir, f)) 
        and not f.startswith('.')] 
        # filters out *.files
    folders.sort(key=natural_sort_key)
    
    if not folders :
        print("No folders found in directory.")
        exit()
    
    print("\nAvailable folders:")
    for i, foldername in enumerate(folders) :
        print(f"{i+1}. {foldername}")
    
    try :
        selection = int(input("\nEnter folder number to process: ")) - 1
        if selection < 0 or selection >= len(folders):
            raise ValueError
        selected_folder = folders[selection]
        folder_path = os.path.join(base_dir, selected_folder)
    except ValueError :
        print("Invalid selection.")
        exit()

    # --- 3. Video File Selection --- #

    video_files = [f for f in os.listdir(folder_path) 
        if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')) 
        and not f.startswith('.')] 
        # filters out *.files
    video_files.sort(key=natural_sort_key)
    
    if not video_files :
        print("No video files found in directory.")
        exit()
    
    print("\nAvailable video files:")
    for i, filename in enumerate(video_files):
        print(f"{i+1}. {filename}")
    
    try :
        selection = int(input("\nEnter file number to deconstruct: ")) - 1
        if selection < 0 or selection >= len(video_files):
            raise ValueError
        selected_file = video_files[selection]
        video_path = os.path.join(folder_path, selected_file)
    except ValueError :
        print("Invalid selection.")
        exit()

    # --- 4. Output Folder Setup --- #
    
    video_name = os.path.splitext(selected_file)[0]
    output_folder = os.path.join(folder_path, f"{video_name}_frames")
    
    print(f"\nStarting video deconstruction...")
    print(f"Input: {video_path}")
    print(f"Output: {output_folder}")
    
    # process video
    try :
        frame_count = video_to_frames(video_path, output_folder)
        print(f"Successfully deconstructed {frame_count} frames!")
    except Exception as e :
        print(f"Error processing video: {str(e)}")
