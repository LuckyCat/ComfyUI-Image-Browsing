<template>
  <div 
    ref="containerRef"
    :class="[
      'prompt-editor fixed bg-gray-900 rounded-lg shadow-2xl flex flex-col overflow-hidden',
      isMaximized ? 'inset-4' : ''
    ]"
    :style="!isMaximized ? containerStyle : {}"
  >
    <!-- Title bar -->
    <div 
      class="title-bar flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700 cursor-move select-none"
      @mousedown="startDrag"
    >
      <div class="flex items-center gap-2 overflow-hidden">
        <i class="pi pi-file-edit text-green-400"></i>
        <span class="text-sm font-medium truncate">{{ filename }}</span>
        <span v-if="isDirty" class="text-yellow-400 text-xs">●</span>
      </div>
      <div class="flex items-center gap-1">
        <button 
          class="p-1 hover:bg-gray-700 rounded text-gray-400 hover:text-white"
          @click="copyToClipboard"
          title="Copy to clipboard"
        >
          <i class="pi pi-copy text-sm"></i>
        </button>
        <button 
          class="p-1 hover:bg-gray-700 rounded text-gray-400 hover:text-white"
          @click="save"
          :disabled="!isDirty"
          title="Save"
        >
          <i class="pi pi-save text-sm"></i>
        </button>
        <button 
          class="p-1 hover:bg-gray-700 rounded text-gray-400 hover:text-white"
          @click="toggleMaximize"
          :title="isMaximized ? 'Restore' : 'Maximize'"
        >
          <i :class="['pi text-sm', isMaximized ? 'pi-window-minimize' : 'pi-window-maximize']"></i>
        </button>
        <button 
          class="p-1 hover:bg-gray-700 rounded text-gray-400 hover:text-white"
          @click="$emit('close')"
          title="Close"
        >
          <i class="pi pi-times text-sm"></i>
        </button>
      </div>
    </div>

    <!-- Editor -->
    <div class="editor-container flex-1 relative overflow-hidden">
      <!-- Syntax highlighted background -->
      <div 
        ref="highlightRef"
        class="highlight-layer absolute inset-0 p-4 overflow-auto whitespace-pre-wrap break-words font-mono text-sm pointer-events-none"
        v-html="highlightedContent"
      ></div>
      <!-- Transparent textarea for editing -->
      <textarea
        ref="textareaRef"
        v-model="content"
        class="edit-layer absolute inset-0 w-full h-full p-4 bg-transparent text-transparent caret-white font-mono text-sm resize-none outline-none"
        spellcheck="false"
        @scroll="syncScroll"
        @input="onInput"
      ></textarea>
    </div>

    <!-- Status bar -->
    <div class="status-bar flex items-center justify-between px-4 py-1 bg-gray-800 border-t border-gray-700 text-xs text-gray-400">
      <span>{{ lineCount }} lines, {{ content.length }} chars</span>
      <span v-if="lastSaved">Last saved: {{ lastSaved }}</span>
    </div>

    <!-- Resize handles -->
    <div 
      v-if="!isMaximized"
      class="resize-handle resize-e absolute right-0 top-0 bottom-0 w-1 cursor-e-resize"
      @mousedown.stop="startResize('e', $event)"
    ></div>
    <div 
      v-if="!isMaximized"
      class="resize-handle resize-s absolute bottom-0 left-0 right-0 h-1 cursor-s-resize"
      @mousedown.stop="startResize('s', $event)"
    ></div>
    <div 
      v-if="!isMaximized"
      class="resize-handle resize-se absolute bottom-0 right-0 w-3 h-3 cursor-se-resize"
      @mousedown.stop="startResize('se', $event)"
    ></div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { request } from 'hooks/request'
import { useToast } from 'hooks/toast'

const props = defineProps<{
  filepath: string
  filename: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'saved'): void
}>()

const { toast } = useToast()

const containerRef = ref<HTMLElement | null>(null)
const highlightRef = ref<HTMLElement | null>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)

const content = ref('')
const originalContent = ref('')
const loading = ref(true)
const lastSaved = ref('')
const isMaximized = ref(false)

// Window position and size
const position = ref({ x: 100, y: 100 })
const size = ref({ width: 600, height: 400 })

const isDirty = computed(() => content.value !== originalContent.value)
const lineCount = computed(() => content.value.split('\n').length)

const containerStyle = computed(() => ({
  left: `${position.value.x}px`,
  top: `${position.value.y}px`,
  width: `${size.value.width}px`,
  height: `${size.value.height}px`,
}))

// Syntax highlighting
const highlightedContent = computed(() => {
  return highlightSyntax(content.value)
})

function highlightSyntax(text: string): string {
  // Escape HTML
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  // Comments (// to end of line)
  html = html.replace(/(\/\/[^\n]*)/g, '<span class="hl-comment">$1</span>')

  // LoRA tags <lora:name:weight>
  html = html.replace(/(&lt;lora:[^&]*&gt;)/gi, '<span class="hl-lora">$1</span>')

  // Embedding tags <embedding:name>
  html = html.replace(/(&lt;embedding:[^&]*&gt;)/gi, '<span class="hl-embedding">$1</span>')

  // Weights (word:1.2) - numbers after colon
  html = html.replace(/:(\d+\.?\d*)/g, ':<span class="hl-weight">$1</span>')

  // Parentheses and brackets
  html = html.replace(/(\(|\))/g, '<span class="hl-paren">$1</span>')
  html = html.replace(/(\[|\])/g, '<span class="hl-bracket">$1</span>')
  html = html.replace(/(\{|\})/g, '<span class="hl-brace">$1</span>')

  // Wildcards {option1|option2}
  html = html.replace(/\|/g, '<span class="hl-pipe">|</span>')

  // Commas
  html = html.replace(/,/g, '<span class="hl-comma">,</span>')

  return html
}

