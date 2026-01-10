"""
FFmpeg configuration and path management
"""

import os
import json
import shutil
from . import config, utils


CONFIG_FILE = "ffmpeg_config.json"


def get_config_path():
    """Get path to FFmpeg config file"""
    return os.path.join(config.extension_uri, CONFIG_FILE)


def load_ffmpeg_config():
    """Load FFmpeg configuration from file"""
    config_path = get_config_path()

    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('ffmpeg_path', 'ffmpeg')
        except Exception as e:
            utils.print_error(f"Failed to load FFmpeg config: {e}")

    return 'ffmpeg'  # Default


def save_ffmpeg_config(ffmpeg_path: str):
    """Save FFmpeg configuration to file"""
    config_path = get_config_path()

    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump({'ffmpeg_path': ffmpeg_path}, f, indent=2)

        # Update in-memory config
        config.ffmpeg_path = ffmpeg_path

        utils.print_debug(f"FFmpeg path saved: {ffmpeg_path}")
        return True
    except Exception as e:
        utils.print_error(f"Failed to save FFmpeg config: {e}")
        return False


def get_ffmpeg_path():
    """Get configured FFmpeg path"""
    if not hasattr(config, 'ffmpeg_path') or not config.ffmpeg_path:
        config.ffmpeg_path = load_ffmpeg_config()

    return config.ffmpeg_path


def set_ffmpeg_path(path: str):
    """Set FFmpeg path and save to config"""
    return save_ffmpeg_config(path)


def detect_ffmpeg():
    """
    Auto-detect FFmpeg installation
    Returns list of possible paths
    """
    candidates = []

    # 1. Check system PATH
    ffmpeg_in_path = shutil.which('ffmpeg')
    if ffmpeg_in_path:
        candidates.append({
            'path': 'ffmpeg',
            'fullpath': ffmpeg_in_path,
            'location': 'System PATH',
            'recommended': True
        })

    # 2. Check common installation paths
    common_paths = []

    if os.name == 'nt':  # Windows
        common_paths = [
            r'C:\ffmpeg\bin\ffmpeg.exe',
            r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
            r'C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe',
            os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'ffmpeg', 'bin', 'ffmpeg.exe'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'ffmpeg', 'bin', 'ffmpeg.exe'),
        ]
    else:  # Linux/Mac
        common_paths = [
            '/usr/bin/ffmpeg',
            '/usr/local/bin/ffmpeg',
            '/opt/ffmpeg/bin/ffmpeg',
            '/snap/bin/ffmpeg',
            os.path.expanduser('~/ffmpeg/bin/ffmpeg'),
        ]

    for path in common_paths:
        if path and os.path.isfile(path):
            candidates.append({
                'path': path,
                'fullpath': path,
                'location': 'Local installation',
                'recommended': False
            })

    # 3. Check relative to ComfyUI
    try:
        comfyui_base = os.path.dirname(os.path.dirname(os.path.dirname(config.extension_uri)))
        relative_paths = [
            os.path.join(comfyui_base, 'ffmpeg', 'bin', 'ffmpeg.exe' if os.name == 'nt' else 'ffmpeg'),
            os.path.join(comfyui_base, 'tools', 'ffmpeg', 'ffmpeg.exe' if os.name == 'nt' else 'ffmpeg'),
        ]

        for path in relative_paths:
            if os.path.isfile(path):
                candidates.append({
                    'path': path,
                    'fullpath': path,
                    'location': 'ComfyUI directory',
                    'recommended': False
                })
    except Exception:
        pass

    return candidates


def test_ffmpeg(ffmpeg_path: str = None):
    """
    Test if FFmpeg is working
    Returns dict with status and version info
    """
    import subprocess

    if not ffmpeg_path:
        ffmpeg_path = get_ffmpeg_path()

    try:
        result = subprocess.run(
            [ffmpeg_path, '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            # Parse version from output
            version_line = result.stdout.split('\n')[0] if result.stdout else ''

            return {
                'available': True,
                'path': ffmpeg_path,
                'version': version_line,
                'error': None
            }
        else:
            return {
                'available': False,
                'path': ffmpeg_path,
                'version': None,
                'error': f"FFmpeg returned error code {result.returncode}"
            }

    except FileNotFoundError:
        return {
            'available': False,
            'path': ffmpeg_path,
            'version': None,
            'error': f"FFmpeg not found at: {ffmpeg_path}"
        }
    except subprocess.TimeoutExpired:
        return {
            'available': False,
            'path': ffmpeg_path,
            'version': None,
            'error': "FFmpeg test timed out"
        }
    except Exception as e:
        return {
            'available': False,
            'path': ffmpeg_path,
            'version': None,
            'error': str(e)
        }


# Initialize config on module load
config.ffmpeg_path = load_ffmpeg_config()
