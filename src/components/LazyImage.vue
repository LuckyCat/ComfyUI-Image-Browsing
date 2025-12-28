<template>
  <div ref="containerRef" class="lazy-image h-full w-full">
    <!-- Placeholder shown while loading -->
    <div 
      v-if="!isLoaded && !hasError" 
      class="h-full w-full flex items-center justify-center bg-gray-800/30"
    >
      <i v-if="isVisible" class="pi pi-spin pi-spinner text-gray-500 text-sm"></i>
    </div>
    
    <!-- Image -->
    <img
      ref="imgRef"
      :class="['h-full w-full object-contain', isLoaded ? 'opacity-100' : 'opacity-0 absolute']"
      :alt="alt"
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
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'

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

let observer: IntersectionObserver | null = null

const loadImage = () => {
  if (imgRef.value && props.src && props.src !== currentSrc.value) {
    currentSrc.value = props.src
    imgRef.value.src = props.src
  }
}

const onLoad = () => {
  isLoaded.value = true
  hasError.value = false
}

const onError = () => {
  hasError.value = true
  isLoaded.value = false
}

onMounted(() => {
  observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          isVisible.value = true
          nextTick(loadImage)
          // Stop observing after becoming visible
          if (observer && containerRef.value) {
            observer.unobserve(containerRef.value)
          }
        }
      })
    },
    {
      rootMargin: '100px',
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
  if (newSrc !== oldSrc && newSrc !== currentSrc.value) {
    isLoaded.value = false
    hasError.value = false
    if (isVisible.value) {
      nextTick(loadImage)
    }
  }
})
</script>

<style scoped>
.lazy-image {
  position: relative;
  overflow: hidden;
}
</style>
