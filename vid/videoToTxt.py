# ----- videoToTxt.py ----- #
# Deconstructs a video into encrypted text frames, cropping each frame to divisible dimensions

# ----- Imports ----- #

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import logging
import cv2
import numpy as np
import common
try :
    from tqdm import tqdm
except ImportError :
    tqdm = None

# ----- Helper Functions ----- #

def process_frame(frame: np.ndarray, frame_index: int, output_folder: str) -> None :
    # Convert a single frame (BGR) to encrypted text and save
    # Convert to RGB
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, _ = frame_rgb.shape

    # Crop to divisible dimensions if needed
    new_w, new_h = common.crop_to_divisible(w, h)
    if (new_w, new_h) != (w, h) :
        # Crop from bottom-right
        frame_rgb = frame_rgb[:new_h, :new_w]
        logging.debug(f"Frame {frame_index}: cropped {w}x{h} → {new_w}x{new_h}")

    out_filename = f"frame_{frame_index:04d}.txt"
    out_path = os.path.join(output_folder, out_filename)

    with open(out_path, 'w') as f :
        for y in range(new_h) :  
            for x in range(new_w) :
                r, g, b = frame_rgb[y, x]
                enc = common.rgb_to_encrypted_string(r, g, b)
                f.write(enc + ' ')
            f.write("\n")

def video_to_frames(video_path: str, output_folder: str) -> int :
    # Extract frames, crop, and save as encrypted text
    os.makedirs(output_folder, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("Could not open video file.")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    logging.info(f"Video: {os.path.basename(video_path)}")
    logging.info(f"Resolution: {width}x{height}, FPS: {fps:.2f}, Frames: {total_frames}")

    # Save metadata (original dimensions, FPS)
    meta_path = os.path.join(output_folder, "metadata.txt")
    with open(meta_path, 'w') as f:
        f.write(f"{width},{height},{fps}")

    success, frame = cap.read()
    frame_index = 0

    iterator = None
    if tqdm and total_frames > 0 :
        iterator = tqdm(total=total_frames, desc="Extracting frames", unit="frame")

    while success :
        process_frame(frame, frame_index, output_folder)
        frame_index += 1
        if iterator :
            iterator.update(1)
        success, frame = cap.read()

    cap.release()
    if iterator :
        iterator.close()

    logging.info(f"Saved {frame_index} frames to {output_folder}")
    return frame_index

# ----- Main ----- #

def main() :
    parser = argparse.ArgumentParser(description="Deconstruct video into encrypted text frames.")
    parser.add_argument('--dir', help='Base directory path')
    parser.add_argument('--folder', help='Folder containing the video file')
    parser.add_argument('--video', help='Video filename (optional, will prompt if not given)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--no-progress', action='store_true', help='Disable progress bar')
    args = parser.parse_args()

    common.setup_logging(args.verbose)

    if args.dir and args.folder :
        base_dir = args.dir
        folder_path = os.path.join(base_dir, args.folder)
        if not os.path.isdir(folder_path) :
            logging.error(f"Folder not found: {folder_path}")
            return
    else :
        try :
            base_dir, folder_path = common.select_directory_and_folder(purpose="select video folder")
        except Exception as e :
            logging.error(e)
            return

    # Find video files
    video_files = [f for f in os.listdir(folder_path)
                   if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')) and not f.startswith('.')]
    video_files.sort(key=common.natural_sort_key)

    if not video_files :
        logging.error("No video files found in folder.")
        return

    if args.video:
        if args.video in video_files :
            selected = args.video
        else :
            logging.error(f"Video '{args.video}' not found in folder.")
            return
    else :
        print("\nAvailable video files:")
        for i, f in enumerate(video_files):
            print(f"{i+1}. {f}")
        try :
            choice = int(input("Select video number: ")) - 1
            selected = video_files[choice]
        except (ValueError, IndexError) :
            logging.error("Invalid selection.")
            return

    video_path = os.path.join(folder_path, selected)
    video_name = os.path.splitext(selected)[0]
    output_folder = os.path.join(folder_path, f"{video_name}_frames")

    try :
        count = video_to_frames(video_path, output_folder)
        logging.info(f"Successfully deconstructed {count} frames.")
    except Exception as e :
        logging.error(f"Error processing video: {e}")

if __name__ == "__main__" :
    main()