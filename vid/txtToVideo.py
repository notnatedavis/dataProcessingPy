# --- txtToVideo.py --- #
# constructs a video from ecrypted text files (individual frames)

# notes : I want to clean up comments + prints + format

# --- Imports --- #
import os
import re
from PIL import Image # not needed ?

import cv2
import numpy as np

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

# --- Helper Functions --- #

def natural_sort_key(s) :
    # Function for natural sorting
    return [int(part) if part.isdigit() else part.lower() 
            for part in re.split('([0-9]+)', s)]

def encrypted_string_to_value(encrypted_str) :
    # converts 2-character encrypted string back to RGB value (0-255)
    char = encrypted_str[0]
    digit = encrypted_str[1]
    return (ord(char) - ord('A')) * 10 + int(digit)

def encrypted_pixel_to_rgb(encrypted_pixel) :
    # converts 6-character encrypted string to RGB tuple
    red_str = encrypted_pixel[0:2]
    green_str = encrypted_pixel[2:4]
    blue_str = encrypted_pixel[4:6]
    r = encrypted_string_to_value(red_str)
    g = encrypted_string_to_value(green_str)
    b = encrypted_string_to_value(blue_str)
    return r, g, b

def text_to_frame(text_path) :
    # converts a single text frame file to a numpy image array (RGB)
    with open(text_path, 'r') as f :
        lines = f.readlines()
    
    height = len(lines)
    width = len(lines[0].strip().split())
    
    # Create empty RGB image array
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    
    for y, line in enumerate(lines) :
        encrypted_pixels = line.strip().split()
        for x, encrypted_pixel in enumerate(encrypted_pixels) :
            r, g, b = encrypted_pixel_to_rgb(encrypted_pixel)
            frame[y, x] = [b, g, r]  # Stored as BGR for OpenCV compatibility
    
    return frame

def frames_to_video(input_folder, output_video_path) :
    # assembles frames into a lossless video

    # read metadata
    metadata_path = os.path.join(input_folder, "metadata.txt")
    if not os.path.exists(metadata_path) :
        raise FileNotFoundError("metadata.txt not found in input folder")
    
    with open(metadata_path, 'r') as f :
        metadata = f.read().strip().split(',')
        width = int(metadata[0])
        height = int(metadata[1])
        fps = float(metadata[2])
    
    # get sorted frame files
    frame_files = [f for f in os.listdir(input_folder) 
                  if f.endswith('.txt') and f != 'metadata.txt']
    frame_files.sort(key=natural_sort_key)
    
    if not frame_files :
        raise ValueError("No frame files found in input folder")
    
    # configure lossless video writer
    fourcc = cv2.VideoWriter_fourcc(*'FFV1')  # Lossless FFV1 codec
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))
    
    if not out.isOpened() :
        # fallback to H.264 with lossless preset
        fourcc = cv2.VideoWriter_fourcc(*'avc1')
        out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))
        if not out.isOpened() :
            raise RuntimeError("Could not create video writer with lossless settings")
    
    # process frames
    for i, frame_file in enumerate(frame_files) :
        frame_path = os.path.join(input_folder, frame_file)
        frame = text_to_frame(frame_path)
        out.write(frame)
        
        # UPDATE THIS TO PRINT LIVE STATUS
    
        # is it possible to create like a loading progress bar within CLI ?
        if (i + 1) % 10 == 0:  # Update every 10 frames
            print(f"Processed frame {i+1}/{len(frame_files)}")
    
    out.release()
    return len(frame_files)

# --- Main Entry Point --- #

if __name__ == "__main__" :

    # --- 1. Directory Selection --- #

    existing_dirs = [d for d in VALID_DIRECTORIES if os.path.exists(d)]
    if not existing_dirs :
        print("ERROR: No valid directories found from the hardcoded list.")
        exit(1)
    
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
        exit(1)

    # --- 2. Folder Selection --- #

    folders = [f for f in os.listdir(base_dir) 
               if os.path.isdir(os.path.join(base_dir, f))]
    folders.sort(key=natural_sort_key)
    
    if not folders :
        print("No folders found in directory.")
        exit(1)
    
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
        exit(1)

    # --- 3. Frame Folder Selection --- #
    # Find folders with "_frames" suffix (created by videoToTxt)
    frame_folders = [f for f in os.listdir(folder_path) 
                     if os.path.isdir(os.path.join(folder_path, f)) 
                     and f.endswith('_frames')]
    frame_folders.sort(key=natural_sort_key)
    
    if not frame_folders:
        print("No frame folders found. Run videoToTxt.py first.")
        exit(1)
    
    print("\nAvailable frame folders:")
    for i, foldername in enumerate(frame_folders):
        print(f"{i+1}. {foldername}")
    
    try :
        selection = int(input("\nEnter frame folder number: ")) - 1
        if selection < 0 or selection >= len(frame_folders):
            raise ValueError
        selected_frame_folder = frame_folders[selection]
        frame_folder_path = os.path.join(folder_path, selected_frame_folder)
    except ValueError :
        print("Invalid selection.")
        exit(1)

    # --- 4. Output Video Setup --- #
    video_name = selected_frame_folder.replace('_frames', '')
    output_video_path = os.path.join(folder_path, f"{video_name}_reconstructed.mov")
    
    print(f"\nStarting video reconstruction...")
    print(f"Input frames: {frame_folder_path}")
    print(f"Output video: {output_video_path}")
    
    # Reconstruct video
    try :
        frame_count = frames_to_video(frame_folder_path, output_video_path)
        print(f"\nSuccess! Reconstructed {frame_count} frames into video")
        print(f"Output saved to: {output_video_path}")
    except Exception as e:
        print(f"\nError reconstructing video: {str(e)}")
        exit(1)