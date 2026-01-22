import { defineStore } from 'hooks/store'
import { DirectoryItem } from 'types/typings'
import { computed, ref } from 'vue'
import { signalUserActivity, cancelThumbnails } from 'hooks/thumbnailQueue'

export const usePreview = defineStore('preview', (store) => {
  const visible = ref(false)
  const current = ref<DirectoryItem>()
  const currentIndex = ref(0)

  const previewItems = computed(() => {
    // Used for image navigation (images + videos)
    return store.explorer.items.value.filter((item) => {
      return item.type === 'image' || item.type === 'video'
    })
  })

  const videoItems = computed(() => {
    // Used for video navigation (videos only)
    return store.explorer.items.value.filter((item) => item.type === 'video')
  })

  const promptItems = computed(() => {
    // Used for prompt navigation
    return store.explorer.items.value.filter((item) => item.type === 'prompt')
  })

  const openPreviousImage = () => {
    if (previewItems.value.length === 0) return
    currentIndex.value--
    if (currentIndex.value < 0) {
      currentIndex.value = previewItems.value.length - 1
    }
    const item = previewItems.value[currentIndex.value]
    current.value = item
  }

  const openNextImage = () => {
    if (previewItems.value.length === 0) return
    currentIndex.value++
    if (currentIndex.value > previewItems.value.length - 1) {
      currentIndex.value = 0
    }
    const item = previewItems.value[currentIndex.value]
    current.value = item
  }

  const openPreviousVideo = () => {
    if (videoItems.value.length === 0) return
    const cur = current.value
    if (!cur || cur.type !== 'video') return

    const vidIndex = videoItems.value.findIndex((v) => v.fullname === cur.fullname)
    const prevIndex = vidIndex <= 0 ? videoItems.value.length - 1 : vidIndex - 1
    const item = videoItems.value[prevIndex]
    current.value = item
    currentIndex.value = previewItems.value.indexOf(item)
  }

  const openNextVideo = () => {
    if (videoItems.value.length === 0) return
    const cur = current.value
    if (!cur || cur.type !== 'video') return

    const vidIndex = videoItems.value.findIndex((v) => v.fullname === cur.fullname)
    const nextIndex = vidIndex >= videoItems.value.length - 1 ? 0 : vidIndex + 1
    const item = videoItems.value[nextIndex]
    current.value = item
    currentIndex.value = previewItems.value.indexOf(item)
  }

  const openPreviousPrompt = () => {
    if (promptItems.value.length === 0) return
    const cur = current.value
    if (!cur || cur.type !== 'prompt') return

    const idx = promptItems.value.findIndex((v) => v.fullname === cur.fullname)
    const prevIndex = idx <= 0 ? promptItems.value.length - 1 : idx - 1
    current.value = promptItems.value[prevIndex]
  }

  const openNextPrompt = () => {
    if (promptItems.value.length === 0) return
    const cur = current.value
    if (!cur || cur.type !== 'prompt') return

    const idx = promptItems.value.findIndex((v) => v.fullname === cur.fullname)
    const nextIndex = idx >= promptItems.value.length - 1 ? 0 : idx + 1
    current.value = promptItems.value[nextIndex]
  }

  const previewKeyboardListener = (event: KeyboardEvent) => {
    if (event.key === 'Escape') {
      close()
    }

    if (current.value?.type === 'image') {
      if (event.key === 'ArrowLeft') {
        openPreviousImage()
      }
      if (event.key === 'ArrowRight') {
        openNextImage()
      }
    }

    if (current.value?.type === 'video') {
      if (event.key === 'ArrowLeft') {
        openPreviousVideo()
      }
      if (event.key === 'ArrowRight') {
        openNextVideo()
      }
    }

    if (current.value?.type === 'prompt') {
      if (event.key === 'ArrowLeft') {
        openPreviousPrompt()
      }
      if (event.key === 'ArrowRight') {
        openNextPrompt()
      }
    }
  }

  const open = (item: DirectoryItem) => {
    // Cancel ALL pending thumbnails and pause queue - preview takes absolute priority
    cancelThumbnails()
    signalUserActivity()

    visible.value = true
    current.value = item
    if (item.type === 'image' || item.type === 'video') {
      currentIndex.value = previewItems.value.indexOf(item)
    }
    document.addEventListener('keyup', previewKeyboardListener)
  }

  const close = () => {
    document.removeEventListener('keyup', previewKeyboardListener)
    visible.value = false
  }

  return {
    visible,
    current,
    open,
    close,
    openPreviousImage,
    openNextImage,
    openPreviousVideo,
    openNextVideo,
    openPreviousPrompt,
    openNextPrompt,
  }
})

declare module 'hooks/store' {
  interface StoreProvider {
    preview: ReturnType<typeof usePreview>
  }
}
