<template>
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

  <div class="flex h-full w-full select-none items-center justify-center">
    <video
      :key="item.fullname"
      class="h-full w-full object-contain"
      :src="item.fullname ? `/image-browsing${item.fullname}` : ''"
      autoplay
      controls
      playsinline
      :loop="loopEnabled"
      @ended="onEnded"
    ></video>
  </div>
</template>

<script setup lang="ts">
import Button from 'primevue/button'
import { DirectoryItem } from 'types/typings'
import { ref, watch } from 'vue'

interface Props {
  item: DirectoryItem
  onClose: () => void
  onNext: () => void
  onPrev: () => void
}

const props = defineProps<Props>()

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
  // If loop is ON, the browser restarts playback; don't advance.
  if (loopEnabled.value) return
  if (!autoNextEnabled.value) return
  // Advance to the next video in the folder (videos-only navigation)
  props.onNext()
}
</script>
