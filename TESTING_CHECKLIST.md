# Testing Checklist for Path Settings

## Status: Ready for Testing

The frontend has been rebuilt with the fixed `pathsSettings.ts` implementation.

## Files Updated

✅ **Frontend rebuilt:** Jan 11, 00:51
✅ **Files copied to:** `X:\ComfyUI_windows_portable\ComfyUI\custom_nodes\ComfyUI-Image-Browsing\web\`

### What Changed

Fixed the critical issue preventing settings registration:
- **Problem:** Used `onMounted()` inside Pinia store which never executes
- **Solution:** Rewrote to use direct async initialization on module import
- **Result:** Settings should now register when `App.vue` imports the module

## Testing Steps

### 1. Restart ComfyUI

Stop and restart ComfyUI from `X:\ComfyUI_windows_portable\` directory.

### 2. Open Browser Console (F12)

Look for these log messages:

```
[PathsSettings] Initializing...
[PathsSettings] Loaded paths from backend: {...}
[PathsSettings] Loaded FFmpeg path: ...
[PathsSettings] Registering settings...
[PathsSettings] All settings registered successfully
```

**If you see these messages** ✅ → Settings registration worked!

**If you DON'T see these messages** ❌ → Module initialization failed

### 3. Open ComfyUI Settings

Click **Settings (⚙️)** → Navigate to **Output Explorer**

### 4. Verify All Settings Appear

Should see **2 categories**:

#### FFmpeg Section
- **FFmpeg Path**
  - Shows current FFmpeg path
  - Can be changed to: `X:\ComfyUI_windows_portable\tools\ffmpeg\bin\ffmpeg.exe`

#### Paths Section
- **Thumbnail Cache Directory**
  - Shows: `X:\ComfyUI_windows_portable_worker\...\thumbnail_cache`
  - Tooltip: "requires restart to take effect"

- **Output Directory**
  - Shows: `X:\ComfyUI_windows_portable_worker\ComfyUI\output`

- **Workflows Directory**
  - Shows: `X:\ComfyUI_windows_portable\ComfyUI\user\default\workflows`

- **Prompts Directory**
  - Shows: `X:\ComfyUI_windows_portable_worker\ComfyUI\user\default\prompts`

**All paths should be ABSOLUTE paths** (full path from drive letter).

### 5. Test Changing a Path

Try changing **Prompts Directory**:

1. Enter a new path (e.g., `D:\MyPrompts` or any valid path)
2. Check browser console for:
   ```
   [PathsSettings] Prompts path updated: D:\MyPrompts
   ```
3. Verify the path was saved:
   ```javascript
   fetch('/image-browsing/paths/status')
     .then(r => r.json())
     .then(data => console.log(data.data.prompts))
   ```
   Should show your new path.

### 6. Verify Configuration File

Check that changes persist:

```bash
cat "X:\ComfyUI_windows_portable\ComfyUI\custom_nodes\ComfyUI-Image-Browsing\paths_config.json"
```

Should contain your new path in JSON format.

## Expected Results

✅ All 5 settings visible in UI
✅ All paths show absolute paths
✅ Console logs show successful initialization
✅ Changing paths saves to backend
✅ Changes persist in `paths_config.json`

## If Settings Don't Appear

### Check Console for Errors

Look for:
- Import errors
- API fetch failures
- `app.ui.settings` not available

### Verify API Works

Test backend directly:
```javascript
fetch('/image-browsing/paths/status')
  .then(r => r.json())
  .then(console.log)
```

Should return all paths with validation status.

### Check Files Were Copied

Verify the new build is present:
```bash
ls -lh "X:\ComfyUI_windows_portable\ComfyUI\custom_nodes\ComfyUI-Image-Browsing\web"
```

Look for files dated Jan 11, 00:51.

## Next Steps

If everything works:
1. ✅ Settings appear correctly
2. ✅ Can change paths
3. ✅ Changes persist

Then the implementation is complete!

If there are still issues:
1. Share the browser console output
2. Share any error messages
3. Verify `app.ui.settings` exists in console

---

**Build Date:** 2026-01-11 00:51
**Status:** Awaiting user testing