// Sync scroll between textarea and highlight
const syncScroll = () => {
  if (highlightRef.value && textareaRef.value) {
    highlightRef.value.scrollTop = textareaRef.value.scrollTop
    highlightRef.value.scrollLeft = textareaRef.value.scrollLeft
  }
}

const onInput = () => {
  syncScroll()
}

// Load content
const loadContent = async () => {
  loading.value = true
  try {
    const response = await request(props.filepath)
    content.value = response.content || ''
    originalContent.value = content.value
  } catch (err) {
    content.value = ''
    originalContent.value = ''
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to load file',
      life: 3000,
    })
  } finally {
    loading.value = false
  }
}

// Save content
const save = async () => {
  if (!isDirty.value) return

  try {
    await request(`${props.filepath}/content`, {
      method: 'PUT',
      body: JSON.stringify({ content: content.value }),
    })
    originalContent.value = content.value
    lastSaved.value = new Date().toLocaleTimeString()
    toast.add({
      severity: 'success',
      summary: 'Saved',
      detail: 'File saved successfully',
      life: 2000,
    })
    emit('saved')
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to save file',
      life: 3000,
    })
  }
}

// Copy to clipboard
const copyToClipboard = async () => {
  try {
    await navigator.clipboard.writeText(content.value)
    toast.add({
      severity: 'success',
      summary: 'Copied',
      detail: 'Content copied to clipboard',
      life: 2000,
    })
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to copy to clipboard',
      life: 3000,
    })
  }
}

// Toggle maximize
const toggleMaximize = () => {
  isMaximized.value = !isMaximized.value
}

// Drag handling
let isDragging = false
let dragOffset = { x: 0, y: 0 }

const startDrag = (e: MouseEvent) => {
  if (isMaximized.value) return
  isDragging = true
  dragOffset = {
    x: e.clientX - position.value.x,
    y: e.clientY - position.value.y,
  }
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
}

const onDrag = (e: MouseEvent) => {
  if (!isDragging) return
  position.value = {
    x: Math.max(0, e.clientX - dragOffset.x),
    y: Math.max(0, e.clientY - dragOffset.y),
  }
}

const stopDrag = () => {
  isDragging = false
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
}

// Resize handling
let isResizing = false
let resizeDir = ''
let resizeStart = { x: 0, y: 0, width: 0, height: 0 }

const startResize = (dir: string, e: MouseEvent) => {
  isResizing = true
  resizeDir = dir
  resizeStart = {
    x: e.clientX,
    y: e.clientY,
    width: size.value.width,
    height: size.value.height,
  }
  document.addEventListener('mousemove', onResize)
  document.addEventListener('mouseup', stopResize)
}

const onResize = (e: MouseEvent) => {
  if (!isResizing) return
  
  const dx = e.clientX - resizeStart.x
  const dy = e.clientY - resizeStart.y
  
  if (resizeDir.includes('e')) {
    size.value.width = Math.max(300, resizeStart.width + dx)
  }
  if (resizeDir.includes('s')) {
    size.value.height = Math.max(200, resizeStart.height + dy)
  }
}

const stopResize = () => {
  isResizing = false
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
}

// Keyboard shortcut for save
const handleKeydown = (e: KeyboardEvent) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    e.preventDefault()
    save()
  }
}

onMounted(() => {
  loadContent()
  document.addEventListener('keydown', handleKeydown)
  
  // Center the window
  const viewportWidth = window.innerWidth
  const viewportHeight = window.innerHeight
  position.value = {
    x: Math.max(0, (viewportWidth - size.value.width) / 2),
    y: Math.max(0, (viewportHeight - size.value.height) / 2),
  }
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
})

watch(() => props.filepath, loadContent)
</script>

<style scoped>
.prompt-editor {
  z-index: 5001;
  min-width: 300px;
  min-height: 200px;
}

.editor-container {
  background: #1a1a2e;
}

.highlight-layer,
.edit-layer {
  line-height: 1.5;
  tab-size: 2;
}

.highlight-layer {
  color: #e0e0e0;
}

.resize-handle {
  background: transparent;
}

.resize-handle:hover {
  background: rgba(59, 130, 246, 0.3);
}

/* Syntax highlighting colors */
:deep(.hl-comment) {
  color: #6a9955;
  font-style: italic;
}

:deep(.hl-weight) {
  color: #b5cea8;
  font-weight: bold;
}

:deep(.hl-paren) {
  color: #ffd700;
}

:deep(.hl-bracket) {
  color: #da70d6;
}

:deep(.hl-brace) {
  color: #569cd6;
}

:deep(.hl-pipe) {
  color: #ce9178;
  font-weight: bold;
}

:deep(.hl-comma) {
  color: #808080;
}

:deep(.hl-lora) {
  color: #4ec9b0;
}

:deep(.hl-embedding) {
  color: #c586c0;
}
</style>
