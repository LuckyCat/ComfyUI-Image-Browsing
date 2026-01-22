<template>
  <div ref="containerRef" class="lazy-image h-full w-full">
    <!-- Placeholder shown while loading (only if not already cached) -->
    <div 
      v-if="!isLoaded && !hasError && !isCached" 
      class="h-full w-full flex items-center justify-center bg-gray-800/30"
    >
      <i v-if="isVisible" class="pi pi-spin pi-spinner text-gray-500 text-sm"></i>
    </div>
    
    <!-- Image with smooth transition -->
    <img
      ref="imgRef"
      :class="[
        'h-full w-full object-contain',
        // Skip transition if already cached for instant display
        isCached ? '' : 'transition-opacity duration-150',
        (isLoaded || isCached) ? 'opacity-100' : 'opacity-0 absolute'
      ]"
      :alt="alt"
      decoding="async"
      @load="onLoad"
      @error="onError"
    />
    
    <!-- Error state -->
    <div v-if="hasError" class="h-full w-full flex items-center justify-center bg-gray-800/30">
      <i class="pi pi-image text-gray-500"></i>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'

// Global cache to track loaded images - survives component unmount/remount
const loadedImagesCache = new Set<string>()

// Limit cache size to prevent memory issues
const MAX_CACHE_SIZE = 1000

const addToCache = (src: string) => {
  if (loadedImagesCache.size >= MAX_CACHE_SIZE) {
    // Remove oldest entries (first 200)
    const entries = Array.from(loadedImagesCache)
    entries.slice(0, 200).forEach(e => loadedImagesCache.delete(e))
  }
  loadedImagesCache.add(src)
}

const props = defineProps<{
  src: string
  alt?: string
}>()

const containerRef = ref<HTMLElement | null>(null)
const imgRef = ref<HTMLImageElement | null>(null)
const isVisible = ref(false)
const isLoaded = ref(false)
const hasError = ref(false)
const currentSrc = ref('')

// Check if this image was already loaded before (cached in browser)
const isCached = computed(() => loadedImagesCache.has(props.src))

let observer: IntersectionObserver | null = null

const loadImage = () => {
  if (!imgRef.value || !props.src) return

  // If already loaded or same src, skip
  if (props.src === currentSrc.value && isLoaded.value) return

  currentSrc.value = props.src

  // Simply set the src - browser will handle caching naturally
  imgRef.value.src = props.src
}

const onLoad = () => {
  isLoaded.value = true
  hasError.value = false
  // Add to global cache so remounted components know it's loaded
  addToCache(props.src)
}

const onError = () => {
  hasError.value = true
  isLoaded.value = false
}

onMounted(() => {
  // If image is already cached, load immediately without waiting for intersection
  if (isCached.value) {
    isVisible.value = true
    isLoaded.value = true // Assume it will load from browser cache
    if (imgRef.value) {
      imgRef.value.src = props.src
      currentSrc.value = props.src
    }
    return
  }

  observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          isVisible.value = true
          loadImage()
          // Stop observing after becoming visible
          if (observer && containerRef.value) {
            observer.unobserve(containerRef.value)
          }
        }
      })
    },
    {
      // Load images when close to viewport
      rootMargin: '200px',
      threshold: 0,
    }
  )

  if (containerRef.value) {
    observer.observe(containerRef.value)
  }
})

onUnmounted(() => {
  if (observer) {
    observer.disconnect()
  }
})

// Handle src changes
watch(() => props.src, (newSrc, oldSrc) => {
  if (newSrc !== oldSrc) {
    // Check if new image is already in cache
    if (loadedImagesCache.has(newSrc)) {
      isLoaded.value = true
      hasError.value = false
      if (imgRef.value) {
        imgRef.value.src = newSrc
        currentSrc.value = newSrc
      }
    } else {
      isLoaded.value = false
      hasError.value = false
      if (isVisible.value) {
        loadImage()
      }
    }
  }
})
</script>

<style scoped>
.lazy-image {
  position: relative;
  overflow: hidden;
  /* Contain layout to prevent reflows */
  contain: layout style;
}

.lazy-image img {
  /* Prevent layout shifts */
  backface-visibility: hidden;
}
</style>
