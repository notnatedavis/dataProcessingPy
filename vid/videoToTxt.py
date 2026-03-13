# ----- vid/videoToTxt.py ----- 
# Deconstructs a video into encrypted text frames using ffmpeg.
# Crops each frame to dimensions divisible by GRID_DIVISOR and saves metadata.txt.
# Enhanced with dimension validation, frame count checks, and error handling.

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
    The frame is assumed to be already cropped to (crop_h, crop_w).
    """
    # Verify dimensions
    if frame_rgb.shape[:2] != (crop_h, crop_w):
        # Crop from top-left if needed (shouldn't happen, but handle gracefully)
        logging.warning(f"Frame {frame_index} has unexpected size {frame_rgb.shape[:2]}, cropping to {crop_h}x{crop_w}")
        frame_rgb = frame_rgb[:crop_h, :crop_w]

    out_filename = f"frame_{frame_index:04d}.txt"
    out_path = os.path.join(output_folder, out_filename)

    try:
        with open(out_path, 'w') as f:
            for y in range(crop_h):
                for x in range(crop_w):
                    r, g, b = frame_rgb[y, x]
                    # Ensure values are integers within 0-255
                    r = int(max(0, min(255, r)))
                    g = int(max(0, min(255, g)))
                    b = int(max(0, min(255, b)))
                    enc = common.rgb_to_encrypted_string(r, g, b)
                    f.write(enc + ' ')
                f.write("\n")
    except Exception as e:
        raise IOError(f"Failed to write frame {frame_index} to {out_path}: {e}")

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
        # Estimate from duration
        duration = float(probe['format']['duration'])
        total_frames = int(duration * fps)
        logging.info(f"Estimated total frames: {total_frames}")

    # Determine cropped dimensions (same for all frames)
    crop_w, crop_h = common.crop_to_divisible(orig_w, orig_h)
    if crop_w == 0 or crop_h == 0:
        raise ValueError(f"Cropped dimensions are zero: {crop_w}x{crop_h}. Video too small for divisor {common.GRID_DIVISOR}.")

    logging.info(f"Video: {os.path.basename(video_path)}")
    logging.info(f"Original resolution: {orig_w}x{orig_h}, FPS: {fps:.2f}, Frames: {total_frames}")
    if (crop_w, crop_h) != (orig_w, orig_h):
        logging.info(f"Frames will be cropped to {crop_w}x{crop_h} for divisibility by {common.GRID_DIVISOR}")

    # Save metadata with cropped dimensions
    meta_path = os.path.join(output_folder, "metadata.txt")
    try:
        with open(meta_path, 'w') as f:
            f.write(f"{crop_w},{crop_h},{fps}")
    except Exception as e:
        raise IOError(f"Failed to write metadata: {e}")

    # Build ffmpeg command to output raw RGB frames
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

    failed_frames = 0

    while True:
        try:
            raw_chunk = process.stdout.read(frame_size)
        except Exception as e:
            logging.error(f"Error reading from ffmpeg stdout: {e}")
            break

        if not raw_chunk:
            break

        # Combine with leftover bytes
        data = bytes_remaining + raw_chunk
        if len(data) < frame_size:
            bytes_remaining = data
            continue

        # Process one full frame
        frame_data = data[:frame_size]
        bytes_remaining = data[frame_size:]

        # Convert to numpy array
        try:
            frame_rgb = np.frombuffer(frame_data, dtype=np.uint8).reshape((orig_h, orig_w, 3))
        except Exception as e:
            logging.error(f"Failed to reshape frame {frame_index}: {e}")
            failed_frames += 1
            continue

        # Crop to divisible dimensions
        if (crop_w, crop_h) != (orig_w, orig_h):
            frame_rgb = frame_rgb[:crop_h, :crop_w]

        # Save frame
        try:
            frame_to_text(frame_rgb, frame_index, output_folder, crop_w, crop_h)
        except Exception as e:
            logging.error(f"Failed to save frame {frame_index}: {e}")
            failed_frames += 1

        frame_index += 1
        if iterator:
            iterator.update(1)

    process.stdout.close()
    process.wait()

    if iterator:
        iterator.close()

    if failed_frames > 0:
        logging.warning(f"Encountered errors on {failed_frames} frames.")

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

    # Determine base directory and folder
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
            logging.error(f"Directory selection failed: {e}")
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
        if count > 0:
            logging.info(f"Successfully deconstructed {count} frames.")
        else:
            logging.error("No frames were extracted.")
    except Exception as e:
        logging.error(f"Error processing video: {e}")

if __name__ == "__main__":
    main()