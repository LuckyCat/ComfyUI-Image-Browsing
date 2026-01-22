# Реализованные изменения - Настройки путей

## Что было сделано

✅ **Добавлены настройки в UI для управления путями:**

1. **Thumbnail Cache Directory** - папка для кеша превью
2. **Output Directory** - папка с выходными файлами
3. **Workflows Directory** - папка с workflow файлами
4. **Prompts Directory** - папка с файлами промптов
5. **FFmpeg Path** - путь к FFmpeg

Все настройки находятся в **Settings → Output Explorer**.

---

## Структура файлов

### Backend (Python)

1. **`py/paths_config.py`** - Модуль управления путями
   - `load_paths_config()` - загрузка конфигурации
   - `save_paths_config()` - сохранение
   - `validate_path()` - валидация путей
   - `get_all_paths()` - получение статуса всех путей
   - `set_path()` - установка пути

2. **`py/config.py`** - Добавлена переменная `thumbnail_cache_uri`

3. **`py/services.py`** - CacheHelper использует настраиваемый путь кеша

4. **`__init__.py`** - API endpoints:
   - `GET /image-browsing/paths/status` - статус всех путей
   - `POST /image-browsing/paths/set` - установить путь
   - `POST /image-browsing/paths/validate` - валидировать путь
   - `POST /image-browsing/paths/reset` - сбросить к defaults

### Frontend (TypeScript/Vue)

1. **`src/hooks/pathsSettings.ts`** - Store для настроек путей
   - Регистрирует все 5 настроек в ComfyUI Settings
   - Загружает текущие значения из backend API
   - Сохраняет изменения через API
   - Показывает подсказки (tooltips)

2. **`src/App.vue`** - Добавлен импорт `pathsSettings` для инициализации

---

## Как это работает

### 1. При запуске ComfyUI:

```
Backend (__init__.py)
  ↓
load_paths_config() - читает paths_config.json
  ↓
Устанавливает: config.thumbnail_cache_uri, config.output_uri и т.д.
  ↓
Создаёт папки если не существуют
  ↓
CacheHelper использует config.thumbnail_cache_uri
```

### 2. При загрузке UI:

```
Frontend (pathsSettings.ts)
  ↓
onMounted() - выполняется при инициализации
  ↓
fetch('/image-browsing/paths/status') - загружает текущие пути
  ↓
app.ui.settings.addSetting() - регистрирует 5 настроек
  ↓
Пользователь видит настройки в UI
```

### 3. При изменении настройки:

```
Пользователь меняет значение в Settings
  ↓
onChange callback
  ↓
fetch('/image-browsing/paths/set', {type, path})
  ↓
Backend валидирует путь
  ↓
Сохраняет в paths_config.json
  ↓
Обновляет config.* в памяти
  ↓
✓ Готово (работает сразу, кроме thumbnail_cache)
```

---

## Конфигурационные файлы

### `paths_config.json`

Создаётся автоматически при первом изменении настроек.

**Местоположение:** `ComfyUI/custom_nodes/ComfyUI-Image-Browsing/paths_config.json`

**Формат:**
```json
{
  "thumbnail_cache": "x:/ComfyUI_windows_portable/ComfyUI/custom_nodes/ComfyUI-Image-Browsing/thumbnail_cache",
  "output": "x:/ComfyUI_windows_portable/ComfyUI/output",
  "workflows": "x:/ComfyUI_windows_portable/ComfyUI/user/default/workflows",
  "prompts": "x:/ComfyUI_windows_portable/ComfyUI/user/default/prompts"
}
```

### `ffmpeg_config.json`

Хранит путь к FFmpeg (уже существовал ранее).

**Формат:**
```json
{
  "ffmpeg_path": "X:\\ComfyUI_windows_portable\\tools\\ffmpeg\\bin\\ffmpeg.exe"
}
```

---

## Значения по умолчанию

| Настройка | Значение по умолчанию |
|-----------|----------------------|
| Thumbnail Cache | `{extension_dir}/thumbnail_cache` |
| Output | Из `folder_paths.get_output_directory()` |
| Workflows | `{comfyui_base}/user/default/workflows` |
| Prompts | `{comfyui_base}/user/default/prompts` |
| FFmpeg | `ffmpeg` (из системного PATH) |

---

## Особенности реализации

### 1. Показ абсолютного пути

Все пути показываются как **абсолютные** в UI:
- ✅ `x:/ComfyUI_windows_portable/ComfyUI/user/default/prompts`
- ❌ Не просто "default"

Это достигается тем, что backend возвращает полные пути через `get_all_paths()`.

### 2. Валидация

При установке пути backend проверяет:
- Путь не пустой
- Путь абсолютный (не относительный)
- Папка существует или может быть создана
- Есть права на запись

### 3. Автосоздание папок

Если папка не существует, backend **автоматически создаёт** её при установке пути.

### 4. Thumbnail Cache требует перезапуска

