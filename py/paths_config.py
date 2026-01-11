"""
Paths configuration and management for ComfyUI Image Browsing
Manages configurable paths for:
- thumbnail_cache: Directory for thumbnail cache
- output: Output directory for generated files
- workflows: Directory for workflow files
- prompts: Directory for prompt files
"""

import os
import json
from . import config, utils


CONFIG_FILE = "paths_config.json"


def get_config_path():
    """Get path to paths config file"""
    return os.path.join(config.extension_uri, CONFIG_FILE)


def get_default_paths():
    """Get default paths based on ComfyUI structure"""
    # Import here to avoid issues when ComfyUI is not fully loaded
    import folder_paths

    comfyui_base = os.path.dirname(folder_paths.get_output_directory())

    return {
        'thumbnail_cache': os.path.join(config.extension_uri, "thumbnail_cache"),
        'output': folder_paths.get_output_directory(),
        'workflows': os.path.join(comfyui_base, "user", "default", "workflows"),
        'prompts': os.path.join(comfyui_base, "user", "default", "prompts")
    }


def load_paths_config():
    """Load paths configuration from file"""
    config_path = get_config_path()
    defaults = get_default_paths()

    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Merge with defaults - use saved value if exists, otherwise use default
                return {
                    'thumbnail_cache': data.get('thumbnail_cache', defaults['thumbnail_cache']),
                    'output': data.get('output', defaults['output']),
                    'workflows': data.get('workflows', defaults['workflows']),
                    'prompts': data.get('prompts', defaults['prompts'])
                }
        except Exception as e:
            utils.print_error(f"Failed to load paths config: {e}")

    return defaults


def save_paths_config(paths: dict):
    """Save paths configuration to file"""
    config_path = get_config_path()

    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(paths, f, indent=2, ensure_ascii=False)

        utils.print_debug(f"Paths config saved: {paths}")
        return True
    except Exception as e:
        utils.print_error(f"Failed to save paths config: {e}")
        return False


def get_path(path_type: str):
    """
    Get configured path by type

    Args:
        path_type: One of 'thumbnail_cache', 'output', 'workflows', 'prompts'

    Returns:
        Configured path or default
    """
    valid_types = ['thumbnail_cache', 'output', 'workflows', 'prompts']
    if path_type not in valid_types:
        raise ValueError(f"Invalid path type. Must be one of: {valid_types}")

    paths = load_paths_config()
    return paths.get(path_type)


def set_path(path_type: str, path: str):
    """
    Set path for given type

    Args:
        path_type: One of 'thumbnail_cache', 'output', 'workflows', 'prompts'
        path: New path value

    Returns:
        True if saved successfully
    """
    valid_types = ['thumbnail_cache', 'output', 'workflows', 'prompts']
    if path_type not in valid_types:
        raise ValueError(f"Invalid path type. Must be one of: {valid_types}")

    # Load current config
    paths = load_paths_config()

    # Update the specified path
    paths[path_type] = path

    # Save updated config
    return save_paths_config(paths)


def validate_path(path: str, should_exist: bool = False, create_if_missing: bool = False):
    """
    Validate a path

    Args:
        path: Path to validate
        should_exist: If True, check that path exists
        create_if_missing: If True, create directory if it doesn't exist

    Returns:
        dict with validation result
    """
    if not path:
        return {
            'valid': False,
            'error': 'Path is empty'
        }

    # Check if path is absolute
    if not os.path.isabs(path):
        return {
            'valid': False,
            'error': 'Path must be absolute'
        }

    # Check if path exists
    exists = os.path.exists(path)

    if should_exist and not exists:
        if create_if_missing:
            try:
                os.makedirs(path, exist_ok=True)
                return {
                    'valid': True,
                    'created': True,
                    'message': f'Directory created: {path}'
                }
            except Exception as e:
                return {
                    'valid': False,
                    'error': f'Failed to create directory: {str(e)}'
                }
        else:
            return {
                'valid': False,
                'error': 'Path does not exist'
            }

    # Check if it's a directory
    if exists and not os.path.isdir(path):
        return {
            'valid': False,
            'error': 'Path exists but is not a directory'
        }

    # Check if writable
    if exists:
        if not os.access(path, os.W_OK):
            return {
                'valid': False,
                'error': 'Directory is not writable'
            }

    return {
        'valid': True,
        'exists': exists
    }


def reset_to_defaults():
    """Reset all paths to default values"""
    defaults = get_default_paths()
    return save_paths_config(defaults)


def get_all_paths():
    """Get all configured paths with validation status"""
    paths = load_paths_config()
    defaults = get_default_paths()

    result = {}
    for path_type in ['thumbnail_cache', 'output', 'workflows', 'prompts']:
        current_path = paths.get(path_type)
        default_path = defaults.get(path_type)

        validation = validate_path(current_path, should_exist=False)

        result[path_type] = {
            'current': current_path,
            'default': default_path,
            'is_default': current_path == default_path,
            'exists': os.path.exists(current_path) if current_path else False,
            'valid': validation.get('valid', False)
        }

    return result
