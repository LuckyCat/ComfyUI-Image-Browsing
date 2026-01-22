# Build Instructions

## Rebuild Frontend After Changes

После изменения файлов в `src/`, нужно перекомпилировать frontend:

```bash
cd x:\ComfyUI_windows_portable_worker\ComfyUI\custom_nodes\ComfyUI-Image-Browsing
npm run build
```

## Copy Files to Running Instance

Затем скопируйте файлы в рабочую директорию ComfyUI:

```bash
# Copy Python backend files
xcopy /Y "x:\ComfyUI_windows_portable_worker\ComfyUI\custom_nodes\ComfyUI-Image-Browsing\py\paths_config.py" "X:\ComfyUI_windows_portable\ComfyUI\custom_nodes\ComfyUI-Image-Browsing\py\"

xcopy /Y "x:\ComfyUI_windows_portable_worker\ComfyUI\custom_nodes\ComfyUI-Image-Browsing\py\config.py" "X:\ComfyUI_windows_portable\ComfyUI\custom_nodes\ComfyUI-Image-Browsing\py\"

xcopy /Y "x:\ComfyUI_windows_portable_worker\ComfyUI\custom_nodes\ComfyUI-Image-Browsing\py\services.py" "X:\ComfyUI_windows_portable\ComfyUI\custom_nodes\ComfyUI-Image-Browsing\py\"

xcopy /Y "x:\ComfyUI_windows_portable_worker\ComfyUI\custom_nodes\ComfyUI-Image-Browsing\__init__.py" "X:\ComfyUI_windows_portable\ComfyUI\custom_nodes\ComfyUI-Image-Browsing\"

# Copy built frontend files
xcopy /Y /S "x:\ComfyUI_windows_portable_worker\ComfyUI\custom_nodes\ComfyUI-Image-Browsing\web\*" "X:\ComfyUI_windows_portable\ComfyUI\custom_nodes\ComfyUI-Image-Browsing\web\"
```

## Restart ComfyUI

После копирования файлов:

1. Остановите ComfyUI (Ctrl+C в консоли)
2. Запустите снова

## Verify Settings Appear

После перезапуска, откройте ComfyUI Settings → Output Explorer.

Должны появиться следующие настройки:

### FFmpeg
- FFmpeg Path

### Paths
- Thumbnail Cache Directory
- Output Directory
- Workflows Directory
- Prompts Directory

## Troubleshooting

### Settings not appearing

1. Check browser console (F12) for errors
2. Clear browser cache
3. Verify files were copied correctly
4. Check ComfyUI console for Python errors

### Build fails

```bash
# Install dependencies if missing
npm install

# Try build again
npm run build
```

### TypeScript errors

Check that all imports are correct in `pathsSettings.ts`
