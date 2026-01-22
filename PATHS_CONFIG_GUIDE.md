# Paths Configuration Guide

This guide explains how to configure custom paths for ComfyUI Image Browsing extension.

## Overview

The extension now supports configurable paths for:

1. **thumbnail_cache** - Directory where thumbnail cache files are stored
2. **output** - Output directory for generated files
3. **workflows** - Directory for workflow files (.json)
4. **prompts** - Directory for prompt files (.txt)

## Configuration File

All path settings are stored in:
```
ComfyUI/custom_nodes/ComfyUI-Image-Browsing/paths_config.json
```

### File Format

```json
{
  "thumbnail_cache": "x:\\ComfyUI_windows_portable_worker\\ComfyUI\\custom_nodes\\ComfyUI-Image-Browsing\\thumbnail_cache",
  "output": "x:\\ComfyUI_windows_portable_worker\\ComfyUI\\output",
  "workflows": "x:\\ComfyUI_windows_portable_worker\\ComfyUI\\user\\default\\workflows",
  "prompts": "x:\\ComfyUI_windows_portable_worker\\ComfyUI\\user\\default\\prompts"
}
```

## Default Values

If not configured, the extension uses these defaults:

| Path Type | Default Location |
|-----------|------------------|
| `thumbnail_cache` | `{extension_dir}/thumbnail_cache` |
| `output` | ComfyUI's default output directory |
| `workflows` | `{comfyui_base}/user/default/workflows` |
| `prompts` | `{comfyui_base}/user/default/prompts` |

## API Endpoints

### Get Paths Status

**Endpoint:** `GET /image-browsing/paths/status`

Returns current configuration and status for all paths.

**Response:**
```json
{
  "success": true,
  "data": {
    "thumbnail_cache": {
      "current": "x:\\path\\to\\cache",
      "default": "x:\\default\\path",
      "is_default": false,
      "exists": true,
      "valid": true
    },
    "output": { ... },
    "workflows": { ... },
    "prompts": { ... }
  }
}
```

### Set Path

**Endpoint:** `POST /image-browsing/paths/set`

Set a specific path configuration.

**Request:**
```json
{
  "type": "thumbnail_cache",
  "path": "x:\\my\\custom\\cache\\path"
}
```

**Valid types:** `thumbnail_cache`, `output`, `workflows`, `prompts`

**Response:**
```json
{
  "success": true,
  "message": "thumbnail_cache path updated successfully",
  "data": {
    "type": "thumbnail_cache",
    "path": "x:\\my\\custom\\cache\\path",
    "validation": {
      "valid": true,
      "created": true,
      "message": "Directory created: x:\\my\\custom\\cache\\path"
    }
  }
}
```

### Validate Path

**Endpoint:** `POST /image-browsing/paths/validate`

Validate a path without saving it.

**Request:**
```json
{
  "path": "x:\\test\\path",
  "create_if_missing": false
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "valid": true,
    "exists": true
  }
}
```

### Reset to Defaults

**Endpoint:** `POST /image-browsing/paths/reset`

Reset all paths to their default values.

**Response:**
```json
{
  "success": true,
  "message": "All paths reset to defaults",
  "data": {
    "thumbnail_cache": "...",
    "output": "...",
    "workflows": "...",
    "prompts": "..."
  }
}
```

## Path Validation

When setting a new path, the following validations are performed:

1. **Not empty** - Path must not be empty
2. **Absolute path** - Path must be absolute, not relative
3. **Directory** - If path exists, it must be a directory (not a file)
4. **Writable** - Directory must be writable (if it exists)
5. **Auto-create** - Non-existent directories are automatically created

### Validation Errors

Common validation errors:

| Error | Meaning |
|-------|---------|
| `Path is empty` | No path provided |
| `Path must be absolute` | Relative path provided (e.g., `./cache`) |
| `Path does not exist` | Path doesn't exist and creation failed |
| `Path exists but is not a directory` | Path points to a file |
| `Directory is not writable` | No write permissions |
| `Failed to create directory: {error}` | Auto-creation failed |