**Важно:** После изменения `Thumbnail Cache Directory` нужен **перезапуск ComfyUI**, так как `CacheHelper` инициализируется один раз при старте.

Остальные пути работают сразу без перезапуска.

### 5. Tooltip подсказки

Каждая настройка имеет tooltip с объяснением:
- Для чего используется
- Примеры значений
- Особенности (например, "требует перезапуска")

---

## Как использовать

### 1. Открыть настройки

ComfyUI → Settings (⚙️) → Output Explorer

### 2. Изменить путь

Найти нужную настройку (например, "Prompts Directory") и ввести новый путь:

```
X:/ComfyUI_windows_portable/ComfyUI/user/default/prompts
```

или

```
D:/MyComfyPrompts
```

**Важно для Windows:** Используйте `/` или `\\` (не одинарный `\`)

### 3. Проверить результат

- Откройте консоль браузера (F12)
- Должно быть сообщение: `[PathsSettings] Prompts path updated: ...`
- Для FFmpeg также покажет результат теста

### 4. Проверить файл конфигурации

```bash
cat ComfyUI/custom_nodes/ComfyUI-Image-Browsing/paths_config.json
```

Должен содержать ваши новые значения.

---

## Тестирование

### Тест 1: Изменить Prompts Directory

```javascript
// В консоли браузера (после открытия Settings)
fetch('/image-browsing/paths/set', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    type: 'prompts',
    path: 'D:/MyPrompts'
  })
})
  .then(r => r.json())
  .then(console.log)
```

Ожидаемый результат:
```json
{
  "success": true,
  "message": "prompts path updated successfully",
  "data": {
    "type": "prompts",
    "path": "D:/MyPrompts",
    "validation": { "valid": true, "created": true }
  }
}
```

### Тест 2: Установить FFmpeg Path

```javascript
fetch('/image-browsing/ffmpeg/set-path', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    path: 'X:/ComfyUI_windows_portable/tools/ffmpeg/bin/ffmpeg.exe'
  })
})
  .then(r => r.json())
  .then(console.log)
```

Ожидаемый результат:
```json
{
  "success": true,
  "message": "FFmpeg path saved",
  "data": {
    "available": true,
    "path": "X:/ComfyUI_windows_portable/tools/ffmpeg/bin/ffmpeg.exe",
    "version": "ffmpeg version ...",
    "error": null
  }
}
```

### Тест 3: Получить все пути

```javascript
fetch('/image-browsing/paths/status')
  .then(r => r.json())
  .then(data => {
    console.table(data.data)
  })
```

---

## Решение проблем

### Настройки не появились в UI

**Проверьте:**
1. Перезапустили ли ComfyUI после копирования файлов?
2. Очищен ли кеш браузера?
3. Есть ли ошибки в консоли браузера (F12)?

**Решение:**
```bash
# 1. Пересобрать frontend
cd x:\ComfyUI_windows_portable_worker\ComfyUI\custom_nodes\ComfyUI-Image-Browsing
npm run build

# 2. Скопировать файлы (см. BUILD_INSTRUCTIONS.md)

# 3. Перезапустить ComfyUI

# 4. Очистить кеш браузера
# DevTools (F12) → Application → Clear storage
```

### Путь не сохраняется

**Проверьте консоль браузера:**
- Есть ли ошибка `Failed to set path: ...`?
- Что говорит backend?

**Проверьте консоль ComfyUI:**
- Есть ли Python ошибки?
- Traceback?

**Частые причины:**
- Путь относительный (нужен абсолютный)
- Нет прав на создание папки
- Неправильный формат пути в Windows (`\` вместо `/`)

### FFmpeg не работает

**Проверьте:**
```bash
# Протестируйте FFmpeg вручную
X:\ComfyUI_windows_portable\tools\ffmpeg\bin\ffmpeg.exe -version
```

Если работает, то путь правильный. Если нет - проверьте, что файл существует.

---

## Дальнейшие улучшения (опционально)

1. **File picker** - добавить кнопку выбора папки в UI
2. **Migration tool** - инструмент для переноса кеша при изменении пути
3. **Path validation UI** - показывать ✓/✗ рядом с полем ввода
4. **Reset button** - кнопка сброса к defaults для каждого пути
5. **Path presets** - предустановленные комбинации путей

---

## Файлы для копирования

Если вы работаете в другой директории (`_worker`), скопируйте эти файлы:

### Backend:
- `py/paths_config.py` (новый)
- `py/config.py` (изменён)
- `py/services.py` (изменён)
- `__init__.py` (изменён)

### Frontend (после npm run build):
- `web/*` (все скомпилированные файлы)

### Документация:
- `PATHS_CONFIG_GUIDE.md` (новый)
- `START_HERE.md` (новый)
- `TEST_API.md` (новый)
- `BUILD_INSTRUCTIONS.md` (новый)
- `IMPLEMENTATION_SUMMARY.md` (этот файл)

---

**Версия:** 1.0
**Дата:** 2026-01-11
**Статус:** ✅ Готово к тестированию
