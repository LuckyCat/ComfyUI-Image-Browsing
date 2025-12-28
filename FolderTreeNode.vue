<template>
  <div class="tree-node">
    <div
      :class="[
        'node-item flex items-center gap-1 cursor-pointer rounded px-2 py-1 mx-1',
        'hover:bg-gray-700',
        'transition-colors duration-150',
        isSelected ? 'bg-gray-700' : '',
        isDragOver ? 'bg-blue-600/50 ring-2 ring-blue-400' : '',
      ]"
      :style="{ paddingLeft: `${level * 16 + 8}px` }"
      @click="onSelect"
      @contextmenu.stop.prevent="onContextMenu"
      @dragover.prevent="onDragOver"
      @dragleave="onDragLeave"
      @drop="onDrop"
    >
      <span
        class="expand-icon w-4 h-4 flex items-center justify-center"
        @click.stop="onToggle"
      >
        <i
          v-if="showExpandIcon"
          :class="[
            'pi text-xs transition-transform duration-200',
            isExpanded ? 'pi-chevron-down' : 'pi-chevron-right',
          ]"
        ></i>
      </span>
      
      <span class="folder-icon w-4 h-4 flex items-center justify-center">
        <i 
          :class="['pi', isExpanded ? 'pi-folder-open' : 'pi-folder']" 
          :style="{ color: '#FFCA28' }"
        ></i>
      </span>
      
      <span class="node-name truncate flex-1">{{ node.name }}</span>
      
      <span 
        v-if="node.fileCount !== undefined && node.fileCount > 0" 
        class="file-count text-xs ml-1 text-blue-400 opacity-70"
      >
        {{ node.fileCount }}
      </span>
    </div>
    
    <div v-if="isExpanded && node.children" class="node-children">
      <FolderTreeNode
        v-for="child in node.children"
        :key="child.fullname"
        :node="child"
        :level="level + 1"
        :expanded-paths="expandedPaths"
        :selected-path="selectedPath"
        :drag-over-path="dragOverPath"
        :cached-folders="cachedFolders"
        @select="$emit('select', $event)"
        @toggle="$emit('toggle', $event)"
        @contextmenu="(e, n) => $emit('contextmenu', e, n)"
        @dragover="(e, n) => $emit('dragover', e, n)"
        @dragleave="$emit('dragleave')"
        @drop="(e, n) => $emit('drop', e, n)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TreeNode } from './FolderTree.vue'

const props = defineProps<{
  node: TreeNode
  level: number
  expandedPaths: Set<string>
  selectedPath: string
  dragOverPath: string | null
  cachedFolders?: Set<string>
}>()

const emit = defineEmits<{
  (e: 'select', path: string): void
  (e: 'toggle', node: TreeNode): void
  (e: 'contextmenu', event: MouseEvent, node: TreeNode): void
  (e: 'dragover', event: DragEvent, node: TreeNode): void
  (e: 'dragleave'): void
  (e: 'drop', event: DragEvent, node: TreeNode): void
}>()

const isExpanded = computed(() => props.expandedPaths.has(props.node.fullname))
const isSelected = computed(() => props.selectedPath === props.node.fullname)
const hasChildren = computed(() => props.node.children && props.node.children.length > 0)
const isDragOver = computed(() => props.dragOverPath === props.node.fullname)

// Folder icons are always yellow (cache state should not affect appearance)

// Show expand icon only if:
// 1. Node has children (loaded and has subfolders), OR
// 2. Node has hasSubfolders explicitly set to true, OR
// 3. Node is not loaded yet (we don't know if it has subfolders)
const showExpandIcon = computed(() => {
  if (hasChildren.value) return true
  if (props.node.hasSubfolders === true) return true
  if (props.node.hasSubfolders === false) return false
  // Not loaded yet - show icon so user can try to expand
  if (!props.node.loaded) return true
  return false
})

const onSelect = () => {
  emit('select', props.node.fullname)
}

const onToggle = () => {
  emit('toggle', props.node)
}

const onContextMenu = (event: MouseEvent) => {
  emit('contextmenu', event, props.node)
}

const onDragOver = (event: DragEvent) => {
  emit('dragover', event, props.node)
}

const onDragLeave = () => {
  emit('dragleave')
}

const onDrop = (event: DragEvent) => {
  emit('drop', event, props.node)
}
</script>

<style scoped>
.node-item {
  user-select: none;
  white-space: nowrap;
}

.node-name {
  font-size: 13px;
}

.expand-icon {
  flex-shrink: 0;
}

.folder-icon {
  flex-shrink: 0;
}
</style>
