<template>
  <div
    ref="containerRef"
    class="image-viewer relative h-full w-full overflow-hidden bg-black/90 cursor-grab"
    :class="{ 'cursor-grabbing': isDragging }"
    @wheel.prevent="onWheel"
    @mousedown="onMouseDown"
    @mousemove="onMouseMove"
    @mouseup="onMouseUp"
    @mouseleave="onMouseUp"
    @dblclick="resetView"
  >
    <!-- Loading indicator -->
    <div v-if="isLoading" class="absolute inset-0 flex items-center justify-center">
      <i class="pi pi-spin pi-spinner text-white text-4xl"></i>
    </div>
    
    <img
      ref="imgRef"
      :src="actualSrc"
      :alt="alt"
      class="absolute select-none"
      :class="{ 'opacity-0': isLoading }"
      :style="imageStyle"
      draggable="false"
      @load="onImageLoad"
      @error="onImageError"
    />
    
    <!-- Error state -->
    <div v-if="hasError" class="absolute inset-0 flex items-center justify-center">
      <div class="text-center text-gray-400">
        <i class="pi pi-exclamation-triangle text-4xl mb-2"></i>
        <p>Failed to load image</p>
      </div>
    </div>
    
    <!-- Zoom controls -->
    <div class="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2 bg-black/60 rounded-lg px-3 py-2">
      <Button
        icon="pi pi-minus"
        severity="secondary"
        :text="true"
        :rounded="true"
        size="small"
        @click="zoomOut"
        :disabled="scale <= minScale"
      />
      <span class="text-white text-sm w-16 text-center">{{ Math.round(scale * 100) }}%</span>
      <Button
        icon="pi pi-plus"
        severity="secondary"
        :text="true"
        :rounded="true"
        size="small"
        @click="zoomIn"
        :disabled="scale >= maxScale"
      />
      <div class="w-px h-4 bg-gray-600 mx-1"></div>
      <Button
        icon="pi pi-refresh"
        severity="secondary"
        :text="true"
        :rounded="true"
        size="small"
        @click="resetView"
        v-tooltip.top="'Reset view (double-click)'"
      />
    </div>
    
    <!-- Close button -->
    <Button
      v-if="showClose"
      icon="pi pi-times"
      severity="secondary"
      :text="true"
      :rounded="true"
      class="absolute top-4 right-4"
      @click="$emit('close')"
    />
    
    <!-- Navigation arrows -->
    <Button
      v-if="showNavigation && hasPrev"
      icon="pi pi-chevron-left"
      severity="secondary"
      :text="true"
      :rounded="true"
      class="absolute left-4 top-1/2 -translate-y-1/2"
      @click="$emit('prev')"
    />
    <Button
      v-if="showNavigation && hasNext"
      icon="pi pi-chevron-right"
      severity="secondary"
      :text="true"
      :rounded="true"
      class="absolute right-4 top-1/2 -translate-y-1/2"
      @click="$emit('next')"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import Button from 'primevue/button'
import Tooltip from 'primevue/tooltip'
import { fetchHighPriority } from 'hooks/thumbnailQueue'

const vTooltip = Tooltip

const props = withDefaults(defineProps<{
  src: string
  alt?: string
  showClose?: boolean
  showNavigation?: boolean
  hasPrev?: boolean
  hasNext?: boolean
}>(), {
  alt: '',
  showClose: true,
  showNavigation: false,
  hasPrev: false,
  hasNext: false,
})

// Use blob URL for high-priority loaded images
const blobUrl = ref<string | null>(null)
const actualSrc = computed(() => blobUrl.value || props.src)

/**
 * Load image with high priority, bypassing thumbnail queue
 */
const loadHighPriority = async (url: string) => {
  try {
    const response = await fetchHighPriority(url)
    if (response.ok) {
      const blob = await response.blob()
      // Clean up previous blob
      if (blobUrl.value) {
        URL.revokeObjectURL(blobUrl.value)
      }
      blobUrl.value = URL.createObjectURL(blob)
    }
  } catch (error) {
    // Fallback to normal loading via src attribute
    console.warn('High priority fetch failed, using fallback:', error)
  }
}

onMounted(() => {
  if (props.src) {
    loadHighPriority(props.src)
  }
})

