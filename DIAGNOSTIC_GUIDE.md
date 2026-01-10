# 🔍 Диагностика проблем после оптимизации

## Проверка что все работает

### 1. Откройте DevTools Console

Нажмите F12 → Console и проверьте наличие ошибок.

**Что должно быть:**
```
[SW] Registered: /
```

**Если ошибка:**
```
[SW] Registration failed: ...
```
Это нормально - Service Worker опционален и не критичен для работы.

---

### 2. Проверьте Network вкладку

1. Откройте DevTools → Network
2. Откройте любую папку в Image Browsing
3. Посмотрите на запросы:

**Должны быть заголовки:**
- ✅ `Cache-Control: public, max-age=31536000` для превью
- ✅ `ETag: "..."` для всех ресурсов
- ✅ `Content-Encoding: gzip` для JSON

**При повторном открытии:**
- ✅ `304 Not Modified` или загрузка из disk cache

---

### 3. Проверьте localStorage

В Console выполните:
```javascript
// Проверить folder cache
const cache = localStorage.getItem('folderCache')
if (cache) {
  const parsed = JSON.parse(cache)
  console.log('Cached folders:', Object.keys(parsed).length)
} else {
  console.log('No folder cache yet')
}

// Проверить prefetch history
const history = localStorage.getItem('prefetchHistory')
if (history) {
  console.log('Prefetch history:', JSON.parse(history).length)
}
```

---

### 4. Проверьте что UI работает

**Основные функции должны работать:**
- ✅ Открытие папок
- ✅ Просмотр изображений
- ✅ Создание/удаление/перемещение файлов
- ✅ Навигация по дереву папок

---

## Если что-то не работает

### Проблема: UI не загружается вообще

**Решение 1:** Очистить кеш браузера
1. Ctrl+Shift+Delete
2. Выбрать "Cached images and files"
3. Clear data
4. F5 (перезагрузить страницу)

**Решение 2:** Отключить Service Worker (временно)
```javascript
// В src/main.ts закомментировать строки 14-23
/*
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    ...
  })
}
*/
```

**Решение 3:** Проверить консоль на ошибки JavaScript
- Могут быть конфликты с другими расширениями
- Проверьте версию браузера (нужен современный Chrome/Edge/Firefox)

---

### Проблема: Кнопки/элементы UI пропали

**Причина:** Возможно конфликт CSS или JavaScript ошибка

**Проверка:**
1. DevTools → Console → Ищите красные ошибки
2. DevTools → Elements → Найдите `<div id="comfyui-image-browsing">`
3. Проверьте что элемент отображается

**Решение:**
```javascript
// В Console проверить
document.getElementById('comfyui-image-browsing')
// Должен вернуть <div>

// Если null - проблема с монтированием Vue
// Проверьте ошибки в src/main.ts
```

---

### Проблема: Медленная загрузка

**Проверка кеширования:**
```javascript
// В Console
performance.getEntriesByType('resource')
  .filter(r => r.name.includes('/image-browsing/'))
  .forEach(r => {
    console.log(r.name, {
      duration: r.duration + 'ms',
      transferSize: r.transferSize + ' bytes',
      cached: r.transferSize === 0 ? 'YES' : 'NO'
    })
  })
```

**Если transferSize > 0 для повторных запросов:**
- Кеш не работает
- Проверьте заголовки Cache-Control
- Убедитесь что ETag совпадают

---

### Проблема: Service Worker ошибки

**Безопасно отключить:**
```javascript
// В Chrome DevTools → Application → Service Workers
// Нажать "Unregister" для comfyui-image-browsing

// ИЛИ в Console:
navigator.serviceWorker.getRegistrations()
  .then(registrations => {
    registrations.forEach(r => r.unregister())
    console.log('All SWs unregistered')
  })
```

Service Worker полностью опционален! Основной функционал работает без него.

---

### Проблема: localStorage переполнен

**Симптомы:**
- Console warning: "localStorage quota exceeded"
- Новые папки не кешируются

**Решение:**
```javascript
// Очистить folder cache
localStorage.removeItem('folderCache')
localStorage.removeItem('prefetchHistory')

// Проверить размер
let size = 0
for (let key in localStorage) {
  size += localStorage[key].length
}
console.log('localStorage size:', (size / 1024).toFixed(2) + ' KB')

// Перезагрузить
location.reload()
```

---

## Откат изменений

Если нужно вернуться к старой версии:

### Откатить HTTP кеширование
В `__init__.py` изменить:
```python
# Строка 76, 103, 130 - изменить на:
"Cache-Control": "public, max-age=3600"  # Вместо 31536000

# Строка 146, 162, 230 - изменить на:
"Cache-Control": "private, no-cache"  # Вместо max-age=300
```

### Откатить localStorage → sessionStorage
В `src/hooks/folderCache.ts`:
```typescript
// Строка 34 - заменить на:
const stored = sessionStorage.getItem('folderCache')

// Строка 59 - заменить на:
sessionStorage.setItem('folderCache', JSON.stringify(obj))

// Строка 170 - заменить на:
sessionStorage.removeItem('folderCache')
```

### Отключить Service Worker
В `src/main.ts` закомментировать строки 14-23

---

## Полезные команды для debugging

### Проверить все кеши
```javascript
// Browser cache (Service Worker)
caches.keys().then(keys => console.log('SW caches:', keys))

// localStorage
console.log('localStorage keys:', Object.keys(localStorage))

// Session storage
console.log('sessionStorage keys:', Object.keys(sessionStorage))
```

### Мониторинг производительности
```javascript
// Засечь время загрузки папки
performance.mark('start')
// ... открыть папку ...
performance.mark('end')
performance.measure('folder-load', 'start', 'end')
console.log(performance.getEntriesByName('folder-load')[0].duration + 'ms')
```

### Проверить что prefetch работает
```javascript
// В Console после навигации
const queue = window.__prefetchQueue || []
console.log('Prefetch queue:', queue.length)
```

---

## Контакты для поддержки

Если проблема не решается:

1. **GitHub Issues:** https://github.com/anthropics/claude-code/issues
2. **Приложите:**
   - Скриншот ошибки в Console
   - Версия браузера
   - Шаги для воспроизведения

---

## Чек-лист "Все работает"

- [ ] UI загружается
- [ ] Папки открываются быстро
- [ ] Превью изображений отображаются
- [ ] При повторном открытии - мгновенная загрузка
- [ ] Network показывает 304 Not Modified
- [ ] localStorage содержит folderCache
- [ ] Нет красных ошибок в Console

Если все ✅ - оптимизация работает отлично! 🎉
