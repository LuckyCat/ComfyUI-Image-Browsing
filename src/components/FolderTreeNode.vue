<template>
  <div class="tree-node">
    <div
      :class="[
        'node-item flex items-center gap-1 cursor-pointer rounded px-2 py-1 mx-1',
        'hover:bg-gray-700',
        isSelected ? 'bg-gray-700' : '',
      ]"
      :style="{ paddingLeft: `${level * 16 + 8}px` }"
      @click="onSelect"
    >
      <span
        class="expand-icon w-4 h-4 flex items-center justify-center"
        @click.stop="onToggle"
      >
        <i
          v-if="hasChildren || !node.loaded"
          :class="[
            'pi text-xs transition-transform duration-200',
            isExpanded ? 'pi-chevron-down' : 'pi-chevron-right',
          ]"
        ></i>
      </span>
      
      <span class="folder-icon w-4 h-4 flex items-center justify-center">
        <i :class="['pi', isExpanded ? 'pi-folder-open' : 'pi-folder']" style="color: #FFCA28;"></i>
      </span>
      
      <span class="node-name truncate flex-1">{{ node.name }}</span>
    </div>
    
    <div v-if="isExpanded && node.children" class="node-children">
      <FolderTreeNode
        v-for="child in node.children"
        :key="child.fullname"
        :node="child"
        :level="level + 1"
        :expanded-paths="expandedPaths"
        :selected-path="selectedPath"
        @select="$emit('select', $event)"
        @toggle="$emit('toggle', $event)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface TreeNode {
  name: string
  fullname: string
  children?: TreeNode[]
  loaded?: boolean
}

const props = defineProps<{
  node: TreeNode
  level: number
  expandedPaths: Set<string>
  selectedPath: string
}>()

const emit = defineEmits<{
  (e: 'select', path: string): void
  (e: 'toggle', node: TreeNode): void
}>()

const isExpanded = computed(() => props.expandedPaths.has(props.node.fullname))
const isSelected = computed(() => props.selectedPath === props.node.fullname)
const hasChildren = computed(() => props.node.children && props.node.children.length > 0)

const onSelect = () => {
  emit('select', props.node.fullname)
}

const onToggle = () => {
  emit('toggle', props.node)
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
