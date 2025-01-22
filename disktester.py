#!/usr/bin/env python3
import os
import hashlib
import shutil
import argparse
from tqdm import tqdm
import re


def write_random_data(filepath: str, size_bytes: int) -> list[str, int]:
    sha1_hash = hashlib.sha1()
    total_bytes = 0

    if size_bytes % 1000 != 0:
        raise ValueError("Size must be a multiple of 1000 bytes")

    with open(filepath, "wb") as f:
        for _ in range(int(size_bytes // 1000)):
            data = os.urandom(1000)
            total_bytes += 1000
            sha1_hash.update(data)
            f.write(data)

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File {filepath} not found")

    hash_file = filepath + ".sha1"
    with open(hash_file, "w") as f:
        f.write(sha1_hash.hexdigest())

    return [sha1_hash.hexdigest(), total_bytes]


def is_sha1_hex(s: str) -> bool:
    return all(c in "0123456789abcdef" for c in s) and len(s) == 40


def validate_data(filepath: str) -> bool:
    sha1_hash = hashlib.sha1()
    hash_file = filepath + ".sha1"

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File {filepath} not found")

    if not os.path.exists(hash_file):
        raise FileNotFoundError(f"Hash file {hash_file} not found")

    with open(hash_file, "r") as f:
        hash_value = f.read()

    if not hash_value:
        raise ValueError("Hash value is empty")

    if not is_sha1_hex(hash_value):
        raise ValueError("Hash value is not a valid SHA-1 hash")

    file_size = os.path.getsize(filepath)
    if file_size % 1024 != 0:
        print(f"Warning: File size is not a multiple of 1024 bytes, continuing...")

    with open(filepath, "rb") as f:
        while True:
            data = f.read(1024)
            if not data:
                break
            sha1_hash.update(data)

    return sha1_hash.hexdigest() == hash_value


def get_space_available(path: str) -> int:
    stat = shutil.disk_usage(path)
    return stat.free


CHUNK_SIZE = 200 * 1e6


def cmd_test_disk(root_folder: str, write_bytes: int, chunk_size: int = CHUNK_SIZE):
    dest_folder = os.path.join(root_folder, "disktester")
    write_GB = int(write_bytes // 1e9)
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)

    space_available_bytes = get_space_available(dest_folder)
    print(f"Space available: {space_available_bytes // 1e9} GB")

    if space_available_bytes < write_bytes:
        raise ValueError(
            f"Insufficient space available in {dest_folder} to write {write_GB} GB"
        )

    int_num_chunks = int(write_bytes // chunk_size)

    print(
        f"Testing disk {root_folder} with {write_GB} GB of random data, {int(chunk_size // 1e6)}MB x {int_num_chunks} chunks"
    )

    for i in tqdm(
        range(int_num_chunks), desc="Writing data", unit="chunk", dynamic_ncols=True
    ):
        fn = f"chunk_{i}.dat"
        fp = os.path.join(dest_folder, fn)
        write_random_data(fp, chunk_size)

    print("Validating data...")
    for i in tqdm(
        range(int_num_chunks), desc="Validating data", unit="chunk", dynamic_ncols=True
    ):
        fn = f"chunk_{i}.dat"
        fp = os.path.join(dest_folder, fn)
        assert validate_data(fp), f"Data validation failed for {fp} aborting..."

    print("All data validated successfully")


def is_empty_folder(folder: str) -> bool:
    return not any(f for f in os.listdir(folder) if not f in [".DS_Store", "Thumbs.db"])


def cmd_clean_disk(root_folder: str):
    dest_folder = os.path.join(root_folder, "disktester")
    if not os.path.exists(dest_folder):
        print(f"Folder {dest_folder} does not exist, nothing to clean")
        return

    print(f"Cleaning folder {dest_folder}")
    for root, dirs, files in os.walk(dest_folder):
        for f in files:
            valid_remove_fn = None
            if re.match(r"chunk_\d+\.dat(?:\.sha1)?", f) is not None:
                valid_remove_fn = os.path.join(root, f)

            if valid_remove_fn is not None:
                os.remove(valid_remove_fn)
                print(f"Removed {valid_remove_fn}")

    if is_empty_folder(dest_folder):
        os.rmdir(dest_folder)
        print(f"Folder {dest_folder} is now empty and has been removed")
    else:
        print(f"Folder {dest_folder} is not empty, not removing")


if __name__ == "__main__":

    args = argparse.ArgumentParser(
        description="Disk tester, writes and validates random data to disk in chunks with checksum files"
    )

    # Example usage: python disktester.py test -f /Volumes/disk1 -s 500
    # This will write 500 GB of random data to /Volumes/disk1/disktester/chunk_{i}.dat
    # and validate the data afterwards

    # Example usage: python disktester.py clean -f /Volumes/disk1
    # This will delete all valid chunk files in /Volumes/disk1/disktester if they exist, and remove disktester folder if empty
    # A folder with only .DS_Store and Thumbs.db files is considered empty

    args.add_argument(
        "action", type=str, help="Action to perform: test or clean", default="test"
    )
    args.add_argument(
        "-f",
        "--folder",
        type=str,
        help="Folder to test or clean",
        default="/Volumes/2TData",
    )
    args.add_argument(
        "-s",
        "--size",
        type=int,
        help="Size of random data to write in GB. Leave some freespace for .sha1 checksum files",
        default=500,
    )
    args.add_argument(
        "-c",
        "--chunksize",
        type=int,
        help="Size of each chunk file in MB",
        default=200,
    )

    args = args.parse_args()

    if args.action == "test":
        cmd_test_disk(args.folder, args.size * 1e9, args.chunksize * 1e6)
    elif args.action == "clean":
        cmd_clean_disk(args.folder)
