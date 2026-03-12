# --- vid/txtToVideo.py --- #
# Reconstructs a video from encrypted text frame files.
# Uses cropped dimensions stored in metadata.txt.

# ----- Imports -----
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import logging
import cv2
import numpy as np
import common
try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

# ----- Helper Functions -----
def text_to_frame(text_path: str) -> np.ndarray:
    """Convert a single text frame file to a numpy BGR image array."""
    with open(text_path, 'r') as f:
        lines = f.readlines()

    height = len(lines)
    width = len(lines[0].strip().split())

    frame = np.zeros((height, width, 3), dtype=np.uint8)

    for y, line in enumerate(lines):
        encrypted_pixels = line.strip().split()
        for x, enc in enumerate(encrypted_pixels):
            r, g, b = common.encrypted_pixel_to_rgb(enc)
            # Clip to 0-255 as a safety measure (shuffling keeps values valid, but harmless)
            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))
            frame[y, x] = [b, g, r]  # BGR for OpenCV

    return frame


def frames_to_video(input_folder: str, output_video_path: str) -> int:
    """Assemble frames into a lossless video using dimensions from metadata."""
    metadata_path = os.path.join(input_folder, "metadata.txt")
    if not os.path.exists(metadata_path):
        raise FileNotFoundError("metadata.txt not found in input folder")

    with open(metadata_path, 'r') as f:
        meta = f.read().strip().split(',')
        width = int(meta[0])
        height = int(meta[1])
        fps = float(meta[2])

    frame_files = [f for f in os.listdir(input_folder)
                   if f.endswith('.txt') and f != 'metadata.txt']
    frame_files.sort(key=common.natural_sort_key)

    if not frame_files:
        raise ValueError("No frame files found.")

    # Try lossless codec
    fourcc = cv2.VideoWriter_fourcc(*'FFV1')
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))
    if not out.isOpened():
        fourcc = cv2.VideoWriter_fourcc(*'avc1')
        out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))
        if not out.isOpened():
            raise RuntimeError("Could not open video writer with lossless settings")

    logging.info(f"Reconstructing {len(frame_files)} frames to {output_video_path}")
    logging.info(f"Output dimensions: {width}x{height}, FPS: {fps}")

    iterator = frame_files
    if tqdm:
        iterator = tqdm(frame_files, desc="Writing frames", unit="frame")

    for frame_file in iterator:
        frame_path = os.path.join(input_folder, frame_file)
        frame = text_to_frame(frame_path)
        out.write(frame)

    out.release()
    return len(frame_files)

# ----- Main -----
def main():
    parser = argparse.ArgumentParser(description="Reconstruct video from encrypted text frames.")
    parser.add_argument('--dir', help='Base directory path')
    parser.add_argument('--folder', help='Folder containing the _frames folder (e.g., video_frames)')
    parser.add_argument('--subfolder', help='Specific frame folder name (e.g., video_frames)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--no-progress', action='store_true', help='Disable progress bar')
    args = parser.parse_args()

    common.setup_logging(args.verbose)

    # --- Step 1: Determine base directory and main folder ---
    if args.dir and args.folder:
        base_dir = args.dir
        folder_path = os.path.join(base_dir, args.folder)
        if not os.path.isdir(folder_path):
            logging.error(f"Folder not found: {folder_path}")
            return
    else:
        try:
            base_dir, folder_path = common.select_directory_and_folder(purpose="select video folder")
        except Exception as e:
            logging.error(e)
            return

    # --- Step 2: Determine subfolder containing the frames ---
    if args.subfolder:
        target_folder = os.path.join(folder_path, args.subfolder)
        if not os.path.isdir(target_folder):
            logging.error(f"Subfolder not found: {target_folder}")
            return
    else:
        # Look for subfolders ending with '_frames'
        try:
            target_folder = common.select_subfolder(folder_path, suffix="_frames", purpose="reconstruct video")
        except Exception as e:
            logging.error(e)
            return

    # --- Step 3: Output video path ---
    video_name = os.path.basename(target_folder).replace('_frames', '') + '_reconstructed.mov'
    output_path = os.path.join(folder_path, video_name)

    try:
        count = frames_to_video(target_folder, output_path)
        logging.info(f"Success! Reconstructed {count} frames to {output_path}")
    except Exception as e:
        logging.error(f"Error reconstructing video: {e}")


if __name__ == "__main__":
    main()