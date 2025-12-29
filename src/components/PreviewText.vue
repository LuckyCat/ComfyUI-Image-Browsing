<template>
  <div class="preview-text h-full w-full flex flex-col bg-gray-900 rounded-lg overflow-hidden">
    <div class="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
      <span class="text-sm font-medium truncate">{{ filename }}</span>
      <button 
        class="text-gray-400 hover:text-white"
        @click="$emit('close')"
      >
        <i class="pi pi-times"></i>
      </button>
    </div>
    <div class="flex-1 overflow-auto p-4">
      <div v-if="loading" class="flex items-center justify-center h-full">
        <i class="pi pi-spin pi-spinner text-2xl"></i>
      </div>
      <pre v-else class="text-sm text-gray-300 whitespace-pre-wrap font-mono">{{ content }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { request } from 'hooks/request'

const props = defineProps<{
  filepath: string
  filename: string
}>()

defineEmits<{
  (e: 'close'): void
}>()

const content = ref('')
const loading = ref(true)

const loadContent = async () => {
  loading.value = true
  try {
    const response = await request(props.filepath)
    content.value = response.content || ''
  } catch (err) {
    content.value = 'Error loading file'
  } finally {
    loading.value = false
  }
}

onMounted(loadContent)

watch(() => props.filepath, loadContent)
</script>

<style scoped>
.preview-text pre {
  margin: 0;
  line-height: 1.5;
}
</style>
