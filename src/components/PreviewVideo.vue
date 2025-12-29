<template>
  <div
    ref="containerRef"
    class="video-viewer relative h-full w-full overflow-hidden bg-black/90 cursor-grab"
    :class="{ 'cursor-grabbing': isDragging }"
    @wheel.prevent="onWheel"
    @mousedown="onMouseDown"
    @mousemove="onMouseMove"
    @mouseup="onMouseUp"
    @mouseleave="onMouseUp"
    @dblclick="resetView"
  >
    <!-- Top-right controls -->
    <div class="absolute right-3 top-3 z-10 flex items-center gap-2">
      <Button
        :icon="autoNextEnabled ? 'pi pi-step-forward' : 'pi pi-step-forward'"
        :severity="autoNextEnabled ? 'info' : 'secondary'"
        text
        rounded
        @click="toggleAutoNext"
        v-tooltip.bottom="autoNextEnabled ? 'Auto-next: ON' : 'Auto-next: OFF'"
      ></Button>

      <Button
        :icon="loopEnabled ? 'pi pi-refresh' : 'pi pi-refresh'"
        :severity="loopEnabled ? 'info' : 'secondary'"
        text
        rounded
        @click="toggleLoop"
        v-tooltip.bottom="loopEnabled ? 'Loop: ON' : 'Loop: OFF'"
      ></Button>

      <Button
        icon="pi pi-times"
        severity="secondary"
        rounded
        @click="onClose"
        v-tooltip.bottom="'Close'"
      ></Button>
    </div>

    <!-- Side navigation -->
    <div class="absolute left-3 top-1/2 z-10 -translate-y-1/2">
      <Button
        icon="pi pi-chevron-left"
        severity="secondary"
        text
        rounded
        @click="onPrev"
        v-tooltip.right="'Previous video (←)'"
      ></Button>
    </div>

    <div class="absolute right-3 top-1/2 z-10 -translate-y-1/2">
      <Button
        icon="pi pi-chevron-right"
        severity="secondary"
        text
        rounded
        @click="onNext"
        v-tooltip.left="'Next video (→)'"
      ></Button>
    </div>

    <!-- Video container with zoom/pan -->
    <div class="flex h-full w-full select-none items-center justify-center">
      <video
        ref="videoRef"
        :key="item.fullname"
        class="absolute select-none"
        :style="videoStyle"
        :src="item.fullname ? `/image-browsing${item.fullname}` : ''"
        autoplay
        controls
        playsinline
        :loop="loopEnabled"
        @ended="onEnded"
        @loadedmetadata="onVideoLoad"
      ></video>
    </div>

    <!-- Bottom controls: Zoom + Frame extraction -->
    <div class="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2 bg-black/60 rounded-lg px-3 py-2 z-10">
      <!-- Zoom controls -->
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
      <Button
        icon="pi pi-refresh"
        severity="secondary"
        :text="true"
        :rounded="true"
        size="small"
        @click="resetView"
        v-tooltip.top="'Reset view (double-click)'"
      />
      
      <div class="w-px h-4 bg-gray-600 mx-1"></div>
      
      <!-- Frame extraction -->
      <Button
        icon="pi pi-camera"
        severity="secondary"
        :text="true"
        :rounded="true"
        size="small"
        @click="extractCurrentFrame"
        :loading="extractingFrame"
        v-tooltip.top="'Extract Current Frame'"
      />
      <Button
        icon="pi pi-step-backward"
        severity="secondary"
        :text="true"
        :rounded="true"
        size="small"
        @click="extractFirstFrame"
        :loading="extractingFirst"
        v-tooltip.top="'Extract First Frame'"
      />
      <Button
        icon="pi pi-step-forward"
        severity="secondary"
        :text="true"
        :rounded="true"
        size="small"
        @click="extractLastFrame"
        :loading="extractingLast"
        v-tooltip.top="'Extract Last Frame'"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import Button from 'primevue/button'
import Tooltip from 'primevue/tooltip'
import { DirectoryItem } from 'types/typings'
import { ref, computed, watch } from 'vue'
import { request } from 'hooks/request'
import { useToast } from 'hooks/toast'

const vTooltip = Tooltip

interface Props {
  item: DirectoryItem
  onClose: () => void
  onNext: () => void
  onPrev: () => void
}

const props = defineProps<Props>()

const { toast } = useToast()

const LS_LOOP = 'comfyui_image_browsing_video_loop'
const LS_AUTONEXT = 'comfyui_image_browsing_video_autonext'

const loopEnabled = ref(localStorage.getItem(LS_LOOP) === '1')
const autoNextEnabled = ref(localStorage.getItem(LS_AUTONEXT) === '1')

