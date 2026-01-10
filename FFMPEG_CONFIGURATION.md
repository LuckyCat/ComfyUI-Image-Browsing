# 🎬 FFmpeg Configuration Guide

## Обзор

ComfyUI Image Browsing использует FFmpeg для работы с видео:
- Объединение видео (merge)
- Извлечение кадров
- Генерация превью видео
- Разделение видео
- Реверс видео

По умолчанию используется `ffmpeg` из системного PATH, но вы можете настроить кастомный путь.

---

## 🚀 Быстрый старт

### Вариант 1: Использовать системный FFmpeg (рекомендуется)

Если FFmpeg уже установлен в системе:
```bash
# Проверить
ffmpeg -version

# Если работает - ничего настраивать не нужно!
```

### Вариант 2: Автоопределение

```javascript
// В DevTools Console или через API
fetch('/image-browsing/ffmpeg/auto-detect', { method: 'POST' })
  .then(r => r.json())
  .then(console.log)
```

### Вариант 3: Ручная настройка

```javascript
// Установить кастомный путь
fetch('/image-browsing/ffmpeg/set-path', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    path: 'C:/ffmpeg/bin/ffmpeg.exe'  // Для Windows
    // path: '/usr/local/bin/ffmpeg'  // Для Linux/Mac
  })
})
```

---

## 📁 Файлы конфигурации

### `ffmpeg_config.json`

Создается автоматически в корне расширения:
```json
{
  "ffmpeg_path": "ffmpeg"
}
```

**Расположение:** `ComfyUI/custom_nodes/ComfyUI-Image-Browsing/ffmpeg_config.json`

---

## 🔧 API Endpoints

### GET `/image-browsing/ffmpeg/status`

Получить текущий статус FFmpeg:

**Response:**
```json
{
  "success": true,
  "data": {
    "current_path": "ffmpeg",
    "test": {
      "available": true,
      "path": "ffmpeg",
      "version": "ffmpeg version 6.0",
      "error": null
    },
    "detected_paths": [
      {
        "path": "ffmpeg",
        "fullpath": "/usr/bin/ffmpeg",
        "location": "System PATH",
        "recommended": true
      }
    ]
  }
}
```

### POST `/image-browsing/ffmpeg/set-path`

Установить путь к FFmpeg:

**Request:**
```json
{
  "path": "/custom/path/to/ffmpeg"
}
```

**Response:**
```json
{
  "success": true,
  "message": "FFmpeg path saved",
  "data": {
    "available": true,
    "version": "ffmpeg version 6.0"
  }
}
```

### POST `/image-browsing/ffmpeg/auto-detect`

Автоопределение и установка FFmpeg:

**Response:**
```json
{
  "success": true,
  "message": "FFmpeg auto-detected: System PATH",
  "data": {
    "path": "ffmpeg",
    "test": {
      "available": true,
      "version": "ffmpeg version 6.0"
    }
  }
}
```

---

## 🖥️ Установка FFmpeg

### Windows

**Вариант 1: Через пакетный менеджер (рекомендуется)**
```bash
# Chocolatey
choco install ffmpeg

# Scoop
scoop install ffmpeg

# WinGet
winget install ffmpeg
```

**Вариант 2: Ручная установка**
1. Скачать: https://ffmpeg.org/download.html
2. Распаковать в `C:\ffmpeg`
3. Добавить `C:\ffmpeg\bin` в PATH
4. Или указать полный путь: `C:\ffmpeg\bin\ffmpeg.exe`

### Linux

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg

# Fedora
sudo dnf install ffmpeg

# Arch
sudo pacman -S ffmpeg
```

### macOS

```bash
# Homebrew
brew install ffmpeg

# MacPorts
sudo port install ffmpeg
```

---

## 🔍 Проверка работы

### В Console

```javascript
// Проверить статус
const status = await fetch('/image-browsing/ffmpeg/status')
  .then(r => r.json())

console.log('FFmpeg available:', status.data.test.available)
console.log('Version:', status.data.test.version)
console.log('Path:', status.data.current_path)
```

### Через командную строку

```bash
# Проверить что FFmpeg в PATH
ffmpeg -version

# Проверить конкретный путь
"C:\ffmpeg\bin\ffmpeg.exe" -version
/usr/local/bin/ffmpeg -version
```

---

## 🐛 Troubleshooting

### Проблема: "FFmpeg not found"

**Решение 1: Установить FFmpeg**
См. раздел "Установка FFmpeg" выше.

**Решение 2: Указать полный путь**
```javascript
fetch('/image-browsing/ffmpeg/set-path', {
  method: 'POST',
  body: JSON.stringify({ path: 'ПОЛНЫЙ_ПУТЬ_К_FFMPEG' })
})
```

### Проблема: "FFmpeg test failed"

**Причины:**
1. Файл не найден
2. Нет прав на выполнение
3. Неправильная версия

**Проверка:**
```javascript
// Детальная диагностика
const status = await fetch('/image-browsing/ffmpeg/status').then(r => r.json())
console.log('Error:', status.data.test.error)
console.log('Detected paths:', status.data.detected_paths)
```

### Проблема: Windows - путь с пробелами

**Неправильно:**
```
C:\Program Files\ffmpeg\bin\ffmpeg.exe
```

**Правильно в конфиге:**
```json
{
  "ffmpeg_path": "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe"
}
```

**Или через API:**
```javascript
fetch('/image-browsing/ffmpeg/set-path', {
  method: 'POST',
  body: JSON.stringify({
    path: 'C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe'
  })
})
```

### Проблема: Linux/Mac - permissions

```bash
# Дать права на выполнение
chmod +x /path/to/ffmpeg