## Usage Examples

### Using cURL

**Get current paths:**
```bash
curl http://127.0.0.1:8188/image-browsing/paths/status
```

**Set thumbnail cache path:**
```bash
curl -X POST http://127.0.0.1:8188/image-browsing/paths/set \
  -H "Content-Type: application/json" \
  -d '{
    "type": "thumbnail_cache",
    "path": "D:\\ComfyUI\\cache"
  }'
```

**Validate a path:**
```bash
curl -X POST http://127.0.0.1:8188/image-browsing/paths/validate \
  -H "Content-Type: application/json" \
  -d '{
    "path": "D:\\ComfyUI\\cache",
    "create_if_missing": true
  }'
```

**Reset to defaults:**
```bash
curl -X POST http://127.0.0.1:8188/image-browsing/paths/reset
```

### Using JavaScript (in browser console)

**Get current paths:**
```javascript
fetch('/image-browsing/paths/status')
  .then(r => r.json())
  .then(console.log)
```

**Set output path:**
```javascript
fetch('/image-browsing/paths/set', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    type: 'output',
    path: 'D:\\MyOutput'
  })
})
  .then(r => r.json())
  .then(console.log)
```

## Important Notes

### Thumbnail Cache

- Changing the `thumbnail_cache` path **does not** automatically migrate existing cache files
- The extension will need to rebuild thumbnails in the new location
- Consider moving cache files manually if you want to preserve them
- Cache uses subdirectories (first 2 characters of hash) for performance

### Output Directory

- Changing the `output` path changes where the extension looks for media files
- This should typically match ComfyUI's output directory
- Changing this affects all file browsing operations

### Workflows and Prompts

- These directories are created automatically if they don't exist
- Workflow files must have `.json` extension
- Prompt files must have `.txt` extension

### Path Format

- **Windows:** Use forward slashes `/` or double backslashes `\\`
  - Good: `D:/ComfyUI/output` or `D:\\ComfyUI\\output`
  - Bad: `D:\ComfyUI\output` (single backslashes in JSON)
- **Linux/Mac:** Use forward slashes `/`
  - Good: `/home/user/comfyui/output`

### Restart Requirements

- Configuration is loaded on extension startup
- **No restart required** when changing paths via API - changes take effect immediately
- Exception: `thumbnail_cache` - existing cache instance continues using old path until restart

## Troubleshooting

### "Path must be absolute" error

Ensure you're providing a full path, not a relative one:
- ❌ `./cache` or `cache`
- ✅ `x:/ComfyUI/cache` or `/home/user/cache`

### "Directory is not writable" error

Check folder permissions:
- Windows: Right-click → Properties → Security
- Linux/Mac: `chmod 755 /path/to/directory`

### Paths not persisting

1. Check if `paths_config.json` is being created in the extension directory
2. Verify write permissions on the extension directory
3. Check console/logs for error messages

### Cache not using new path

- Restart ComfyUI after changing `thumbnail_cache` path
- The cache instance is created once on startup

## Implementation Details

### Backend Files

- **`py/paths_config.py`** - Path configuration management
- **`py/config.py`** - Configuration variables
- **`py/services.py`** - Cache implementation (uses configured path)
- **`__init__.py`** - API endpoints and initialization

### Configuration Loading

1. Extension starts → `__init__.py` loads
2. `paths_config.load_paths_config()` reads `paths_config.json`
3. Paths are set in `config` module
4. Directories are created if they don't exist
5. `CacheHelper` in `services.py` uses configured cache path

### In-Memory Updates

When paths are changed via API:
- Configuration file is updated
- In-memory `config` variables are updated immediately
- Changes take effect without restart (except for cache)

## Future Frontend Integration

The API endpoints are ready for frontend UI integration. A settings panel could be added to allow users to:

1. View current paths and their status
2. Change paths with file/folder picker
3. Validate paths before saving
4. Reset to defaults with one click
5. See which paths are using custom vs default values

Similar to the FFmpeg settings interface, this could be integrated into ComfyUI's settings dialog or a custom settings panel in the Image Browsing extension.