watch(loopEnabled, (v) => localStorage.setItem(LS_LOOP, v ? '1' : '0'))
watch(autoNextEnabled, (v) => localStorage.setItem(LS_AUTONEXT, v ? '1' : '0'))

const toggleLoop = () => {
  loopEnabled.value = !loopEnabled.value
}

const toggleAutoNext = () => {
  autoNextEnabled.value = !autoNextEnabled.value
}

const onEnded = () => {
  if (loopEnabled.value) return
  if (!autoNextEnabled.value) return
  props.onNext()
}

// Zoom/Pan state
const containerRef = ref<HTMLElement | null>(null)
const videoRef = ref<HTMLVideoElement | null>(null)

const scale = ref(1)
const translateX = ref(0)
const translateY = ref(0)
const isDragging = ref(false)
const dragStartX = ref(0)
const dragStartY = ref(0)
const lastTranslateX = ref(0)
const lastTranslateY = ref(0)
const videoWidth = ref(0)
const videoHeight = ref(0)

const minScale = 0.1
const maxScale = 10
const zoomStep = 0.25

const videoStyle = computed(() => ({
  transform: `translate(${translateX.value}px, ${translateY.value}px) scale(${scale.value})`,
  transformOrigin: 'center center',
  left: '50%',
  top: '50%',
  marginLeft: `-${videoWidth.value / 2}px`,
  marginTop: `-${videoHeight.value / 2}px`,
}))

const onVideoLoad = () => {
  if (videoRef.value) {
    videoWidth.value = videoRef.value.videoWidth
    videoHeight.value = videoRef.value.videoHeight
    fitToContainer()
  }
}

const fitToContainer = () => {
  if (!containerRef.value || !videoRef.value) return
  
  const container = containerRef.value
  const containerWidth = container.clientWidth
  const containerHeight = container.clientHeight
  
  const padding = 80 // More padding for controls
  const scaleX = (containerWidth - padding * 2) / videoWidth.value
  const scaleY = (containerHeight - padding * 2) / videoHeight.value
  
  scale.value = Math.min(scaleX, scaleY, 1)
  translateX.value = 0
  translateY.value = 0
}

const resetView = () => {
  fitToContainer()
}

const zoomIn = () => {
  scale.value = Math.min(scale.value + zoomStep, maxScale)
}

const zoomOut = () => {
  scale.value = Math.max(scale.value - zoomStep, minScale)
}

const onWheel = (event: WheelEvent) => {
  const delta = event.deltaY > 0 ? -0.1 : 0.1
  const newScale = Math.max(minScale, Math.min(maxScale, scale.value + delta * scale.value))
  
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
  if (event.button !== 0) return
  // Don't start drag if clicking on video controls
  const target = event.target as HTMLElement
  if (target.tagName === 'VIDEO' && event.offsetY > (videoRef.value?.clientHeight ?? 0) - 40) {
    return
  }
  
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

// Reset view when item changes
watch(() => props.item.fullname, () => {
  scale.value = 1
  translateX.value = 0
  translateY.value = 0
})

// Frame extraction
const extractingFrame = ref(false)
const extractingFirst = ref(false)
const extractingLast = ref(false)

const extractCurrentFrame = async () => {
  if (!videoRef.value) return
  
  extractingFrame.value = true
  try {
    const currentTime = videoRef.value.currentTime
    await request('/extract-frame', {
      method: 'POST',
      body: JSON.stringify({
        video_path: props.item.fullname,
        frame_type: 'current',
        timestamp: currentTime,
      }),
    })
    
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: 'Current frame extracted',
      life: 2000,
    })
  } catch (err: any) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: err.message || 'Failed to extract frame',
      life: 3000,
    })
  } finally {
    extractingFrame.value = false
  }
}

const extractFirstFrame = async () => {
  extractingFirst.value = true
  try {
    await request('/extract-frame', {
      method: 'POST',
      body: JSON.stringify({
        video_path: props.item.fullname,
        frame_type: 'first',
      }),
    })
    
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: 'First frame extracted',
      life: 2000,
    })
  } catch (err: any) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: err.message || 'Failed to extract frame',
      life: 3000,
    })
  } finally {
    extractingFirst.value = false
  }
}

const extractLastFrame = async () => {
  extractingLast.value = true
  try {
    await request('/extract-frame', {
      method: 'POST',
      body: JSON.stringify({
        video_path: props.item.fullname,
        frame_type: 'last',
      }),
    })
    
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: 'Last frame extracted',
      life: 2000,
    })
  } catch (err: any) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: err.message || 'Failed to extract frame',
      life: 3000,
    })
  } finally {
    extractingLast.value = false
  }
}
</script>

<style scoped>
.video-viewer {
  user-select: none;
}
</style>
