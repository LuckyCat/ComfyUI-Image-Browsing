# ⚙️ Settings Configuration Guide

## Overview

ComfyUI Image Browsing settings are available in **ComfyUI Settings → Output Explorer**.

All settings are automatically saved and persist between sessions.

---

## 📍 Available Settings

### 1. **Delete Confirmation** (`Delete` category)

**Show delete confirmation dialog**

- **Type:** Toggle (boolean)
- **Default:** `true` (enabled)
- **Description:** Show confirmation dialog before deleting files
- **Location:** Settings → Output Explorer → Delete

When enabled, you'll see a confirmation prompt before deleting any files or folders.

---

### 2. **FFmpeg Path** (`FFmpeg` category)

**Path to FFmpeg executable**

- **Type:** Text input
- **Default:** `ffmpeg` (use system PATH)
- **Location:** Settings → Output Explorer → FFmpeg
- **Tooltip:** Path to FFmpeg executable (e.g., "ffmpeg", "C:\ffmpeg\bin\ffmpeg.exe", or "/usr/bin/ffmpeg")

**Examples:**
```
ffmpeg                                    # Use system PATH (recommended)
C:\ffmpeg\bin\ffmpeg.exe                  # Windows custom path
/usr/local/bin/ffmpeg                     # Linux/Mac custom path
```

**How it works:**
1. Enter the path to FFmpeg
2. Backend automatically tests if FFmpeg is working
3. If test passes, path is saved to `ffmpeg_config.json`
4. If test fails, error is shown in console

**Troubleshooting:**
- Check console for errors: `Failed to set FFmpeg path: ...`
- Verify FFmpeg is installed: run `ffmpeg -version` in terminal
- See [FFMPEG_CONFIGURATION.md](FFMPEG_CONFIGURATION.md) for detailed guide

---

### 3. **Output Directory** (`Paths` category)

**Custom output directory path**

- **Type:** Text input
- **Default:** Empty (use ComfyUI default output)
- **Location:** Settings → Output Explorer → Paths
- **Tooltip:** Custom output directory path (leave empty for default ComfyUI output)

**Examples:**
```
                                          # Empty = use default ComfyUI output
D:\MyImages\ComfyUI_Output                # Windows custom path
/mnt/storage/comfyui/output               # Linux custom path
```

**How it works:**
1. Leave empty to use default ComfyUI output directory
2. Or enter custom path to use different location
3. Directory must exist (not created automatically)
4. Saved to `paths_config.json`

**Use cases:**
- Store outputs on different drive (SSD vs HDD)
- Organize outputs in custom folder structure
- Use network/cloud storage location

---

### 4. **Workflows Directory** (`Paths` category)

**Custom workflows directory path**

- **Type:** Text input
- **Default:** Empty (use `ComfyUI/user/default/workflows`)
- **Location:** Settings → Output Explorer → Paths
- **Tooltip:** Custom workflows directory path (leave empty for default)

**Examples:**
```
                                          # Empty = use default
D:\MyWorkflows                            # Windows custom path
/home/user/comfyui-workflows              # Linux custom path
```

**How it works:**
- Same as Output Directory
- Used for workflow file browser/management
- Directory must exist

---

### 5. **Prompts Directory** (`Paths` category)

**Custom prompts directory path**

- **Type:** Text input
- **Default:** Empty (use `ComfyUI/user/default/prompts`)
- **Location:** Settings → Output Explorer → Paths
- **Tooltip:** Custom prompts directory path (leave empty for default)

**Examples:**
```
                                          # Empty = use default
D:\MyPrompts                              # Windows custom path
/home/user/comfyui-prompts                # Linux custom path
```

**How it works:**
- Same as Output Directory
- Used for prompt file browser/management
- Directory must exist

---

## 💾 Configuration Files

### `ffmpeg_config.json`

Stores FFmpeg path configuration.

**Location:** `ComfyUI/custom_nodes/ComfyUI-Image-Browsing/ffmpeg_config.json`

