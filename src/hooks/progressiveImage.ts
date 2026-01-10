/**
 * Progressive image loading
 * Load tiny blur placeholder first, then full image
 * Similar to Medium.com's image loading
 */

import { ref, onMounted, watch } from 'vue'

export interface ProgressiveImageOptions {
  src: string
  placeholderSrc?: string // Low-res preview
  lazy?: boolean // Use Intersection Observer
  rootMargin?: string // For lazy loading
  onLoad?: () => void
  onError?: (error: Error) => void
}

export function useProgressiveImage(options: ProgressiveImageOptions) {
  const {
    src,
    placeholderSrc,
    lazy = true,
    rootMargin = '200px',
    onLoad,
    onError,
  } = options

  const currentSrc = ref<string>(placeholderSrc || '')
  const isLoading = ref(false)
  const isLoaded = ref(false)
  const hasError = ref(false)
  const imgRef = ref<HTMLImageElement | null>(null)

  let observer: IntersectionObserver | null = null

  const loadImage = (imageSrc: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      const img = new Image()

      img.onload = () => {
        currentSrc.value = imageSrc
        isLoaded.value = true
        isLoading.value = false
        onLoad?.()
        resolve()
      }

      img.onerror = () => {
        hasError.value = true
        isLoading.value = false
        const error = new Error(`Failed to load image: ${imageSrc}`)
        onError?.(error)
        reject(error)
      }

      img.src = imageSrc
    })
  }

  const startLoading = async () => {
    if (isLoaded.value || isLoading.value || hasError.value) {
      return
    }

    isLoading.value = true

    try {
      // Load placeholder first (if not already loaded)
      if (placeholderSrc && currentSrc.value !== placeholderSrc) {
        await loadImage(placeholderSrc)
      }

      // Then load full image
      await loadImage(src)
    } catch (error) {
      console.error('Image loading failed:', error)
    }
  }

  const setupIntersectionObserver = () => {
    if (!lazy || !imgRef.value) return

    observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            startLoading()
            observer?.unobserve(entry.target)
          }
        })
      },
      {
        rootMargin,
      }
    )

    observer.observe(imgRef.value)
  }

  onMounted(() => {
    if (lazy) {
      setupIntersectionObserver()
    } else {
      startLoading()
    }
  })

  // Watch src changes
  watch(() => src, (newSrc) => {
    if (newSrc !== currentSrc.value) {
      isLoaded.value = false
      hasError.value = false
      if (!lazy) {
        startLoading()
      }
    }
  })

  return {
    imgRef,
    currentSrc,
    isLoading,
    isLoaded,
    hasError,
    startLoading,
  }
}

/**
 * Multi-resolution progressive loading
 * Loads: tiny blur → thumbnail → full resolution
 */
export function useMultiResImage(
  sources: {
    tiny?: string // Ultra-low res (blur placeholder)
    thumbnail: string // Medium res
    full: string // Full resolution
  },
  lazy = true
) {
  const { tiny, thumbnail, full } = sources

  const currentSrc = ref(tiny || '')
  const currentQuality = ref<'tiny' | 'thumbnail' | 'full'>(tiny ? 'tiny' : 'thumbnail')
  const isLoading = ref(false)
  const imgRef = ref<HTMLImageElement | null>(null)

  const loadNextQuality = async () => {
    if (isLoading.value) return

    isLoading.value = true

    try {
      if (currentQuality.value === 'tiny' && thumbnail) {
        await loadImage(thumbnail)
        currentSrc.value = thumbnail
        currentQuality.value = 'thumbnail'
      }

      if (currentQuality.value === 'thumbnail' && full) {
        await loadImage(full)
        currentSrc.value = full
        currentQuality.value = 'full'
      }
    } finally {
      isLoading.value = false
    }
  }

  const loadImage = (src: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      const img = new Image()
      img.onload = () => resolve()
      img.onerror = () => reject(new Error(`Failed to load: ${src}`))
      img.src = src
    })
  }

  const setupObserver = () => {
    if (!lazy || !imgRef.value) return

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            loadNextQuality()
            observer.unobserve(entry.target)
          }
        })
      },
      { rootMargin: '200px' }
    )

    observer.observe(imgRef.value)
  }

  onMounted(() => {
    if (lazy) {
      setupObserver()
    } else {
      loadNextQuality()
    }
  })

  return {
    imgRef,
    currentSrc,
    currentQuality,
    isLoading,
    loadNextQuality,
  }
}
