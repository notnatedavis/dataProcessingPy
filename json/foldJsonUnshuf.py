# --- json/foldJsonUnshuf.py --- #
# Reverses character shuffle on all .json files in a folder
# Unshuffles both keys (object property names) and string values.
# Only letters A-Z and a-z are unshuffled; other characters remain unchanged.

# ----- Imports ----- #

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import logging
import json
import common
try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

# ----- Helper Functions ----- #

def unshuffle_string(s: str) -> str:
    """
    Unshuffle letters in a string using the static inverse map from common.
    Uppercase letters are mapped via common.CHAR_UNSHUFFLE_MAP.
    Lowercase letters are mapped via the same inverse map but returned as lowercase.
    Non-letters are unchanged.
    """
    result = []
    for ch in s:
        if 'A' <= ch <= 'Z':
            result.append(common.CHAR_UNSHUFFLE_MAP.get(ch, ch))
        elif 'a' <= ch <= 'z':
            upper = ch.upper()
            mapped = common.CHAR_UNSHUFFLE_MAP.get(upper, upper)
            result.append(mapped.lower())
        else:
            result.append(ch)
    return ''.join(result)

def unshuffle_json_data(data):
    """
    Recursively traverse JSON data and unshuffle all strings.
    For dictionaries, both keys and values are unshuffled.
    """
    if isinstance(data, dict):
        # Build new dict with unshuffled keys and unshuffled values
        unshuffled_dict = {}
        for key, value in data.items():
            new_key = unshuffle_string(key) if isinstance(key, str) else key
            unshuffled_dict[new_key] = unshuffle_json_data(value)
        return unshuffled_dict
    elif isinstance(data, list):
        return [unshuffle_json_data(item) for item in data]
    elif isinstance(data, str):
        return unshuffle_string(data)
    else:
        return data

def unshuffle_json_file(json_path: str) -> None:
    """Unshuffle a single JSON file in place."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            original = json.load(f)
    except Exception as e:
        raise IOError(f"Failed to read {json_path}: {e}")

    try:
        unshuffled = unshuffle_json_data(original)
    except Exception as e:
        raise ValueError(f"Unshuffle failed for {json_path}: {e}")

    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(unshuffled, f, indent=2, ensure_ascii=False)
            f.write('\n')
    except Exception as e:
        raise IOError(f"Failed to write unshuffled data to {json_path}: {e}")

    logging.info(f"Unshuffled: {os.path.basename(json_path)}")

# ----- Main ----- #

def main():
    parser = argparse.ArgumentParser(description="Unshuffle all .json files in a folder.")
    parser.add_argument('--dir', help='Base directory path')
    parser.add_argument('--folder', help='Folder name inside base directory')
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
            base_dir, folder_path = common.select_directory_and_folder(purpose="unshuffle JSON")
        except Exception as e:
            logging.error(e)
            return

    json_files = [f for f in os.listdir(folder_path)
                  if f.lower().endswith('.json') and not f.startswith('.')]
    json_files.sort(key=common.natural_sort_key)

    if not json_files:
        logging.error("No .json files found.")
        return

    logging.info(f"Found {len(json_files)} files. Starting unshuffle...")

    iterator = json_files
    if tqdm and not args.no_progress:
        iterator = tqdm(json_files, desc="Unshuffling JSON", unit="file")

    for json_file in iterator:
        json_path = os.path.join(folder_path, json_file)
        try:
            unshuffle_json_file(json_path)
        except Exception as e:
            logging.error(f"Error processing {json_file}: {e}")

    logging.info("All .json files processed.")

if __name__ == "__main__":
    main()