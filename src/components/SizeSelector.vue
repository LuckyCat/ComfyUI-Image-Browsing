<template>
  <div class="size-selector">
    <button
      v-for="size in sizes"
      :key="size"
      :class="['size-btn', { active: currentSize === size }]"
      @click="setSize(size)"
    >
      {{ $t(`size.${size}`) }}
    </button>
  </div>
</template>

<script setup lang="ts">
import {
  useThumbnailSize,
  type ThumbnailSizeType,
} from 'hooks/thumbnailSize'

const { currentSize, setSize } = useThumbnailSize()

const sizes: ThumbnailSizeType[] = ['small', 'medium', 'large']
</script>

<style scoped>
.size-selector {
  display: flex;
  align-items: center;
  gap: 4px;
}

.size-btn {
  background: transparent;
  border: 1px solid transparent;
  border-radius: 4px;
  padding: 4px 12px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.15s ease;
  color: var(--p-text-muted-color, #888);
}

.size-btn:hover {
  color: var(--p-text-color, #fff);
  background: var(--p-surface-100, rgba(255, 255, 255, 0.1));
}

.size-btn.active {
  color: var(--p-text-color, #fff);
  background: var(--p-primary-color, #3b82f6);
  border-color: var(--p-primary-color, #3b82f6);
}
</style>
