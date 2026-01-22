# Тестирование API настройки путей

## Быстрая проверка

Откройте браузер, зайдите на ComfyUI (обычно `http://127.0.0.1:8188`), откройте консоль разработчика (F12), и выполните эти команды:

### 1. Проверить текущие пути

```javascript
fetch('/image-browsing/paths/status')
  .then(r => r.json())
  .then(data => {
    console.log('Статус путей:', data);
    if (data.success) {
      console.table(data.data);
    }
  })
  .catch(err => console.error('Ошибка:', err));
```

**Ожидаемый результат:** Должна вернуться информация о всех 4 путях (thumbnail_cache, output, workflows, prompts) с их текущими значениями и статусом.

---

### 2. Проверить валидацию пути

```javascript
// Проверка существующего пути (должна пройти)
fetch('/image-browsing/paths/validate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    path: 'x:/ComfyUI_windows_portable_worker/ComfyUI/output',
    create_if_missing: false
  })
})
  .then(r => r.json())
  .then(data => console.log('Валидация пути:', data))
  .catch(err => console.error('Ошибка:', err));
```

**Ожидаемый результат:** `{ success: true, data: { valid: true, exists: true } }`

---

### 3. Установить путь для thumbnail_cache

```javascript
fetch('/image-browsing/paths/set', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    type: 'thumbnail_cache',
    path: 'x:/ComfyUI_windows_portable_worker/ComfyUI/my_custom_cache'
  })
})
  .then(r => r.json())
  .then(data => {
    console.log('Результат установки пути:', data);
    if (data.success) {
      console.log('✓ Путь успешно установлен!');
      console.log('Путь:', data.data.path);
      console.log('Валидация:', data.data.validation);
    } else {
      console.error('✗ Ошибка:', data.error);
    }
  })
  .catch(err => console.error('Ошибка:', err));
```

**Ожидаемый результат:**
```javascript
{
  success: true,
  message: "thumbnail_cache path updated successfully",
  data: {
    type: "thumbnail_cache",
    path: "x:/ComfyUI_windows_portable_worker/ComfyUI/my_custom_cache",
    validation: { valid: true, created: true, ... }
  }
}
```

---

### 4. Проверить, что путь сохранился

```javascript
fetch('/image-browsing/paths/status')
  .then(r => r.json())
  .then(data => {
    if (data.success) {
      const cacheInfo = data.data.thumbnail_cache;
      console.log('Информация о thumbnail_cache:');
      console.log('  Текущий путь:', cacheInfo.current);
      console.log('  По умолчанию:', cacheInfo.default);
      console.log('  Использует дефолт:', cacheInfo.is_default);
      console.log('  Существует:', cacheInfo.exists);
      console.log('  Валиден:', cacheInfo.valid);
    }
  });
```

---

### 5. Сбросить все пути к значениям по умолчанию

```javascript
fetch('/image-browsing/paths/reset', {
  method: 'POST'
})
  .then(r => r.json())
  .then(data => {
    console.log('Результат сброса:', data);
    if (data.success) {
      console.log('✓ Все пути сброшены к значениям по умолчанию');
      console.log('Новые значения:', data.data);
    }
  })
  .catch(err => console.error('Ошибка:', err));
```

---

## Проверка файла конфигурации

После установки путей, проверьте, что файл конфигурации создан:

```bash
cd x:\ComfyUI_windows_portable_worker\ComfyUI\custom_nodes\ComfyUI-Image-Browsing
cat paths_config.json
```

Должно быть что-то вроде:

```json
{
  "thumbnail_cache": "x:/ComfyUI_windows_portable_worker/ComfyUI/my_custom_cache",
  "output": "x:/ComfyUI_windows_portable_worker/ComfyUI/output",
  "workflows": "x:/ComfyUI_windows_portable_worker/ComfyUI/user/default/workflows",
  "prompts": "x:/ComfyUI_windows_portable_worker/ComfyUI/user/default/prompts"
}
```

---

## Тестирование через cURL

Если у вас есть curl, можете тестировать из командной строки:

### Получить статус

```bash
curl http://127.0.0.1:8188/image-browsing/paths/status
```

### Установить путь

```bash
curl -X POST http://127.0.0.1:8188/image-browsing/paths/set ^
  -H "Content-Type: application/json" ^
  -d "{\"type\":\"thumbnail_cache\",\"path\":\"x:/ComfyUI_windows_portable_worker/ComfyUI/cache\"}"
```

---

## Возможные ошибки

### Ошибка: "Module not found"

Если вы видите ошибку в консоли ComfyUI при загрузке:
```
ModuleNotFoundError: No module named 'folder_paths'
```

**Решение:** Убедитесь, что ComfyUI полностью запущен. Модуль `folder_paths` доступен только после загрузки ComfyUI.

### Ошибка: 404 Not Found

Если API endpoint возвращает 404:

1. Проверьте, что расширение загружено: в консоли ComfyUI должно быть сообщение о загрузке "ComfyUI Image Browsing"
2. Перезапустите ComfyUI
3. Проверьте, что нет ошибок импорта в логах

### Ошибка: "Path must be absolute"

Если валидация пути не проходит:
- ❌ Неправильно: `./cache` или `cache` (относительные пути)
- ✅ Правильно: `x:/ComfyUI/cache` или `/home/user/cache` (абсолютные пути)

### Ошибка: "Directory is not writable"

Проверьте права доступа к папке:
- Windows: Правый клик → Свойства → Безопасность
- Linux/Mac: `chmod 755 /path/to/directory`

---

## Проверка работы cache

После изменения `thumbnail_cache` пути:

1. **Важно:** Перезапустите ComfyUI, чтобы кеш начал использовать новый путь
2. Откройте Image Browsing
3. Просмотрите несколько изображений
4. Проверьте, что в новом пути создаются файлы кеша:

```bash
cd x:/ComfyUI_windows_portable_worker/ComfyUI/my_custom_cache
ls -la
```

Вы должны увидеть подпапки с именами из 2 символов (00, 01, 02...) и внутри файлы .webp

---

## Диагностика

Если что-то не работает:

1. **Проверьте консоль браузера** (F12) на ошибки JavaScript
2. **Проверьте консоль/логи ComfyUI** на ошибки Python
3. **Проверьте Network tab** в DevTools - видны ли запросы к API?
4. **Проверьте файл paths_config.json** - создан ли он и корректен ли JSON?

---

## Успешный результат

Если всё работает правильно, вы должны:

1. ✅ Получить данные от `/image-browsing/paths/status`
2. ✅ Успешно установить новый путь через `/image-browsing/paths/set`
3. ✅ Увидеть созданный файл `paths_config.json`
4. ✅ После перезапуска ComfyUI, кеш должен использовать новый путь
