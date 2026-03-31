#!/usr/bin/env python3
import argparse
import hashlib
import logging
import os
import shutil
import sys
import urllib.request
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)
logger = logging.getLogger("download_verify")


def compute_sha256(file_path: str, chunk_size: int = 8192) -> str:
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def compute_md5(file_path: str, chunk_size: int = 8192) -> str:
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


def verify_file(file_path: str, expected_hash: str, hash_algorithm: str = "sha256") -> bool:
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return False

    logger.info(f"Computing {hash_algorithm} checksum for {file_path}...")
    if hash_algorithm.lower() == "sha256":
        actual_hash = compute_sha256(file_path)
    elif hash_algorithm.lower() == "md5":
        actual_hash = compute_md5(file_path)
    else:
        logger.error(f"Unsupported hash algorithm: {hash_algorithm}")
        return False

    if actual_hash.lower() == expected_hash.lower():
        logger.info(f"Checksum verification PASSED: {actual_hash}")
        return True
    else:
        logger.error(f"Checksum verification FAILED: expected {expected_hash}, got {actual_hash}")
        return False


def download_file(url: str, dest_path: str, max_retries: int = 3, timeout: int = 300) -> bool:
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Downloading {url} (attempt {attempt}/{max_retries})...")

            def reporthook(block_num: int, block_size: int, total_size: int):
                if total_size > 0:
                    percent = min(100, (block_num * block_size * 100) // total_size)
                    if block_num % 100 == 0:
                        logger.info(f"Download progress: {percent}%")

            urllib.request.urlretrieve(url, dest_path, reporthook)
            logger.info(f"Downloaded successfully to {dest_path}")
            return True

        except Exception as e:
            logger.warning(f"Download attempt {attempt} failed: {e}")
            if attempt < max_retries:
                import time
                wait_time = 2 ** attempt
                logger.info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                logger.error(f"Download failed after {max_retries} attempts")
                if dest_path.exists():
                    os.remove(dest_path)
                return False

    return False


def download_and_verify(
    url: str,
    dest_path: str,
    expected_hash: str | None = None,
    hash_algorithm: str = "sha256",
    max_retries: int = 3,
) -> int:
    os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)

    if os.path.exists(dest_path) and expected_hash:
        logger.info(f"File already exists at {dest_path}, verifying...")
        if verify_file(dest_path, expected_hash, hash_algorithm):
            logger.info("Existing file verified successfully")
            return 0
        else:
            logger.warning("Existing file verification failed, re-downloading...")
            os.remove(dest_path)

    if not download_file(url, dest_path, max_retries):
        logger.error(f"Failed to download {url}")
        return 1

    if expected_hash:
        if not verify_file(dest_path, expected_hash, hash_algorithm):
            logger.error(f"Checksum verification failed for {dest_path}")
            return 1
        logger.info("Download and verification completed successfully")
    else:
        logger.info("Download completed (no checksum provided)")

    return 0


def download_tts_model(
    model_name: str,
    cache_dir: str,
    max_retries: int = 3,
) -> int:
    logger.info(f"Preparing to download TTS model: {model_name}")
    logger.info(f"Cache directory: {cache_dir}")

    os.environ["TTS_CACHE_DIR"] = cache_dir
    os.environ["HF_HOME"] = os.path.join(cache_dir, "hf")
    os.environ["TRANSFORMERS_CACHE"] = os.path.join(cache_dir, "hf")
    os.environ["COQUI_TOS_AGREED"] = "1"

    os.makedirs(cache_dir, exist_ok=True)
    os.makedirs(os.path.join(cache_dir, "hf"), exist_ok=True)

    try:
        from TTS.api import TTS
        logger.info(f"Downloading XTTS-v2 model '{model_name}'...")
        tts = TTS(model_name)
        logger.info("XTTS-v2 model downloaded and cached successfully")
        tts = None
        return 0
    except Exception as e:
        logger.error(f"Failed to download TTS model: {e}")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Download and verify model files")
    parser.add_argument("--url", help="URL to download")
    parser.add_argument("--dest", help="Destination path")
    parser.add_argument("--expected-hash", help="Expected file hash (SHA256 or MD5)")
    parser.add_argument("--hash-algo", default="sha256", choices=["sha256", "md5"], help="Hash algorithm")
    parser.add_argument("--max-retries", type=int, default=3, help="Maximum download retries")
    parser.add_argument("--model-name", help="TTS model name (e.g., tts_models/multilingual/multi-dataset/xtts_v2)")
    parser.add_argument("--cache-dir", help="Model cache directory")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.model_name and args.cache_dir:
        return download_tts_model(args.model_name, args.cache_dir, args.max_retries)
    elif args.url and args.dest:
        return download_and_verify(
            args.url,
            args.dest,
            args.expected_hash,
            args.hash_algo,
            args.max_retries,
        )
    else:
        logger.error("Either --model-name with --cache-dir, or --url with --dest, is required")
        return 1


if __name__ == "__main__":
    sys.exit(main())