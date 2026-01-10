import { definePreset } from '@primevue/themes'
import Aura from '@primevue/themes/aura'
import PrimeVue from 'primevue/config'
import ConfirmationService from 'primevue/confirmationservice'
import ToastService from 'primevue/toastservice'
import Tooltip from 'primevue/tooltip'
import { app } from 'scripts/comfyAPI'
import { installGraphDropHandler } from 'scripts/graphDrop'
import { createApp } from 'vue'
import App from './App.vue'
import { i18n } from './i18n'
import './style.css'

// Service Worker для offline-first кеширования (опционально)
// Можно закомментировать если не нужен
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/extensions/ComfyUI-Image-Browsing/sw.js')
      .then(reg => console.log('[SW] Registered:', reg.scope))
      .catch(err => console.warn('[SW] Registration failed:', err))
  })
}

const ComfyUIPreset = definePreset(Aura, {
  semantic: {
    primary: Aura['primitive'].blue,
  },
})

function createVueApp(rootContainer: string | HTMLElement) {
  const app = createApp(App)
  app.directive('tooltip', Tooltip)
  app
    .use(PrimeVue, {
      theme: {
        preset: ComfyUIPreset,
        options: {
          prefix: 'p',
          cssLayer: {
            name: 'primevue',
            order: 'tailwind-base, primevue, tailwind-utilities',
          },
          // This is a workaround for the issue with the dark mode selector
          // https://github.com/primefaces/primevue/issues/5515
          darkModeSelector: '.dark-theme, :root:has(.dark-theme)',
        },
      },
    })
    .use(ToastService)
    .use(ConfirmationService)
    .use(i18n)
    .mount(rootContainer)
}

app.registerExtension({
  name: 'Comfy.ImageBrowsing',
  setup() {
    // Allow dragging items from the explorer onto the ComfyUI graph.
    installGraphDropHandler()

    const container = document.createElement('div')
    container.id = 'comfyui-image-browsing'
    document.body.appendChild(container)

    createVueApp(container)
  },
})