# Проверить
ls -la /path/to/ffmpeg
```

---

## 📊 Какие функции требуют FFmpeg

| Функция | Требует FFmpeg | Альтернатива |
|---------|----------------|--------------|
| Просмотр изображений | ❌ | - |
| Генерация превью изображений | ❌ | PIL/Pillow |
| **Генерация превью видео** | ✅ | Нет |
| **Объединение видео** | ✅ | Нет |
| **Извлечение кадров** | ✅ | Нет |
| **Разделение видео** | ✅ | Нет |
| **Реверс видео** | ✅ | Нет |
| Навигация по папкам | ❌ | - |

**Вывод:** FFmpeg нужен только для работы с видео.

---

## ⚙️ Расширенная конфигурация

### Использовать разные версии FFmpeg

```python
# В py/config.py или через runtime
import config

# Использовать FFmpeg 5.x для одних задач
config.ffmpeg_path = '/opt/ffmpeg5/bin/ffmpeg'

# Использовать FFmpeg 6.x для других
config.ffmpeg_path = '/opt/ffmpeg6/bin/ffmpeg'
```

### Кастомные параметры FFmpeg

Редактируйте [`py/services.py`](py/services.py) где вызываются FFmpeg команды.

Пример - изменить качество merge:
```python
# Было
"-crf", "18",

# Стало (меньше = лучше качество, больше размер)
"-crf", "15",
```

### Проверка доступных кодеков

```bash
ffmpeg -codecs | grep h264
ffmpeg -encoders
```

---

## 🎯 Best Practices

### 1. Использовать системный PATH

Самый простой способ - установить FFmpeg в систему и он будет доступен глобально.

### 2. Portable установка рядом с ComfyUI

```
ComfyUI/
  ├── custom_nodes/
  │   └── ComfyUI-Image-Browsing/
  └── tools/
      └── ffmpeg/
          └── ffmpeg.exe
```

В конфиге:
```json
{
  "ffmpeg_path": "../../tools/ffmpeg/ffmpeg.exe"
}
```

### 3. Проверка при старте

Добавить в инициализацию:
```python
# В __init__.py
from .py import ffmpeg_config

# Проверить FFmpeg при загрузке
test = ffmpeg_config.test_ffmpeg()
if not test['available']:
    print(f"WARNING: FFmpeg not available: {test['error']}")
    print("Video features will not work!")
```

---

## 📝 Примеры использования

### Объединить несколько видео

```javascript
const files = ['/output/video1.mp4', '/output/video2.mp4']

fetch('/image-browsing/merge-videos', {
  method: 'POST',
  body: JSON.stringify({
    file_list: files,
    output_name: 'merged.mp4'
  })
})
```

### Извлечь кадр из видео

```javascript
fetch('/image-browsing/extract-frame', {
  method: 'POST',
  body: JSON.stringify({
    video_path: '/output/video.mp4',
    frame_type: 'first'  // или 'last', 'current'
  })
})
```

### Проверить что FFmpeg работает

```javascript
async function testFFmpeg() {
  const status = await fetch('/image-browsing/ffmpeg/status')
    .then(r => r.json())

  if (status.data.test.available) {
    console.log('✅ FFmpeg OK:', status.data.test.version)
    return true
  } else {
    console.error('❌ FFmpeg ERROR:', status.data.test.error)

    // Попробовать автоопределение
    const autoDetect = await fetch('/image-browsing/ffmpeg/auto-detect', {
      method: 'POST'
    }).then(r => r.json())

    if (autoDetect.success) {
      console.log('✅ Auto-detected:', autoDetect.data.path)
      return true
    } else {
      console.error('❌ No FFmpeg found. Please install.')
      return false
    }
  }
}

testFFmpeg()
```

---

## 🔐 Безопасность

### Path Injection защита

Все пути проходят проверку:
- Тестирование перед сохранением
- Валидация существования файла
- Проверка прав доступа

### Sandboxing

FFmpeg вызывается через `subprocess` с:
- Timeout (30-60 секунд)
- capture_output (изоляция)
- Валидация параметров

---

## 📚 Дополнительные ресурсы

- [FFmpeg Official](https://ffmpeg.org/)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [FFmpeg Download](https://ffmpeg.org/download.html)
- [FFmpeg Wiki](https://trac.ffmpeg.org/)

---

**Версия:** 1.0
**Дата:** 2026-01-10
