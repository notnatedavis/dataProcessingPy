# ----- vid/videoToTxt.py ----- 
# Deconstructs a video into encrypted text frames using ffmpeg.
# Crops each frame to dimensions divisible by GRID_DIVISOR and saves metadata.txt.

# ----- Imports -----
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import logging
import subprocess as sp
import numpy as np
import common
try:
    import ffmpeg
except ImportError:
    logging.error("ffmpeg-python not installed. Run: pip install ffmpeg-python")
    sys.exit(1)
try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

# ----- Helper Functions -----
def frame_to_text(frame_rgb: np.ndarray, frame_index: int, output_folder: str,
                  crop_w: int, crop_h: int) -> None:
    """
    Convert a single RGB frame (numpy array) to encrypted text and save.
    The frame may already be cropped; this function writes the text file.
    """
    # Ensure frame is cropped to the expected dimensions (should already be)
    if frame_rgb.shape[:2] != (crop_h, crop_w):
        # Crop from top-left (ffmpeg raw video gives full frame; we crop after)
        frame_rgb = frame_rgb[:crop_h, :crop_w]

    out_filename = f"frame_{frame_index:04d}.txt"
    out_path = os.path.join(output_folder, out_filename)

    with open(out_path, 'w') as f:
        for y in range(crop_h):
            for x in range(crop_w):
                r, g, b = frame_rgb[y, x]
                enc = common.rgb_to_encrypted_string(int(r), int(g), int(b))
                f.write(enc + ' ')
            f.write("\n")


def video_to_frames_ffmpeg(video_path: str, output_folder: str) -> int:
    """Extract frames via ffmpeg pipe, crop, and save as encrypted text."""
    os.makedirs(output_folder, exist_ok=True)

    # Probe video to get info
    try:
        probe = ffmpeg.probe(video_path)
    except ffmpeg.Error as e:
        raise RuntimeError(f"ffmpeg probe failed: {e.stderr.decode()}")

    video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
    if not video_stream:
        raise ValueError("No video stream found.")

    orig_w = int(video_stream['width'])
    orig_h = int(video_stream['height'])
    fps = eval(video_stream['r_frame_rate'])  # may be fraction like "30000/1001"
    total_frames = int(video_stream.get('nb_frames', 0))
    if total_frames == 0:
        # Estimate duration * fps if nb_frames missing
        duration = float(probe['format']['duration'])
        total_frames = int(duration * fps)

    # Determine cropped dimensions (same for all frames)
    crop_w, crop_h = common.crop_to_divisible(orig_w, orig_h)

    logging.info(f"Video: {os.path.basename(video_path)}")
    logging.info(f"Original resolution: {orig_w}x{orig_h}, FPS: {fps:.2f}, Frames: {total_frames}")
    if (crop_w, crop_h) != (orig_w, orig_h):
        logging.info(f"Frames will be cropped to {crop_w}x{crop_h} for divisibility by {common.GRID_DIVISOR}")

    # Save metadata with cropped dimensions
    meta_path = os.path.join(output_folder, "metadata.txt")
    with open(meta_path, 'w') as f:
        f.write(f"{crop_w},{crop_h},{fps}")

    # Build ffmpeg command to output raw RGB frames (one per frame)
    # We'll read from stdout and process frame by frame.
    process = (
        ffmpeg
        .input(video_path)
        .output('pipe:', format='rawvideo', pix_fmt='rgb24')
        .run_async(pipe_stdout=True, pipe_stderr=True)
    )

    frame_size = orig_w * orig_h * 3  # bytes per frame (RGB)
    frame_index = 0
    bytes_remaining = b''

    iterator = None
    if tqdm and total_frames > 0:
        iterator = tqdm(total=total_frames, desc="Extracting frames", unit="frame")

    while True:
        # Read raw frame data from stdout
        raw_chunk = process.stdout.read(frame_size)
        if not raw_chunk:
            break
        # Combine with any leftover bytes from previous iteration
        data = bytes_remaining + raw_chunk
        if len(data) < frame_size:
            # Incomplete frame, store leftover and continue
            bytes_remaining = data
            continue

        # We have at least one complete frame
        frame_data = data[:frame_size]
        bytes_remaining = data[frame_size:]

        # Convert to numpy array (height x width x 3)
        frame_rgb = np.frombuffer(frame_data, dtype=np.uint8).reshape((orig_h, orig_w, 3))

        # Crop to divisible dimensions
        if (crop_w, crop_h) != (orig_w, orig_h):
            frame_rgb = frame_rgb[:crop_h, :crop_w]

        frame_to_text(frame_rgb, frame_index, output_folder, crop_w, crop_h)
        frame_index += 1
        if iterator:
            iterator.update(1)

        # If there's leftover data, it will be prepended next iteration

    process.stdout.close()
    process.wait()

    if iterator:
        iterator.close()

    logging.info(f"Saved {frame_index} frames to {output_folder}")
    return frame_index

# ----- Main -----
def main():
    parser = argparse.ArgumentParser(description="Deconstruct video into encrypted text frames using ffmpeg.")
    parser.add_argument('--dir', help='Base directory path')
    parser.add_argument('--folder', help='Folder containing the video file')
    parser.add_argument('--video', help='Video filename (optional, will prompt if not given)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--no-progress', action='store_true', help='Disable progress bar')
    args = parser.parse_args()

    common.setup_logging(args.verbose)

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

    # Find video files
    video_files = [f for f in os.listdir(folder_path)
                   if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')) and not f.startswith('.')]
    video_files.sort(key=common.natural_sort_key)

    if not video_files:
        logging.error("No video files found in folder.")
        return

    if args.video:
        if args.video in video_files:
            selected = args.video
        else:
            logging.error(f"Video '{args.video}' not found in folder.")
            return
    else:
        print("\nAvailable video files:")
        for i, f in enumerate(video_files):
            print(f"{i+1}. {f}")
        try:
            choice = int(input("Select video number: ")) - 1
            selected = video_files[choice]
        except (ValueError, IndexError):
            logging.error("Invalid selection.")
            return

    video_path = os.path.join(folder_path, selected)
    video_name = os.path.splitext(selected)[0]
    output_folder = os.path.join(folder_path, f"{video_name}_frames")

    try:
        count = video_to_frames_ffmpeg(video_path, output_folder)
        logging.info(f"Successfully deconstructed {count} frames.")
    except Exception as e:
        logging.error(f"Error processing video: {e}")

if __name__ == "__main__":
    main()