onUnmounted(() => {
  // Clean up blob URL
  if (blobUrl.value) {
    URL.revokeObjectURL(blobUrl.value)
  }
})

defineEmits<{
  (e: 'close'): void
  (e: 'prev'): void
  (e: 'next'): void
}>()

const containerRef = ref<HTMLElement | null>(null)
const imgRef = ref<HTMLImageElement | null>(null)

const scale = ref(1)
const translateX = ref(0)
const translateY = ref(0)
const isDragging = ref(false)
const dragStartX = ref(0)
const dragStartY = ref(0)
const lastTranslateX = ref(0)
const lastTranslateY = ref(0)
const isLoading = ref(true)
const hasError = ref(false)

const minScale = 0.1
const maxScale = 10
const zoomStep = 0.25

const imageStyle = computed(() => ({
  transform: `translate(${translateX.value}px, ${translateY.value}px) scale(${scale.value})`,
  transformOrigin: 'center center',
  left: '50%',
  top: '50%',
  marginLeft: imgRef.value ? `-${imgRef.value.naturalWidth / 2}px` : '0',
  marginTop: imgRef.value ? `-${imgRef.value.naturalHeight / 2}px` : '0',
}))

const onImageLoad = () => {
  isLoading.value = false
  hasError.value = false
  fitToContainer()
}

const onImageError = () => {
  isLoading.value = false
  hasError.value = true
}

const fitToContainer = () => {
  if (!containerRef.value || !imgRef.value) return
  
  const container = containerRef.value
  const img = imgRef.value
  
  const containerWidth = container.clientWidth
  const containerHeight = container.clientHeight
  const imgWidth = img.naturalWidth
  const imgHeight = img.naturalHeight
  
  // Calculate scale to fit image in container with padding
  const padding = 40
  const scaleX = (containerWidth - padding * 2) / imgWidth
  const scaleY = (containerHeight - padding * 2) / imgHeight
  
  scale.value = Math.min(scaleX, scaleY, 1) // Don't scale up beyond 100%
  translateX.value = 0
  translateY.value = 0
}

const resetView = () => {
  fitToContainer()
}

const zoomIn = () => {
  const newScale = Math.min(scale.value + zoomStep, maxScale)
  scale.value = newScale
}

const zoomOut = () => {
  const newScale = Math.max(scale.value - zoomStep, minScale)
  scale.value = newScale
}

const onWheel = (event: WheelEvent) => {
  const delta = event.deltaY > 0 ? -0.1 : 0.1
  const newScale = Math.max(minScale, Math.min(maxScale, scale.value + delta * scale.value))
  
  // Zoom towards cursor position
  if (containerRef.value) {
    const rect = containerRef.value.getBoundingClientRect()
    const cursorX = event.clientX - rect.left - rect.width / 2
    const cursorY = event.clientY - rect.top - rect.height / 2
    
    const scaleDiff = newScale / scale.value
    translateX.value = cursorX - (cursorX - translateX.value) * scaleDiff
    translateY.value = cursorY - (cursorY - translateY.value) * scaleDiff
  }
  
  scale.value = newScale
}

const onMouseDown = (event: MouseEvent) => {
  if (event.button !== 0) return // Only left mouse button
  
  isDragging.value = true
  dragStartX.value = event.clientX
  dragStartY.value = event.clientY
  lastTranslateX.value = translateX.value
  lastTranslateY.value = translateY.value
}

const onMouseMove = (event: MouseEvent) => {
  if (!isDragging.value) return
  
  const deltaX = event.clientX - dragStartX.value
  const deltaY = event.clientY - dragStartY.value
  
  translateX.value = lastTranslateX.value + deltaX
  translateY.value = lastTranslateY.value + deltaY
}

const onMouseUp = () => {
  isDragging.value = false
}

// Reset view and load with high priority when src changes
watch(() => props.src, (newSrc) => {
  // Clean up previous blob
  if (blobUrl.value) {
    URL.revokeObjectURL(blobUrl.value)
    blobUrl.value = null
  }

  isLoading.value = true
  hasError.value = false
  scale.value = 1
  translateX.value = 0
  translateY.value = 0

  // Load new image with high priority
  if (newSrc) {
    loadHighPriority(newSrc)
  }
})
</script>

<style scoped>
.image-viewer {
  user-select: none;
}
</style>
