# --- vid/txtToVideo.py --- #
# Reconstructs a video from encrypted text frame files using ffmpeg.
# Reads metadata.txt for dimensions and FPS, then pipes raw frames to ffmpeg.
# Now includes live ffmpeg statistics in the tqdm progress bar.

# ----- Imports -----
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import logging
import subprocess as sp
import numpy as np
import re
import queue
import threading
import io
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
def text_to_frame(text_path: str, width: int, height: int) -> np.ndarray:
    """Convert a single text frame file to a numpy RGB array (shape: height x width x 3)."""
    with open(text_path, 'r') as f:
        lines = f.readlines()

    # Validate dimensions (should match metadata)
    if len(lines) != height:
        raise ValueError(f"Frame height mismatch: expected {height}, got {len(lines)}")
    first_line = lines[0].strip().split()
    if len(first_line) != width:
        raise ValueError(f"Frame width mismatch: expected {width}, got {len(first_line)}")

    frame = np.zeros((height, width, 3), dtype=np.uint8)

    for y, line in enumerate(lines):
        encrypted_pixels = line.strip().split()
        for x, enc in enumerate(encrypted_pixels):
            r, g, b = common.encrypted_pixel_to_rgb(enc)
            # Clip values to the valid 0-255 range (needed for shuffled frames)
            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))
            frame[y, x] = [r, g, b]   # RGB order

    return frame


def frames_to_video_ffmpeg(input_folder: str, output_video_path: str, no_progress: bool = False) -> int:
    """Assemble frames into a video by piping raw RGB to ffmpeg.
       Displays live ffmpeg statistics in the tqdm progress bar.
    """
    metadata_path = os.path.join(input_folder, "metadata.txt")
    if not os.path.exists(metadata_path):
        raise FileNotFoundError("metadata.txt not found in input folder")

    with open(metadata_path, 'r') as f:
        meta = f.read().strip().split(',')
        width = int(meta[0])
        height = int(meta[1])
        fps = float(meta[2])

    # Get all .txt files except metadata.txt
    frame_files = [f for f in os.listdir(input_folder)
                   if f.endswith('.txt') and f != 'metadata.txt']
    frame_files.sort(key=common.natural_sort_key)

    if not frame_files:
        raise ValueError("No frame files found.")

    logging.info(f"Reconstructing {len(frame_files)} frames to {output_video_path}")
    logging.info(f"Dimensions: {width}x{height}, FPS: {fps}")

    # Build ffmpeg command to read raw RGB from stdin and encode to video
    process = (
        ffmpeg
        .input('pipe:', format='rawvideo', pix_fmt='rgb24', s=f'{width}x{height}')
        .output(output_video_path, vcodec='libx264', r=fps, pix_fmt='yuv420p')
        .overwrite_output()
        .run_async(pipe_stdin=True, pipe_stderr=True)   # <-- capture stderr
    )

    # ---------- Background thread to read ffmpeg stderr ----------
    stat_queue = queue.Queue()
    stop_reader = threading.Event()

    def stderr_reader():
        """Read lines from ffmpeg stderr, parse key=value pairs, and put updates into the queue."""
        # Wrap the byte stream in a text wrapper for line-by-line reading
        with process.stderr:
            text_stream = io.TextIOWrapper(process.stderr, encoding='utf-8', errors='replace')
            for line in text_stream:
                if stop_reader.is_set():
                    break
                # Find all key=value pairs (values may contain units like 'KiB', 'kbits/s')
                matches = re.findall(r'(\w+)=\s*([^\s]+)', line)
                if matches:
                    stat_update = dict(matches)
                    stat_queue.put(stat_update)
        # Signal end of stream
        stat_queue.put(None)

    reader_thread = threading.Thread(target=stderr_reader)
    reader_thread.start()

    # ---------- Main encoding loop ----------
    use_tqdm = tqdm is not None and not no_progress
    if use_tqdm:
        pbar = tqdm(total=len(frame_files), desc="(w) frames ", unit="frame")
    else:
        pbar = None

    stats = {}   # holds the latest ffmpeg statistics

    for frame_file in frame_files:
        frame_path = os.path.join(input_folder, frame_file)
        frame_rgb = text_to_frame(frame_path, width, height)
        process.stdin.write(frame_rgb.tobytes())

        if use_tqdm:
            pbar.update(1)

        # Drain any new statistics from the queue
        while True:
            try:
                update = stat_queue.get_nowait()
                if update is None:          # EOF marker
                    break
                stats.update(update)
            except queue.Empty:
                break

        # --- Whitelist only the statistics we want to display ---
        keep_keys = {'size'} # frame , fps , bitrate , time 
        stats = {k: v for k, v in stats.items() if k in keep_keys}
        # ---------------------------------------------------------

        # Update the progress bar with the filtered stats
        if use_tqdm and stats:
            pbar.set_postfix(**stats)

    # ---------- Cleanup ----------
    process.stdin.close()
    process.wait()

    stop_reader.set()
    reader_thread.join(timeout=2)

    if use_tqdm:
        pbar.close()

    if process.returncode != 0:
        raise RuntimeError("ffmpeg encoding failed")

    return len(frame_files)


# ----- Main -----
def main():
    parser = argparse.ArgumentParser(description="Reconstruct video from encrypted text frames using ffmpeg.")
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
        count = frames_to_video_ffmpeg(target_folder, output_path, no_progress=args.no_progress)
        logging.info(f"Success! Reconstructed {count} frames to {output_path}")
    except Exception as e:
        logging.error(f"Error reconstructing video: {e}")

if __name__ == "__main__":
    main()