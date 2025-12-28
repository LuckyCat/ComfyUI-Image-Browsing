<template>
  <div class="folder-tree h-full overflow-auto">
    <div class="py-2">
      <FolderTreeNode
        :node="rootNode"
        :level="0"
        :expanded-paths="expandedPaths"
        :selected-path="selectedPath"
        @select="onSelectFolder"
        @toggle="onToggleExpand"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { request } from 'hooks/request'
import FolderTreeNode from './FolderTreeNode.vue'

interface TreeNode {
  name: string
  fullname: string
  children?: TreeNode[]
  loaded?: boolean
}

const props = defineProps<{
  selectedPath: string
}>()

const emit = defineEmits<{
  (e: 'select', path: string): void
}>()

const rootNode = ref<TreeNode>({
  name: 'output',
  fullname: '/output',
  children: [],
  loaded: false,
})

const expandedPaths = ref<Set<string>>(new Set(['/output']))

const loadChildren = async (node: TreeNode) => {
  if (node.loaded) return

  try {
    const resData = await request(node.fullname)
    const folders = resData
      .filter((item: any) => item.type === 'folder')
      .map((item: any) => ({
        name: item.name,
        fullname: `${node.fullname}/${item.name}`,
        children: [],
        loaded: false,
      }))
      .sort((a: TreeNode, b: TreeNode) => a.name.localeCompare(b.name))
    
    node.children = folders
    node.loaded = true
  } catch (err) {
    console.error('Failed to load folder:', err)
  }
}

const onSelectFolder = async (path: string) => {
  emit('select', path)
}

const onToggleExpand = async (node: TreeNode) => {
  const path = node.fullname
  
  if (expandedPaths.value.has(path)) {
    expandedPaths.value.delete(path)
  } else {
    await loadChildren(node)
    expandedPaths.value.add(path)
  }
  expandedPaths.value = new Set(expandedPaths.value)
}

// Auto-expand to selected path
watch(() => props.selectedPath, async (newPath) => {
  if (!newPath) return
  
  const parts = newPath.split('/').filter(Boolean)
  let currentPath = ''
  
  for (const part of parts) {
    currentPath += '/' + part
    if (!expandedPaths.value.has(currentPath)) {
      // Find the node and load its children
      const node = findNode(rootNode.value, currentPath)
      if (node) {
        await loadChildren(node)
        expandedPaths.value.add(currentPath)
      }
    }
  }
  expandedPaths.value = new Set(expandedPaths.value)
}, { immediate: true })

const findNode = (node: TreeNode, path: string): TreeNode | null => {
  if (node.fullname === path) return node
  
  if (node.children) {
    for (const child of node.children) {
      const found = findNode(child, path)
      if (found) return found
    }
  }
  
  return null
}

onMounted(async () => {
  await loadChildren(rootNode.value)
})

// Expose refresh method
const refreshTree = async () => {
  rootNode.value.loaded = false
  rootNode.value.children = []
  await loadChildren(rootNode.value)
}

defineExpose({ refreshTree })
</script>

<style scoped>
.folder-tree {
  font-size: 13px;
}

.folder-tree::-webkit-scrollbar {
  width: 6px;
}

.folder-tree::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 3px;
}

.folder-tree::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}
</style>