**Format:**
```json
{
  "ffmpeg_path": "ffmpeg"
}
```

### `paths_config.json`

Stores custom directory paths.

**Location:** `ComfyUI/custom_nodes/ComfyUI-Image-Browsing/paths_config.json`

**Format:**
```json
{
  "output_path": "",
  "workflows_path": "",
  "prompts_path": ""
}
```

**Note:** Empty strings mean "use default". File is created automatically when you save any path setting.

---

## 🔄 How Settings Work

### Frontend → Backend Flow

1. **User changes setting** in ComfyUI Settings UI
2. **Frontend** updates reactive ref (immediate UI feedback)
3. **Frontend** sends POST request to backend API:
   - FFmpeg: `/image-browsing/ffmpeg/set-path`
   - Paths: `/image-browsing/config/set-path`
4. **Backend** validates and saves to JSON file
5. **Backend** updates in-memory config
6. **Backend** returns success/error response

### Backend → Frontend Flow (on load)

1. **ComfyUI starts**, extension initializes
2. **Backend** loads config from JSON files
3. **Backend** sets `config.output_uri`, `config.workflows_uri`, etc.
4. **Frontend** reads settings from `app.ui.settings.getSettingValue()`
5. **UI** displays current values

---

## 🐛 Troubleshooting

### Settings don't appear in UI

**Symptoms:**
- Settings → Output Explorer section is missing
- Only "Delete" and "Thumbnail Size" are visible

**Possible causes:**
1. Frontend not recompiled after changes
2. Browser cache showing old version
3. Settings registration failed

**Solutions:**
```bash
# 1. Clear browser cache
# In DevTools: Application → Clear storage → Clear site data

# 2. Check console for errors
# Look for: "Failed to set FFmpeg path" or similar

# 3. Verify config.ts is loaded
console.log(app.ui.settings.store)  # Should show all settings
```

### Settings don't persist after restart

**Symptoms:**
- Settings reset to default after ComfyUI restart
- JSON config files are empty or missing

**Check:**
```bash
# Verify config files exist
ls ComfyUI/custom_nodes/ComfyUI-Image-Browsing/*.json

# Should see:
# ffmpeg_config.json
# paths_config.json
```

**Solutions:**
1. Check file permissions (write access)
2. Check console for save errors
3. Manually verify JSON files are valid

### Path validation fails

**Symptoms:**
- "Directory not found" error when setting custom path
- Backend rejects the path

**Solutions:**
1. Verify directory exists: `ls /your/custom/path`
2. Check permissions (read access)
3. Use absolute paths, not relative
4. On Windows, use forward slashes or escape backslashes:
   - ✅ `C:/ComfyUI/output`
   - ✅ `C:\\ComfyUI\\output`
   - ❌ `C:\ComfyUI\output` (in JSON)

---

## 🎯 Best Practices

### 1. Use Default Paths When Possible

The defaults work for 99% of users:
- Output: ComfyUI's configured output directory
- Workflows/Prompts: `ComfyUI/user/default/`

Only change if you have specific requirements.

### 2. FFmpeg Path

**Recommended:** Install FFmpeg system-wide and use `ffmpeg` (default)

**When to use custom path:**
- Portable FFmpeg installation
- Multiple FFmpeg versions
- Non-standard installation location

### 3. Backup Configs

The JSON config files are small. Back them up:
```bash
cp ffmpeg_config.json ffmpeg_config.json.backup
cp paths_config.json paths_config.json.backup
```

### 4. Testing Changes

After changing paths:
1. Check console for errors
2. Try browsing files (verify it works)
3. Restart ComfyUI (verify persistence)

---

## 📚 Related Documentation

- [FFMPEG_CONFIGURATION.md](FFMPEG_CONFIGURATION.md) - Detailed FFmpeg setup guide
- [CACHE_ALL_EXPLAINED.md](CACHE_ALL_EXPLAINED.md) - Cache optimization guide

---

**Version:** 1.0
**Date:** 2026-01-10
