import os
import shutil
import mimetypes
import folder_paths
import hashlib
import json
import subprocess
from threading import Lock

from . import config
from . import ffmpeg_config
from . import utils
from typing import Literal


def _get_ffmpeg_cmd():
    """Get FFmpeg command (path from config)"""
    return ffmpeg_config.get_ffmpeg_path()


def get_file_content_type(filename: str):
    extension_mimetypes_cache = folder_paths.extension_mimetypes_cache

    extension = filename.split(".")[-1].lower()
    content_type = None
    if extension not in extension_mimetypes_cache:
        mime_type, _ = mimetypes.guess_type(filename, strict=False)
        if mime_type:
            content_type = mime_type.split("/")[0]
            extension_mimetypes_cache[extension] = content_type
    else:
        content_type = extension_mimetypes_cache[extension]

    return content_type


def assert_file_type(filename: str, content_types: Literal["image", "video", "audio"]):
    content_type = get_file_content_type(filename)
    if not content_type:
        return False
    return content_type in content_types


# ============================================================================
# Disk Cache with configurable size
# ============================================================================

class DiskCache:
    """
    Disk-based cache for thumbnails.
    Stores thumbnails as files on disk, survives restarts.
    """
    
    CONFIG_FILE = "cache_config.json"
    DEFAULT_MAX_SIZE_GB = 2.0  # Increased from 1.0 for better caching
    
    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        self.lock = Lock()
        self._ensure_cache_dir()
        self._load_config()
    
    def _ensure_cache_dir(self):
        """Create cache directory if it doesn't exist"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def _get_config_path(self) -> str:
        return os.path.join(self.cache_dir, self.CONFIG_FILE)
    
    def _load_config(self):
        """Load cache configuration from disk"""
        config_path = self._get_config_path()
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    cfg = json.load(f)
                    self.max_size_gb = cfg.get('max_size_gb', self.DEFAULT_MAX_SIZE_GB)
            else:
                self.max_size_gb = self.DEFAULT_MAX_SIZE_GB
        except Exception:
            self.max_size_gb = self.DEFAULT_MAX_SIZE_GB
    
    def _save_config(self):
        """Save cache configuration to disk"""
        config_path = self._get_config_path()
        try:
            with open(config_path, 'w') as f:
                json.dump({'max_size_gb': self.max_size_gb}, f)
        except Exception as e:
            utils.print_error(f"Failed to save cache config: {e}")
    
    def set_max_size(self, size_gb: float):
        """Set maximum cache size in GB"""
        self.max_size_gb = max(1.0, min(size_gb, 100.0))  # Clamp between 1GB and 100GB
        self._save_config()
        # Trigger cleanup if over limit
        self.cleanup()
    
    def get_max_size(self) -> float:
        """Get maximum cache size in GB"""
        return self.max_size_gb
    
    @property
    def max_size_bytes(self) -> int:
        return int(self.max_size_gb * 1024 * 1024 * 1024)
    
    def _get_cache_path(self, key: str) -> str:
        """Convert cache key to file path"""
        # Use first 2 chars as subdirectory for better filesystem performance
        subdir = key[:2]
        cache_subdir = os.path.join(self.cache_dir, subdir)
        if not os.path.exists(cache_subdir):
            try:
                os.makedirs(cache_subdir)
            except FileExistsError:
                pass
        return os.path.join(cache_subdir, f"{key}.webp")
    
    def get(self, key: str) -> bytes | None:
        """Get cached data by key"""
        cache_path = self._get_cache_path(key)
        
        try:
            if os.path.exists(cache_path):
                # Update access time for LRU
                os.utime(cache_path, None)
                with open(cache_path, 'rb') as f:
                    return f.read()
        except (OSError, IOError):
            pass
        
        return None
    
    def set(self, key: str, data: bytes):
        """Store data in cache"""
        cache_path = self._get_cache_path(key)
        
        try:
            with open(cache_path, 'wb') as f:
                f.write(data)
        except (OSError, IOError) as e:
            utils.print_error(f"Failed to write cache: {e}")
    
    def get_cache_size(self) -> int:
        """Calculate total cache size in bytes"""
        total_size = 0
        try:
            for root, dirs, files in os.walk(self.cache_dir):
                for f in files:
                    if f.endswith('.webp'):
                        fp = os.path.join(root, f)
                        try:
                            total_size += os.path.getsize(fp)
                        except OSError:
                            pass
        except OSError:
            pass
        return total_size
    
    def get_cache_info(self) -> dict:
        """Get cache statistics"""
        size_bytes = self.get_cache_size()
        return {
            "size_bytes": size_bytes,
            "size_mb": round(size_bytes / (1024 * 1024), 2),
            "size_gb": round(size_bytes / (1024 * 1024 * 1024), 2),
            "max_size_gb": self.max_size_gb,
            "usage_percent": round((size_bytes / self.max_size_bytes) * 100, 1) if self.max_size_bytes > 0 else 0,
        }
    
    def cleanup(self, target_size_bytes: int = None):
        """
        Remove oldest files until cache is under target size.
        Called periodically or when cache is full.
        """
        if target_size_bytes is None:
            target_size_bytes = int(self.max_size_bytes * 0.8)  # Clean to 80%
        
        with self.lock:
            # Get all cache files with their access times
            cache_files = []
            try:
                for root, dirs, files in os.walk(self.cache_dir):
                    for f in files:
                        if f.endswith('.webp'):
                            fp = os.path.join(root, f)
                            try:
                                stat = os.stat(fp)
                                cache_files.append((fp, stat.st_atime, stat.st_size))
                            except OSError:
                                pass
            except OSError:
                return
            
            # Calculate current size
            current_size = sum(f[2] for f in cache_files)
            
            if current_size <= self.max_size_bytes:
                return
            
            # Sort by access time (oldest first)
            cache_files.sort(key=lambda x: x[1])
            
            # Remove oldest files until under target
            for filepath, atime, size in cache_files:
                if current_size <= target_size_bytes:
                    break
                try:
                    os.remove(filepath)
                    current_size -= size
                except OSError:
                    pass
            
            utils.print_debug(f"Cache cleanup: removed files, new size: {current_size / (1024*1024):.1f} MB")
    
    def clear(self):
        """Clear entire cache"""
        with self.lock:
            try:
                for root, dirs, files in os.walk(self.cache_dir):
                    for f in files:
                        if f.endswith('.webp'):
                            try:
                                os.remove(os.path.join(root, f))
                            except OSError:
                                pass
            except OSError as e:
                utils.print_error(f"Failed to clear cache: {e}")


class CacheHelper:
    def __init__(self) -> None:
        self.cache: dict[str, tuple[list, float]] = {}
        self.cache_lock = Lock()
        
        # Initialize disk cache in plugin directory
        cache_dir = os.path.join(config.extension_uri, "thumbnail_cache")
        self.image_cache = DiskCache(cache_dir)
        
        # Cleanup counter - run cleanup every N cache writes
        self._write_count = 0
        self._cleanup_interval = 200  # Increased from 100 - less frequent cleanup

    def get_cache(self, key: str):
        with self.cache_lock:
            return self.cache.get(key, ([], 0))

    def set_cache(self, key: str, value: tuple[list, float]):
        with self.cache_lock:
            self.cache[key] = value

    def rm_cache(self, key: str):
        with self.cache_lock:
            if key in self.cache:
                del self.cache[key]

    def get_image_cache(self, key: str) -> bytes | None:
        return self.image_cache.get(key)

    def set_image_cache(self, key: str, data: bytes):
        self.image_cache.set(key, data)
        
        # Periodic cleanup
        self._write_count += 1
        if self._write_count >= self._cleanup_interval:
            self._write_count = 0
            # Run cleanup in background
            import threading
            threading.Thread(target=self.image_cache.cleanup, daemon=True).start()


cache_helper = CacheHelper()


from concurrent.futures import ThreadPoolExecutor, as_completed


# Global thread pool for file operations
_executor = ThreadPoolExecutor(max_workers=4)


# ============================================================================
# File count cache - persistent storage for folder file counts
# ============================================================================

_file_count_cache: dict[str, tuple[int, float]] = {}  # path -> (count, mtime)
_file_count_lock = Lock()


def get_folder_file_count(folder_path: str) -> int:
    """Get cached file count for a folder, returns -1 if not cached"""
    with _file_count_lock:
        if folder_path in _file_count_cache:
            count, cached_mtime = _file_count_cache[folder_path]
            try:
                current_mtime = os.path.getmtime(folder_path)
                if current_mtime == cached_mtime:
                    return count
            except OSError:
                pass
        return -1


def set_folder_file_count(folder_path: str, count: int):
    """Cache file count for a folder"""
    with _file_count_lock:
        try:
            mtime = os.path.getmtime(folder_path)
            _file_count_cache[folder_path] = (count, mtime)
        except OSError:
            pass


def scan_directory_items(directory: str):
    result, m_time = cache_helper.get_cache(directory)
    
    try:
        folder_m_time = os.path.getmtime(directory)
    except OSError:
        return []

    if folder_m_time == m_time:
        return result

    result = []
    file_count = 0

    def get_file_info(entry: os.DirEntry[str]):
        try:
            filepath = entry.path
            is_dir = entry.is_dir()

            if not is_dir and not assert_file_type(filepath, ["image", "video", "audio"]):
                return None

            stat = entry.stat()
            return {
                "name": entry.name,
                "type": "folder" if is_dir else get_file_content_type(filepath),
                "size": 0 if is_dir else stat.st_size,
                "createdAt": round(stat.st_ctime_ns / 1000000),
                "updatedAt": round(stat.st_mtime_ns / 1000000),
            }
        except OSError:
            return None

    try:
        with os.scandir(directory) as it:
            entries = list(it)
        
        # Use thread pool for parallel file info gathering
        futures = {_executor.submit(get_file_info, entry): entry for entry in entries}
        for future in as_completed(futures):
            try:
                file_info = future.result(timeout=5)
                if file_info is not None:
                    result.append(file_info)
                    if file_info["type"] != "folder":
                        file_count += 1
            except Exception:
                pass
    except OSError:
        return []

    cache_helper.set_cache(directory, (result, folder_m_time))
    set_folder_file_count(directory, file_count)
    return result


def scan_workflows_directory(directory: str):
    """Scan directory for workflow files (.json) and folders with caching"""
    # Check cache first
    result, m_time = cache_helper.get_cache(directory)
    
    try:
        folder_m_time = os.path.getmtime(directory)
    except OSError:
        return []

    if folder_m_time == m_time:
        return result

    result = []
    
    try:
        with os.scandir(directory) as it:
            for entry in it:
                try:
                    stat = entry.stat()
                    is_dir = entry.is_dir()
                    
                    # Only include folders and .json files
                    if is_dir:
                        result.append({
                            "name": entry.name,
                            "type": "folder",
                            "size": 0,
                            "createdAt": round(stat.st_ctime_ns / 1000000),
                            "updatedAt": round(stat.st_mtime_ns / 1000000),
                        })
                    elif entry.name.lower().endswith('.json'):
                        result.append({
                            "name": entry.name,
                            "type": "workflow",
                            "size": stat.st_size,
                            "createdAt": round(stat.st_ctime_ns / 1000000),
                            "updatedAt": round(stat.st_mtime_ns / 1000000),
                        })
                except OSError:
                    pass
    except OSError:
        return []
    
    cache_helper.set_cache(directory, (result, folder_m_time))
    return result


def scan_prompts_directory(directory: str):
    """Scan directory for prompt files (.txt) and folders with caching"""
    # Check cache first
    result, m_time = cache_helper.get_cache(directory)
    
    try:
        folder_m_time = os.path.getmtime(directory)
    except OSError:
        return []

    if folder_m_time == m_time:
        return result

    result = []
    
    try:
        with os.scandir(directory) as it:
            for entry in it:
                try:
                    stat = entry.stat()
                    is_dir = entry.is_dir()
                    
                    # Only include folders and .txt files
                    if is_dir:
                        result.append({
                            "name": entry.name,
                            "type": "folder",
                            "size": 0,
                            "createdAt": round(stat.st_ctime_ns / 1000000),
                            "updatedAt": round(stat.st_mtime_ns / 1000000),
                        })
                    elif entry.name.lower().endswith('.txt'):
                        result.append({
                            "name": entry.name,
                            "type": "prompt",
                            "size": stat.st_size,
                            "createdAt": round(stat.st_ctime_ns / 1000000),
                            "updatedAt": round(stat.st_mtime_ns / 1000000),
                        })
                except OSError:
                    pass
    except OSError:
        return []
    
    cache_helper.set_cache(directory, (result, folder_m_time))
    return result


def get_real_path_for_type(filepath: str):
    """Get real filesystem path based on virtual path type"""
    if filepath.startswith("/output"):
        return utils.get_real_output_filepath(filepath)
    elif filepath.startswith("/workflows"):
        return utils.get_real_workflows_filepath(filepath)
    elif filepath.startswith("/prompts"):
        return utils.get_real_prompts_filepath(filepath)
    return filepath


async def create_file_or_folder_generic(pathname: str, reader, folder_type: str):
    """Create file or folder in any folder type"""
    real_pathname = get_real_path_for_type(pathname)
    
    while True:
        part = await reader.next()
        if part is None:
            break

        name = part.name

        if name == "files":
            filename = part.filename
            filepath = f"{real_pathname}/{filename}"
            while True:
                if not os.path.exists(filepath):
                    break
                filepath_0 = os.path.splitext(filepath)[0]
                filepath_1 = os.path.splitext(filepath)[1]
                filepath = f"{filepath_0}(1){filepath_1}"

            utils.print_debug(f"Creating file: {filepath}")
            with open(filepath, "wb") as f:
                while True:
                    chunk = await part.read_chunk()
                    if not chunk:
                        break
                    f.write(chunk)

        if name == "folders":
            filename = await part.text()
            filepath = f"{real_pathname}/{filename}"
            if os.path.exists(filepath):
                raise RuntimeError(f"filename '{filename}' was existed.")
            utils.print_debug(f"Create folder: {filepath}")
            os.mkdir(filepath)
    
    # Invalidate cache for the directory
    cache_helper.rm_cache(real_pathname)


def rename_file_generic(pathname: str, filename: str, folder_type: str):
    """Rename file in any folder type"""
    real_pathname = get_real_path_for_type(pathname)
    real_filename = get_real_path_for_type(filename)
    shutil.move(real_pathname, real_filename)
    
    # Invalidate cache
    parent_dir = os.path.dirname(real_pathname)
    cache_helper.rm_cache(parent_dir)


def recursive_delete_files_generic(file_list: list[str]):
    """Delete files from any folder type"""
    dirs_to_invalidate = set()
    
    for file_path in file_list:
        real_path = get_real_path_for_type(file_path)
        dirs_to_invalidate.add(os.path.dirname(real_path))

        if os.path.isfile(real_path):
            os.remove(real_path)
        elif os.path.islink(real_path):
            os.unlink(real_path)
        elif os.path.isdir(real_path):
            shutil.rmtree(real_path)
    
    # Invalidate cache for affected directories
    for dir_path in dirs_to_invalidate:
        cache_helper.rm_cache(dir_path)


def move_files_generic(file_list: list[str], target_folder: str):
    """Move files within the same root folder type"""
    if not file_list:
        return
    
    # Get root type of first file and target
    first_root = utils.get_root_type(file_list[0])
    target_root = utils.get_root_type(target_folder)
    
    # Validate all files are from the same root type
    for file_path in file_list:
        file_root = utils.get_root_type(file_path)
        if file_root != first_root:
            raise RuntimeError("Cannot move files from different root folders")
    
    # Validate target is same root type
    if first_root != target_root:
        raise RuntimeError(f"Cannot move {first_root} files to {target_root} folder")
    
    dirs_to_invalidate = set()
    
    real_target = get_real_path_for_type(target_folder)
    
    if not os.path.isdir(real_target):
        raise RuntimeError(f"Target folder does not exist: {target_folder}")
    
    dirs_to_invalidate.add(real_target)
    
    for file_path in file_list:
        real_path = get_real_path_for_type(file_path)
        
        if not os.path.exists(real_path):
            continue
        
        # Add source directory to invalidate
        dirs_to_invalidate.add(os.path.dirname(real_path))
        
        # Get filename and create destination path
        filename = os.path.basename(real_path)
        dest_path = os.path.join(real_target, filename)
        
        # Handle name conflicts
        if os.path.exists(dest_path):
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(dest_path):
                dest_path = os.path.join(real_target, f"{base}({counter}){ext}")
                counter += 1
        
        shutil.move(real_path, dest_path)
        utils.print_debug(f"Moved {real_path} to {dest_path}")
    
    # Invalidate cache for affected directories
    for dir_path in dirs_to_invalidate:
        cache_helper.rm_cache(dir_path)


import re

def duplicate_workflow(file_path: str) -> str:
    """Duplicate a workflow file with incremented number"""
    real_path = get_real_path_for_type(file_path)
    
    if not os.path.isfile(real_path):
        raise RuntimeError(f"File not found: {file_path}")
    
    directory = os.path.dirname(real_path)
    filename = os.path.basename(real_path)
    name, ext = os.path.splitext(filename)
    
    # Check if name ends with a number
    match = re.match(r'^(.+?)(\d+)$', name)
    if match:
        base_name = match.group(1)
        number = int(match.group(2)) + 1
    else:
        base_name = name
        number = 1
    
    # Find next available number
    new_name = f"{base_name}{number}{ext}"
    new_path = os.path.join(directory, new_name)
    
    while os.path.exists(new_path):
        number += 1
        new_name = f"{base_name}{number}{ext}"
        new_path = os.path.join(directory, new_name)
    
    # Copy the file
    shutil.copy2(real_path, new_path)
    
    # Invalidate cache
    cache_helper.rm_cache(directory)
    
    # Return virtual path
    folder_virtual = os.path.dirname(file_path)
    return f"{folder_virtual}/{new_name}"


def get_folder_counts(folder_path: str) -> dict:
    """
    Get file counts and subfolder info for a folder and its subfolders.
    Returns dict with:
      - 'counts': folder paths as keys and file counts as values
      - 'hasSubfolders': folder paths as keys and boolean as values
    """
    real_path = utils.get_real_output_filepath(folder_path)
    counts = {}
    has_subfolders = {}
    
    try:
        # First scan the folder to get its contents
        items = scan_directory_items(real_path)
        
        # Count files in this folder
        file_count = sum(1 for item in items if item["type"] != "folder")
        folder_items = [item for item in items if item["type"] == "folder"]
        
        counts[folder_path] = file_count
        has_subfolders[folder_path] = len(folder_items) > 0
        
        # Get counts for subfolders
        for item in folder_items:
            subfolder_path = f"{folder_path}/{item['name']}"
            subfolder_real = os.path.join(real_path, item["name"])
            
            # Check cached count first
            cached_count = get_folder_file_count(subfolder_real)
            if cached_count >= 0:
                counts[subfolder_path] = cached_count
            else:
                # Scan subfolder
                sub_items = scan_directory_items(subfolder_real)
                sub_count = sum(1 for i in sub_items if i["type"] != "folder")
                counts[subfolder_path] = sub_count
                set_folder_file_count(subfolder_real, sub_count)
                
                # Check if subfolder has subfolders
                sub_folder_items = [i for i in sub_items if i["type"] == "folder"]
                has_subfolders[subfolder_path] = len(sub_folder_items) > 0
    
    except Exception as e:
        utils.print_error(f"Error getting folder counts: {e}")
    
    return {"counts": counts, "hasSubfolders": has_subfolders}


async def create_file_or_folder(pathname: str, reader):
    real_pathname = utils.get_real_output_filepath(pathname)

    while True:
        part = await reader.next()
        if part is None:
            break

        name = part.name

        if name == "files":
            filename = part.filename
            filepath = f"{real_pathname}/{filename}"
            while True:
                if not os.path.exists(filepath):
                    break
                filepath_0 = os.path.splitext(filepath)[0]
                filepath_1 = os.path.splitext(filepath)[1]
                filepath = f"{filepath_0}(1){filepath_1}"

            utils.print_debug(f"Creating file: {filepath}")
            with open(filepath, "wb") as f:
                while True:
                    chunk = await part.read_chunk()
                    if not chunk:
                        break
                    f.write(chunk)

        if name == "folders":
            filename = await part.text()
            filepath = f"{real_pathname}/{filename}"
            if os.path.exists(filepath):
                raise RuntimeError(f"filename '{filename}' was existed.")
            utils.print_debug(f"Create folder: {filepath}")
            os.mkdir(filepath)
    
    # Invalidate cache for the directory
    cache_helper.rm_cache(real_pathname)


def rename_file(pathname: str, filename: str):
    real_pathname = utils.get_real_output_filepath(pathname)
    real_filename = utils.get_real_output_filepath(filename)
    shutil.move(real_pathname, real_filename)
    
    # Invalidate cache
    parent_dir = os.path.dirname(real_pathname)
    cache_helper.rm_cache(parent_dir)


def recursive_delete_files(file_list: list[str]):
    dirs_to_invalidate = set()
    
    for file_path in file_list:
        real_path = utils.get_real_output_filepath(file_path)
        dirs_to_invalidate.add(os.path.dirname(real_path))

        if os.path.isfile(real_path):
            os.remove(real_path)
        elif os.path.islink(real_path):
            os.unlink(real_path)
        elif os.path.isdir(real_path):
            shutil.rmtree(real_path)
    
    # Invalidate cache for affected directories
    for dir_path in dirs_to_invalidate:
        cache_helper.rm_cache(dir_path)


def move_files(file_list: list[str], target_folder: str):
    """Move files/folders to target folder"""
    dirs_to_invalidate = set()
    
    real_target = utils.get_real_output_filepath(target_folder)
    
    if not os.path.isdir(real_target):
        raise RuntimeError(f"Target folder does not exist: {target_folder}")
    
    dirs_to_invalidate.add(real_target)
    
    for file_path in file_list:
        real_path = utils.get_real_output_filepath(file_path)
        
        if not os.path.exists(real_path):
            continue
        
        # Add source directory to invalidate
        dirs_to_invalidate.add(os.path.dirname(real_path))
        
        # Get filename and create destination path
        filename = os.path.basename(real_path)
        dest_path = os.path.join(real_target, filename)
        
        # Handle name conflicts
        if os.path.exists(dest_path):
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(dest_path):
                dest_path = os.path.join(real_target, f"{base}({counter}){ext}")
                counter += 1
        
        shutil.move(real_path, dest_path)
        utils.print_debug(f"Moved {real_path} to {dest_path}")
    
    # Invalidate cache for affected directories
    for dir_path in dirs_to_invalidate:
        cache_helper.rm_cache(dir_path)


from PIL import Image
from io import BytesIO



# ============================================================================
# Video merge (ffmpeg concat)
# ============================================================================

def _escape_concat_path(path: str) -> str:
    # ffmpeg concat demuxer uses single-quoted paths: file '...'
    return path.replace("'", "'\\''")

def merge_videos(file_list: list[str], output_name: str) -> str:
    """
    Merge (concatenate) selected video files sequentially into a new MP4 in the same folder.
    Returns the new file fullname (e.g. /output/sub/merged_xxx.mp4).
    Requires ffmpeg in PATH.
    """
    if not file_list or len(file_list) < 2:
        raise RuntimeError("Need at least 2 videos to merge")

    # Validate and map to real paths
    real_paths: list[str] = []
    for file_path in file_list:
        real_path = utils.get_real_output_filepath(file_path)
        if not os.path.isfile(real_path):
            raise RuntimeError(f"File not found: {file_path}")
        if not assert_file_type(real_path, ["video"]):
            raise RuntimeError(f"Not a video file: {file_path}")
        real_paths.append(real_path)

    # Ensure all files are in the same directory (output in same folder)
    out_dir_real = os.path.dirname(real_paths[0])
    for rp in real_paths[1:]:
        if os.path.dirname(rp) != out_dir_real:
            raise RuntimeError("All selected videos must be in the same folder")

    safe_name = os.path.basename(output_name or "").strip()
    if safe_name == "":
        raise RuntimeError("Missing output_name")
    if not safe_name.lower().endswith(".mp4"):
        safe_name += ".mp4"

    out_real = os.path.join(out_dir_real, safe_name)
    if os.path.exists(out_real):
        raise RuntimeError(f"Output already exists: {safe_name}")

    # Create concat list file
    tmp_dir_local = os.path.join(config.extension_uri, "tmp")
    if not os.path.exists(tmp_dir_local):
        os.makedirs(tmp_dir_local)

    import time
    list_path = os.path.join(tmp_dir_local, f"concat_{int(time.time()*1000)}.txt")
    with open(list_path, "w", encoding="utf-8") as f:
        for rp in real_paths:
            f.write(f"file '{_escape_concat_path(rp)}'\n")

    base = [
        _get_ffmpeg_cmd(),
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        list_path,
    ]

    # Fast path: stream copy (works only if codecs/params match)
    cmd_copy = base + ["-c", "copy", out_real]
    result = subprocess.run(cmd_copy, capture_output=True, text=True)

    if result.returncode != 0:
        # Fallback: re-encode for maximum compatibility
        cmd_reencode = base + [
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            out_real,
        ]
        result2 = subprocess.run(cmd_reencode, capture_output=True, text=True)
        if result2.returncode != 0:
            try:
                os.remove(list_path)
            except OSError:
                pass
            raise RuntimeError(
                "ffmpeg merge failed: "
                + (result.stderr.strip() or result2.stderr.strip() or "unknown error")
            )

    try:
        os.remove(list_path)
    except OSError:
        pass

    # Invalidate directory cache so new file shows up immediately
    cache_helper.rm_cache(out_dir_real)

    # Build fullname for UI (/output/...)
    # file_list entries are already fullnames, keep their folder prefix
    folder_fullname = os.path.dirname(file_list[0].rstrip("/"))
    if folder_fullname == "":
        folder_fullname = "/output"
    new_fullname = f"{folder_fullname}/{safe_name}".replace("//", "/")
    return new_fullname


def extract_video_frame(video_path: str, frame_type: str = "first", timestamp: float = 0) -> str:
    """
    Extract first, last, or current frame from a video file.
    Returns the output filename (e.g. /output/sub/video_first_frame.png).
    Requires ffmpeg in PATH.
    
    Args:
        video_path: Virtual path to video (e.g., /output/folder/video.mp4)
        frame_type: "first", "last", or "current"
        timestamp: Time in seconds for "current" frame type
    """
    real_path = utils.get_real_output_filepath(video_path)
    
    if not os.path.isfile(real_path):
        raise RuntimeError(f"File not found: {video_path}")
    
    if not assert_file_type(real_path, ["video"]):
        raise RuntimeError(f"Not a video file: {video_path}")
    
    # Get video info to find last frame
    out_dir = os.path.dirname(real_path)
    base_name = os.path.splitext(os.path.basename(real_path))[0]
    
    if frame_type == "current":
        suffix = f"frame_{int(timestamp*1000)}ms"
    elif frame_type == "first":
        suffix = "first_frame"
    else:
        suffix = "last_frame"
    
    output_name = f"{base_name}_{suffix}.png"
    output_path = os.path.join(out_dir, output_name)
    
    # Handle name conflicts
    counter = 1
    while os.path.exists(output_path):
        output_name = f"{base_name}_{suffix}_{counter}.png"
        output_path = os.path.join(out_dir, output_name)
        counter += 1
    
    if frame_type == "first":
        # Extract first frame
        cmd = [
            _get_ffmpeg_cmd(),
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-i", real_path,
            "-vframes", "1",
            "-q:v", "1",
            output_path
        ]
    elif frame_type == "current":
        # Extract frame at specific timestamp
        cmd = [
            _get_ffmpeg_cmd(),
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-ss", str(timestamp),
            "-i", real_path,
            "-vframes", "1",
            "-q:v", "1",
            output_path
        ]
    else:
        # Extract last frame - need to get video duration first
        probe_cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-count_packets",
            "-show_entries", "stream=nb_read_packets",
            "-of", "csv=p=0",
            real_path
        ]
        
        try:
            result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout.strip():
                # Use sseof to seek from end
                cmd = [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel", "error",
                    "-y",
                    "-sseof", "-0.1",  # Seek to 0.1 seconds before end
                    "-i", real_path,
                    "-update", "1",
                    "-q:v", "1",
                    output_path
                ]
            else:
                # Fallback: seek to a very late timestamp
                cmd = [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel", "error", 
                    "-y",
                    "-sseof", "-0.1",
                    "-i", real_path,
                    "-update", "1",
                    "-q:v", "1",
                    output_path
                ]
        except Exception:
            # Fallback
            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel", "error",
                "-y", 
                "-sseof", "-0.1",
                "-i", real_path,
                "-update", "1",
                "-q:v", "1",
                output_path
            ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    
    if result.returncode != 0 or not os.path.exists(output_path):
        raise RuntimeError(f"ffmpeg extract failed: {result.stderr.strip() or 'unknown error'}")
    
    # Invalidate directory cache
    cache_helper.rm_cache(out_dir)
    
    # Build virtual path for UI
    folder_fullname = os.path.dirname(video_path.rstrip("/"))
    if folder_fullname == "":
        folder_fullname = "/output"
    new_fullname = f"{folder_fullname}/{output_name}".replace("//", "/")
    return new_fullname

def get_cache_key(filename: str, max_size: int) -> str:
    """Generate cache key based on filename, mtime, and size"""
    try:
        mtime = os.path.getmtime(filename)
        key_string = f"{filename}:{mtime}:{max_size}"
        return hashlib.md5(key_string.encode()).hexdigest()
    except OSError:
        return hashlib.md5(f"{filename}:{max_size}".encode()).hexdigest()


def get_video_thumbnail(filename: str, max_size: int = 128) -> bytes | None:
    """
    Generate a thumbnail from a video file using ffmpeg.
    Extracts a frame from 1 second into the video.
    """
    try:
        # Check if ffmpeg is available
        result = subprocess.run(
            [_get_ffmpeg_cmd(), '-version'],
            capture_output=True,
            timeout=5
        )
        if result.returncode != 0:
            return None
    except (subprocess.SubprocessError, FileNotFoundError):
        return None
    
    try:
        # Extract frame at 1 second (or start if video is shorter)
        cmd = [
            _get_ffmpeg_cmd(),
            '-i', filename,
            '-ss', '00:00:01',  # Seek to 1 second
            '-vframes', '1',    # Extract 1 frame
            '-vf', f'scale={max_size}:{max_size}:force_original_aspect_ratio=decrease',
            '-f', 'image2pipe',
            '-vcodec', 'png',
            '-y',
            'pipe:1'
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=30
        )
        
        if result.returncode != 0:
            # Try extracting first frame instead
            cmd[3] = '00:00:00'
            result = subprocess.run(cmd, capture_output=True, timeout=30)
        
        if result.returncode == 0 and result.stdout:
            # Convert PNG to WEBP
            with Image.open(BytesIO(result.stdout)) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                img_byte_arr = BytesIO()
                img.save(img_byte_arr, format="WEBP", quality=75)
                return img_byte_arr.getvalue()
    
    except Exception as e:
        utils.print_error(f"Error generating video thumbnail for {filename}: {e}")
    
    return None


def get_image_data(filename: str, max_size: int = 128):
    """
    Generate a thumbnail of the image/video with the specified max_size.
    Uses disk cache with file modification time for invalidation.
    """
    # Clamp max_size to valid range
    max_size = max(64, min(max_size, 1024))
    
    # Check cache first
    cache_key = get_cache_key(filename, max_size)
    cached_data = cache_helper.get_image_cache(cache_key)
    if cached_data is not None:
        return BytesIO(cached_data)
    
    # Check if it's a video file
    if assert_file_type(filename, ["video"]):
        video_thumb = get_video_thumbnail(filename, max_size)
        if video_thumb:
            cache_helper.set_image_cache(cache_key, video_thumb)
            return BytesIO(video_thumb)
        else:
            # Return a placeholder for videos without ffmpeg
            raise Exception("Video thumbnail generation requires ffmpeg")
    
    try:
        with Image.open(filename) as img:
            # Convert to RGB if necessary (handles RGBA, P mode, etc.)
            if img.mode in ('RGBA', 'P', 'LA'):
                # Create white background for transparent images
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            old_width, old_height = img.size
            scale = min(max_size / old_width, max_size / old_height)

            if scale >= 1:
                new_width, new_height = old_width, old_height
            else:
                new_width = int(old_width * scale)
                new_height = int(old_height * scale)

            # Use faster resampling for small thumbnails
            if max_size <= 128:
                resample = Image.Resampling.BILINEAR
                quality = 60  # Lower quality for tiny thumbs - faster encoding
            elif max_size <= 256:
                resample = Image.Resampling.BILINEAR
                quality = 70
            elif max_size <= 512:
                resample = Image.Resampling.BILINEAR
                quality = 75
            else:
                resample = Image.Resampling.LANCZOS
                quality = 85
            
            img = img.resize((new_width, new_height), resample)

            img_byte_arr = BytesIO()
            img.save(img_byte_arr, format="WEBP", quality=quality, method=4)
            
            # Cache the result to disk
            img_data = img_byte_arr.getvalue()
            cache_helper.set_image_cache(cache_key, img_data)
            
            img_byte_arr.seek(0)
            return img_byte_arr
            
    except Exception as e:
        utils.print_error(f"Error processing image {filename}: {e}")
        raise


import zipfile
import datetime


tmp_dir = os.path.join(config.extension_uri, "tmp")


async def package_file(root_dir: str, file_list: list[str]):
    zip_filename = f"{datetime.datetime.now().strftime('%Y%m%dT%H%M%SZ')}.zip"

    tmp_dir_local = os.path.join(config.extension_uri, "tmp")
    if not os.path.exists(tmp_dir_local):
        os.makedirs(tmp_dir_local)

    zip_temp_file = os.path.join(tmp_dir, zip_filename)
    real_root_dir = utils.get_real_output_filepath(root_dir)

    utils.print_debug(f"Creating zip file: {zip_temp_file}")
    utils.print_debug(f"Root directory: {root_dir}")
    utils.print_debug(f"Real root directory: {real_root_dir}")

    with zipfile.ZipFile(zip_temp_file, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in file_list:
            real_path = utils.get_real_output_filepath(file_path)
            filename = os.path.relpath(file_path, root_dir)

            if os.path.isfile(real_path):
                utils.print_debug(f"Adding file: {filename}")
                zip_file.write(real_path, filename)
            elif os.path.isdir(real_path):
                utils.print_debug(f"Checking sub directory: {filename}")
                for root, _, files in os.walk(real_path):
                    utils.print_debug(f"Find {root} files: {files}")
                    for file in files:
                        sub_real_path = os.path.join(root, file)
                        sub_dir = os.path.relpath(
                            root, os.path.join(real_root_dir, filename)
                        )
                        sub_filename = os.path.join(filename, sub_dir, file)
                        utils.print_debug(f"Adding file: {sub_filename}")
                        zip_file.write(sub_real_path, sub_filename)
            else:
                utils.print_error(f"File not found: {real_path}")
    return zip_filename


async def get_temp_file_path(filename: str):
    return os.path.join(config.extension_uri, "tmp", filename)


import asyncio


class TemporaryFile:
    def __init__(self, file_path):
        self.file_path = file_path
        self.file = None
        self.loop = asyncio.get_event_loop()

    async def __aenter__(self):
        def open_file():
            self.file = open(self.file_path, "rb")
            return self.file

        self.file = await self.loop.run_in_executor(None, open_file)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.file:
            self.file.close()
        os.remove(self.file_path)

    async def read(self, size=-1):
        def sync_read():
            return self.file.read(size)

        return await self.loop.run_in_executor(None, sync_read)


def open_tmp_file(filepath: str):
    return TemporaryFile(filepath)


# ============================================================================
# Cache status tracking and cache-all functionality
# ============================================================================

_cache_status = {
    "is_running": False,
    "phase": "",  # "counting" or "caching"
    "total": 0,
    "processed": 0,
    "current_file": "",
    "errors": 0,
}
_cache_status_lock = Lock()


def get_cache_status():
    """Get current caching status"""
    with _cache_status_lock:
        status = dict(_cache_status)
    
    # Add cache info
    status["cache_info"] = cache_helper.image_cache.get_cache_info()
    return status


def set_cache_max_size(size_gb: float):
    """Set maximum cache size"""
    cache_helper.image_cache.set_max_size(size_gb)
    return cache_helper.image_cache.get_cache_info()


def clear_cache():
    """Clear all cached thumbnails"""
    cache_helper.image_cache.clear()
    return {"success": True}


# ============================================================================
# Parallel caching with pause/resume support
# ============================================================================

_cache_status = {
    "is_running": False,
    "is_paused": False,
    "phase": "",  # "scanning", "caching", "done"
    "total": 0,
    "processed": 0,
    "skipped": 0,  # Already cached
    "current_file": "",
    "errors": 0,
    "folder_counts": {},
    "cached_folders": [],
    "folders_total": 0,
    "folders_done": 0,
}
_cache_status_lock = Lock()


def get_cache_status():
    """Get current caching status"""
    with _cache_status_lock:
        status = dict(_cache_status)
    
    # Add cache info
    status["cache_info"] = cache_helper.image_cache.get_cache_info()
    return status


def pause_caching():
    """Pause the caching process"""
    global _cache_status
    with _cache_status_lock:
        if _cache_status["is_running"]:
            _cache_status["is_paused"] = True
    return get_cache_status()


def resume_caching():
    """Resume the caching process"""
    global _cache_status
    with _cache_status_lock:
        _cache_status["is_paused"] = False
    return get_cache_status()


def stop_caching():
    """Stop the caching process"""
    global _cache_status
    with _cache_status_lock:
        _cache_status["is_running"] = False
        _cache_status["is_paused"] = False
    return get_cache_status()


def _process_single_file(args):
    """Process a single file for caching - used by thread pool"""
    filepath, max_size = args
    try:
        cache_key = get_cache_key(filepath, max_size)
        if cache_helper.get_image_cache(cache_key) is not None:
            return ("skipped", filepath)
        
        get_image_data(filepath, max_size)
        return ("success", filepath)
    except Exception as e:
        return ("error", filepath, str(e))


def cache_all_images(max_size: int = 128, num_workers: int = 1, priority_folder: str = None):
    """
    Cache all images and videos in output directory.
    
    Phases:
    1. Quick scan - count files in each folder (fast, updates UI immediately)
    2. Caching - process files with low priority (yields to user operations)
    """
    global _cache_status
    
    import time
    
    with _cache_status_lock:
        if _cache_status["is_running"]:
            return {"error": "Caching already in progress"}
        _cache_status["is_running"] = True
        _cache_status["is_paused"] = False
        _cache_status["phase"] = "scanning"
        _cache_status["total"] = 0
        _cache_status["processed"] = 0
        _cache_status["skipped"] = 0
        _cache_status["errors"] = 0
        _cache_status["current_file"] = ""
        _cache_status["folder_counts"] = {}
        _cache_status["cached_folders"] = []  # Folders where caching is complete
        _cache_status["folders_total"] = 0
        _cache_status["folders_done"] = 0
    
    try:
        output_dir = config.output_uri
        
        # =====================================================================
        # Phase 1: Quick scan - just count files, no heavy processing
        # =====================================================================
        utils.print_debug("Phase 1: Quick scanning folders...")
        
        folder_files_map = {}  # folder_path -> list of file paths
        folder_counts = {}
        
        for root, dirs, files in os.walk(output_dir):
            with _cache_status_lock:
                if not _cache_status["is_running"]:
                    return {"stopped": True}
                _cache_status["current_file"] = f"Scanning: {os.path.basename(root)}"
            
            media_files = []
            for file in files:
                filepath = os.path.join(root, file)
                if assert_file_type(filepath, ["image", "video"]):
                    media_files.append(filepath)
            
            if media_files:
                folder_files_map[root] = media_files
                folder_counts[root] = len(media_files)
                set_folder_file_count(root, len(media_files))
                
                # Update status immediately so UI can show counts
                with _cache_status_lock:
                    _cache_status["folder_counts"][root] = len(media_files)
        
        # Calculate totals
        total_files = sum(len(files) for files in folder_files_map.values())
        total_folders = len(folder_files_map)
        
        with _cache_status_lock:
            _cache_status["total"] = total_files
            _cache_status["folders_total"] = total_folders
            _cache_status["phase"] = "caching"
            _cache_status["current_file"] = ""
        
        utils.print_debug(f"Phase 1 complete: {total_files} files in {total_folders} folders")
        
        # =====================================================================
        # Phase 2: Cache files folder by folder with low priority
        # =====================================================================
        utils.print_debug(f"Phase 2: Caching with {num_workers} workers...")
        
        # Sort folders - priority folder first if specified
        folder_list = list(folder_files_map.keys())
        if priority_folder:
            priority_real = utils.get_real_output_filepath(priority_folder)
            # Move priority folder and its subfolders to the front
            priority_folders = [f for f in folder_list if f == priority_real or f.startswith(priority_real + os.sep)]
            other_folders = [f for f in folder_list if f not in priority_folders]
            folder_list = priority_folders + other_folders
        
        processed = 0
        skipped = 0
        errors = 0
        folders_done = 0
        
        for folder_path in folder_list:
            with _cache_status_lock:
                if not _cache_status["is_running"]:
                    break
            
            # Wait while paused
            while True:
                with _cache_status_lock:
                    if not _cache_status["is_paused"]:
                        break
                    if not _cache_status["is_running"]:
                        break
                time.sleep(0.5)
            
            files_in_folder = folder_files_map[folder_path]
            
            # Process files in this folder with limited parallelism
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                futures = []
                
                for filepath in files_in_folder:
                    with _cache_status_lock:
                        if not _cache_status["is_running"]:
                            break
                    
                    futures.append(executor.submit(_process_single_file, (filepath, max_size)))
                
                for future in as_completed(futures):
                    result = future.result()
                    processed += 1
                    
                    if result[0] == "skipped":
                        skipped += 1
                    elif result[0] == "error":
                        errors += 1
                    
                    with _cache_status_lock:
                        _cache_status["processed"] = processed
                        _cache_status["skipped"] = skipped
                        _cache_status["errors"] = errors
                        _cache_status["current_file"] = os.path.basename(result[1])
            
            # Yield between folders to keep server responsive for user requests
            time.sleep(0.05)
            
            # Mark folder as done
            folders_done += 1
            with _cache_status_lock:
                _cache_status["folders_done"] = folders_done
                _cache_status["cached_folders"].append(folder_path)
        
        with _cache_status_lock:
            _cache_status["processed"] = total_files
            _cache_status["current_file"] = ""
            _cache_status["phase"] = "done"
        
        utils.print_debug(f"Caching complete: {processed} files, {skipped} skipped, {errors} errors")
        
    finally:
        with _cache_status_lock:
            _cache_status["is_running"] = False
            _cache_status["is_paused"] = False
    
    return {"success": True, "total": total_files, "skipped": skipped, "errors": errors}


def regenerate_thumbnail(file_path: str):
    """
    Regenerate thumbnail for a file by removing it from cache
    """
    real_path = utils.get_real_output_filepath(file_path)

    if not os.path.exists(real_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # Get cache keys for different sizes and remove them
    for max_size in [128, 256, 512, 1024]:
        cache_key = get_cache_key(real_path, max_size)
        cache_path = cache_helper.image_cache._get_cache_path(cache_key)
        if os.path.exists(cache_path):
            try:
                os.remove(cache_path)
            except OSError:
                pass

    return True


def recache_folder(folder_path: str):
    """
    Force recache all files in a folder (regenerate all thumbnails)
    Returns count of files recached
    """
    real_path = utils.get_real_output_filepath(folder_path)

    if not os.path.exists(real_path):
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    if not os.path.isdir(real_path):
        raise ValueError(f"Not a folder: {folder_path}")

    recached_count = 0

    # Scan all files in folder
    try:
        with os.scandir(real_path) as it:
            for entry in it:
                if entry.is_file():
                    filepath = entry.path
                    if assert_file_type(filepath, ["image", "video"]):
                        # Remove from cache
                        for max_size in [128, 256, 512, 1024]:
                            cache_key = get_cache_key(filepath, max_size)
                            cache_path = cache_helper.image_cache._get_cache_path(cache_key)
                            if os.path.exists(cache_path):
                                try:
                                    os.remove(cache_path)
                                except OSError:
                                    pass
                        recached_count += 1
    except OSError as e:
        raise RuntimeError(f"Failed to recache folder: {e}")

    # Invalidate folder cache
    cache_helper.rm_cache(real_path)

    utils.print_debug(f"Recached {recached_count} files in {folder_path}")
    return {"count": recached_count}


def precache_all_folders():
    """
    Pre-scan all folders and return folder structure with file counts.
    This allows frontend to cache folder listings in localStorage.
    Returns dictionary of folder paths with their metadata.
    """
    utils.print_debug("Pre-caching all folder listings...")

    output_dir = config.output_uri
    folder_data = {}

    try:
        for root, dirs, files in os.walk(output_dir):
            # Count media files in this folder
            media_files = []
            for file in files:
                filepath = os.path.join(root, file)
                if assert_file_type(filepath, ["image", "video"]):
                    media_files.append(file)

            if media_files or dirs:  # Include folders with subfolders
                # Get relative path for API
                rel_path = os.path.relpath(root, output_dir)
                if rel_path == '.':
                    rel_path = ''

                folder_data['/output/' + rel_path.replace('\\', '/')] = {
                    'file_count': len(media_files),
                    'has_subfolders': len(dirs) > 0,
                    'mtime': os.path.getmtime(root)
                }

        utils.print_debug(f"Pre-cached {len(folder_data)} folders")
        return folder_data

    except Exception as e:
        utils.print_error(f"Failed to precache folders: {e}")
        return {}


def copy_to_input_and_get_node(file_path: str, node_type: str):
    """
    Copy file to ComfyUI input folder and return node data for clipboard
    """
    real_path = utils.get_real_output_filepath(file_path)
    
    if not os.path.exists(real_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Get input directory
    import folder_paths
    input_dir = folder_paths.get_input_directory()
    
    # Copy file to input
    filename = os.path.basename(real_path)
    dest_path = os.path.join(input_dir, filename)
    
    # Handle name conflicts
    if os.path.exists(dest_path):
        base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(dest_path):
            filename = f"{base}({counter}){ext}"
            dest_path = os.path.join(input_dir, filename)
            counter += 1
    
    shutil.copy2(real_path, dest_path)
    
    # Create node data for clipboard
    if node_type == "image":
        node_data = {
            "nodes": [{
                "id": 1,
                "type": "LoadImage",
                "pos": [0, 0],
                "size": [315, 314],
                "flags": {},
                "order": 0,
                "mode": 0,
                "outputs": [
                    {"name": "IMAGE", "type": "IMAGE", "links": [], "slot_index": 0},
                    {"name": "MASK", "type": "MASK", "links": [], "slot_index": 1}
                ],
                "properties": {"Node name for S&R": "LoadImage"},
                "widgets_values": [filename, "image"]
            }],
            "links": [],
            "groups": [],
            "config": {},
            "extra": {},
            "version": 0.4
        }
    else:  # video
        node_data = {
            "nodes": [{
                "id": 1,
                "type": "LoadVideo",
                "pos": [0, 0],
                "size": [240, 130],
                "flags": {},
                "order": 0,
                "mode": 0,
                "outputs": [
                    {"name": "IMAGES", "type": "IMAGE", "links": [], "slot_index": 0},
                    {"name": "AUDIO", "type": "AUDIO", "links": [], "slot_index": 1},
                    {"name": "VIDEO_INFO", "type": "VIDEO_INFO", "links": [], "slot_index": 2}
                ],
                "properties": {"Node name for S&R": "LoadVideo"},
                "widgets_values": [filename, 0, False, 0, 0, "nearest-exact"]
            }],
            "links": [],
            "groups": [],
            "config": {},
            "extra": {},
            "version": 0.4
        }
    
    return {"filename": filename, "nodeData": node_data}


def split_video_at_timestamp(video_path: str, timestamp: float):
    """
    Split video into two parts at the specified timestamp and extract the frame at that point
    """
    real_path = utils.get_real_output_filepath(video_path)
    
    if not os.path.exists(real_path):
        raise FileNotFoundError(f"Video not found: {video_path}")
    
    # Get output directory (same as source file)
    output_dir = os.path.dirname(real_path)
    base_name = os.path.splitext(os.path.basename(real_path))[0]
    ext = os.path.splitext(real_path)[1]
    
    # Generate output filenames
    timestamp_str = f"{int(timestamp * 1000)}ms"
    part1_name = f"{base_name}_part1_{timestamp_str}{ext}"
    part2_name = f"{base_name}_part2_{timestamp_str}{ext}"
    frame_name = f"{base_name}_frame_{timestamp_str}.png"
    
    part1_path = os.path.join(output_dir, part1_name)
    part2_path = os.path.join(output_dir, part2_name)
    frame_path = os.path.join(output_dir, frame_name)
    
    # Handle name conflicts
    def get_unique_path(path):
        if not os.path.exists(path):
            return path
        base, ext_tmp = os.path.splitext(path)
        counter = 1
        while os.path.exists(f"{base}({counter}){ext_tmp}"):
            counter += 1
        return f"{base}({counter}){ext_tmp}"
    
    part1_path = get_unique_path(part1_path)
    part2_path = get_unique_path(part2_path)
    frame_path = get_unique_path(frame_path)
    
    # Update names after conflict resolution
    part1_name = os.path.basename(part1_path)
    part2_name = os.path.basename(part2_path)
    frame_name = os.path.basename(frame_path)
    
    try:
        # Part 1: from start to timestamp (stream copy is fine for part1)
        subprocess.run([
            _get_ffmpeg_cmd(), '-y', '-i', real_path,
            '-t', str(timestamp),
            '-c', 'copy',
            '-avoid_negative_ts', 'make_zero',
            part1_path
        ], check=True, capture_output=True)
        
        # Part 2: from timestamp to end
        # Use -ss after -i for frame-accurate seek, re-encode to fix timestamps
        subprocess.run([
            _get_ffmpeg_cmd(), '-y',
            '-i', real_path,
            '-ss', str(timestamp),
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
            '-c:a', 'aac', '-b:a', '192k',
            '-video_track_timescale', '90000',
            '-fflags', '+genpts',
            part2_path
        ], check=True, capture_output=True)
        
        # Extract frame at timestamp
        subprocess.run([
            _get_ffmpeg_cmd(), '-y',
            '-ss', str(timestamp),
            '-i', real_path,
            '-vframes', '1',
            '-q:v', '2',
            frame_path
        ], check=True, capture_output=True)
        
        return {
            "part1": part1_name,
            "part2": part2_name,
            "frame": frame_name
        }
    except subprocess.CalledProcessError as e:
        raise Exception(f"FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}")


def reverse_video(video_path: str):
    """
    Create a reversed copy of the video
    """
    real_path = utils.get_real_output_filepath(video_path)
    
    if not os.path.exists(real_path):
        raise FileNotFoundError(f"Video not found: {video_path}")
    
    # Get output directory (same as source file)
    output_dir = os.path.dirname(real_path)
    base_name = os.path.splitext(os.path.basename(real_path))[0]
    ext = os.path.splitext(real_path)[1]
    
    # Generate output filename
    output_name = f"{base_name}_reversed{ext}"
    output_path = os.path.join(output_dir, output_name)
    
    # Handle name conflicts
    if os.path.exists(output_path):
        base, ext_tmp = os.path.splitext(output_path)
        counter = 1
        while os.path.exists(f"{base}({counter}){ext_tmp}"):
            counter += 1
        output_path = f"{base}({counter}){ext_tmp}"
        output_name = os.path.basename(output_path)
    
    try:
        # Reverse video and audio
        subprocess.run([
            _get_ffmpeg_cmd(), '-y',
            '-i', real_path,
            '-vf', 'reverse',
            '-af', 'areverse',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
            '-c:a', 'aac', '-b:a', '192k',
            output_path
        ], check=True, capture_output=True)
        
        return {"output": output_name}
    except subprocess.CalledProcessError as e:
        raise Exception(f"FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}")
