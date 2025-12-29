<template>
  <div
    v-if="visible"
    class="fixed left-0 top-0 z-[5000] flex h-full w-full items-center justify-center bg-black/40 dark:bg-black/60"
  >
    <PreviewImage
      v-if="current?.type === 'image'"
      :item="current"
      @close="close"
      @prev="openPreviousImage"
      @next="openNextImage"
    ></PreviewImage>

    <PreviewAudio
      v-else-if="current?.type === 'audio'"
      :item="current"
      @close="close"
    ></PreviewAudio>

    <PreviewVideo
      v-else-if="current?.type === 'video'"
      :item="current"
      @close="close"
      @prev="openPreviousVideo"
      @next="openNextVideo"
    ></PreviewVideo>

    <PromptEditor
      v-else-if="current?.type === 'prompt'"
      :filepath="current.fullname"
      :filename="current.name"
      @close="close"
    ></PromptEditor>
  </div>
</template>

<script setup lang="ts">
import { usePreview } from 'hooks/preview'
import PreviewAudio from './PreviewAudio.vue'
import PreviewImage from './PreviewImage.vue'
import PreviewVideo from './PreviewVideo.vue'
import PromptEditor from './PromptEditor.vue'

const {
  visible,
  current,
  close,
  openPreviousImage,
  openNextImage,
  openPreviousVideo,
  openNextVideo,
} = usePreview()
</script>
