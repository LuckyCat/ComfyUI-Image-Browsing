<template>
  <ImageViewer
    :src="item.fullname ? `/image-browsing${item.fullname}` : ''"
    :alt="item.name"
    :show-close="true"
    :show-navigation="true"
    :has-prev="true"
    :has-next="true"
    @close="onClose"
    @prev="onPrev"
    @next="onNext"
  />
</template>

<script setup lang="ts">
import ImageViewer from './ImageViewer.vue'
import { DirectoryItem } from 'types/typings'

interface Props {
  item: DirectoryItem
  onNext: () => void
  onPrev: () => void
  onClose: () => void
}

defineProps<Props>()
</script>
