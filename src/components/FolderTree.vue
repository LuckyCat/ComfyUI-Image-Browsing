<template>
  <div class="folder-tree h-full overflow-auto" @contextmenu.prevent>
    <div class="py-2">
      <!-- Root output folder -->
      <div
        :class="[
          'node-item flex items-center gap-1 cursor-pointer rounded px-2 py-1 mx-1',
          'hover:bg-gray-700',
          'transition-colors duration-150',
          selectedPath === rootNode.fullname ? 'bg-gray-700' : '',
          dragOverPath === rootNode.fullname ? 'bg-blue-600/50 ring-2 ring-blue-400' : '',
        ]"
        style="padding-left: 8px"
        @click="onSelectFolder(rootNode.fullname)"
        @contextmenu.stop.prevent="onContextMenu($event, rootNode)"
        @dragover.prevent="onDragOver($event, rootNode)"
        @dragleave="onDragLeave"
        @drop="onDrop($event, rootNode)"
      >
        <span
          class="expand-icon w-4 h-4 flex items-center justify-center"
          @click.stop="onToggleExpand(rootNode)"
        >
          <i
            :class="[
              'pi text-xs transition-transform duration-200',
              expandedPaths.has(rootNode.fullname) ? 'pi-chevron-down' : 'pi-chevron-right',
            ]"
          ></i>
        </span>
        
        <span class="folder-icon w-4 h-4 flex items-center justify-center">
          <i :class="['pi', expandedPaths.has(rootNode.fullname) ? 'pi-folder-open' : 'pi-folder']" style="color: #FFCA28;"></i>
        </span>
        
        <span class="node-name truncate flex-1">{{ rootNode.name }}</span>
        
        <span v-if="rootNode.fileCount !== undefined" class="file-count text-xs text-gray-500 ml-1">
          {{ rootNode.fileCount }}
        </span>
      </div>
      
      <!-- Child folders -->
      <div v-if="expandedPaths.has(rootNode.fullname) && rootNode.children">
        <FolderTreeNode
          v-for="child in rootNode.children"
          :key="child.fullname"
          :node="child"
          :level="1"
          :expanded-paths="expandedPaths"
          :selected-path="selectedPath"
          :drag-over-path="dragOverPath"
          :cached-folders="cachedFolderSet"
          @select="onSelectFolder"
          @toggle="onToggleExpand"
          @contextmenu="onContextMenu"
          @dragover="onDragOver"
          @dragleave="onDragLeave"
          @drop="onDrop"
        />
      </div>
    </div>
    
    <ContextMenu ref="contextMenuRef" :model="contextMenuItems" />
    
    <ConfirmDialog group="tree-confirm-name">
      <template #container="{ acceptCallback: accept, rejectCallback: reject }">
        <div class="flex w-90 flex-col items-end rounded px-4 pb-4 pt-8">
          <InputText
            class="w-full"
            type="text"
            v-model="confirmName"
            v-focus
            @keyup.enter="accept"
          />
          <div class="mt-6 flex items-center gap-2">
            <Button :label="$t('cancel')" @click="reject" outlined />
            <Button :label="$t('confirm')" @click="accept" />
          </div>
        </div>
      </template>
    </ConfirmDialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { request } from 'hooks/request'
import { useToast } from 'hooks/toast'
import { useCacheStatus } from 'hooks/cacheStatus'
import { useI18n } from 'vue-i18n'
import FolderTreeNode from './FolderTreeNode.vue'
import ContextMenu from 'primevue/contextmenu'
import ConfirmDialog from 'primevue/confirmdialog'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import type { MenuItem } from 'primevue/menuitem'

const { cacheStatus } = useCacheStatus()

export interface TreeNode {
  name: string
  fullname: string
  children?: TreeNode[]
  loaded?: boolean
  fileCount?: number
  hasSubfolders?: boolean  // Whether this folder has subfolders
}

// Local storage for file counts cache
const FILE_COUNTS_STORAGE_KEY = 'comfyui-image-browsing-folder-counts'

const loadCachedCounts = (): Record<string, number> => {
  try {
    const cached = localStorage.getItem(FILE_COUNTS_STORAGE_KEY)
    return cached ? JSON.parse(cached) : {}
  } catch {
    return {}
  }
}

const saveCachedCounts = (counts: Record<string, number>) => {
  try {
    localStorage.setItem(FILE_COUNTS_STORAGE_KEY, JSON.stringify(counts))
  } catch {
    // Ignore storage errors
  }
}

const cachedFileCounts = ref<Record<string, number>>(loadCachedCounts())

const props = defineProps<{
  selectedPath: string
}>()

const emit = defineEmits<{
  (e: 'select', path: string): void
  (e: 'refresh'): void
  (e: 'moveFiles', files: string[], targetFolder: string): void
}>()

// Computed set for fast lookup of cached folders from cache status
const cachedFolderSet = computed(() => new Set(cacheStatus.value.cached_folders || []))

const { toast, confirm } = useToast()
const { t } = useI18n()

const rootNode = ref<TreeNode>({
  name: 'output',
  fullname: '/output',
  children: [],
  loaded: false,
})

const expandedPaths = ref<Set<string>>(new Set(['/output']))
const contextMenuRef = ref()
const contextMenuItems = ref<MenuItem[]>([])
const contextMenuNode = ref<TreeNode | null>(null)
const confirmName = ref('')
const dragOverPath = ref<string | null>(null)

const vFocus = {
  mounted: (el: HTMLInputElement) => el.focus(),
}

const loadChildren = async (node: TreeNode) => {
  if (node.loaded) return

  try {
    const resData = await request(node.fullname)
    
    // Count files (non-folders) in current response
    const fileCount = resData.filter((item: any) => item.type !== 'folder').length
    node.fileCount = fileCount
    
    // Cache this count
    cachedFileCounts.value[node.fullname] = fileCount
    saveCachedCounts(cachedFileCounts.value)
    
    const folders = resData
      .filter((item: any) => item.type === 'folder')
      .map((item: any) => {
        const fullname = `${node.fullname}/${item.name}`
        return {
          name: item.name,
          fullname,
          children: [],
          loaded: false,  // Not loaded yet
          fileCount: cachedFileCounts.value[fullname],  // Use cached count if available
          hasSubfolders: undefined,  // Unknown until loaded or fetched
        } as TreeNode
      })
      .sort((a: TreeNode, b: TreeNode) => a.name.localeCompare(b.name))
    
    // Mark that this node has subfolders
    node.hasSubfolders = folders.length > 0
    
    node.children = folders
    node.loaded = true
    
    // Fetch file counts for subfolders in background
    if (folders.length > 0) {
      fetchFolderCounts(node.fullname)
    }
  } catch (err) {
    console.error('Failed to load folder:', err)
  }
}

const fetchFolderCounts = async (folderPath: string) => {
  try {
    const response = await request(`/folder-counts${folderPath}`)
    if (response && typeof response === 'object') {
      // Handle new format with counts and hasSubfolders
      const counts = response.counts || response
      const subfolderInfo = response.hasSubfolders || {}
      
      // Update counts for all folders and cache them
      Object.assign(cachedFileCounts.value, counts)
      saveCachedCounts(cachedFileCounts.value)
      
      // Update counts in tree nodes
      updateNodeCounts(rootNode.value, counts)
      
      // Update hasSubfolders info
      if (Object.keys(subfolderInfo).length > 0) {
        updateNodeHasSubfolders(rootNode.value, subfolderInfo)
      }
    }
  } catch (err) {
    console.error('Failed to fetch folder counts:', err)
  }
}

const updateNodeCounts = (node: TreeNode, counts: Record<string, number>) => {
  if (counts[node.fullname] !== undefined) {
    node.fileCount = counts[node.fullname]
  }
  
  if (node.children) {
    for (const child of node.children) {
      updateNodeCounts(child, counts)
    }
  }
}

const updateNodeHasSubfolders = (node: TreeNode, subfolderInfo: Record<string, boolean>) => {
  if (subfolderInfo[node.fullname] !== undefined) {
    node.hasSubfolders = subfolderInfo[node.fullname]
  }
  
  if (node.children) {
    for (const child of node.children) {
      updateNodeHasSubfolders(child, subfolderInfo)
    }
  }
}

const reloadNode = async (node: TreeNode) => {
  node.loaded = false
  node.children = []
  await loadChildren(node)
}

const findParentNode = (targetPath: string): TreeNode | null => {
  const parentPath = targetPath.substring(0, targetPath.lastIndexOf('/'))
  if (!parentPath || parentPath === '') return rootNode.value
  return findNode(rootNode.value, parentPath)
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

const onContextMenu = (event: MouseEvent, node: TreeNode) => {
  contextMenuNode.value = node
  
  contextMenuItems.value = [
    {
      label: t('open'),
      icon: 'pi pi-folder-open',
      command: () => {
        emit('select', node.fullname)
      },
    },
    {
      label: t('addFolder'),
      icon: 'pi pi-folder-plus',
      command: () => createSubfolder(node),
    },
    {
      separator: true,
    },
    {
      label: t('rename'),
      icon: 'pi pi-file-edit',
      command: () => renameFolder(node),
    },
    {
      label: t('delete'),
      icon: 'pi pi-trash',
      command: () => deleteFolder(node),
    },
  ]
  
  contextMenuRef.value.show(event)
}

const createSubfolder = (parentNode: TreeNode) => {
  confirmName.value = t('newFolderName')
  
  confirm.require({
    group: 'tree-confirm-name',
    accept: async () => {
      const name = confirmName.value?.trim()
      if (!name) return
      
      try {
        const formData = new FormData()
        formData.append('folders', name)
        
        await request(parentNode.fullname, {
          method: 'POST',
          body: formData,
        })
        
        toast.add({
          severity: 'success',
          summary: 'Success',
          detail: 'Folder created',
          life: 2000,
        })
        
        // Reload parent and expand
        await reloadNode(parentNode)
        expandedPaths.value.add(parentNode.fullname)
        expandedPaths.value = new Set(expandedPaths.value)
        
        emit('refresh')
      } catch (err: any) {
        toast.add({
          severity: 'error',
          summary: 'Error',
          detail: err.message || 'Failed to create folder',
          life: 5000,
        })
      }
    },
  })
}

const renameFolder = (node: TreeNode) => {
  confirmName.value = node.name
  
  confirm.require({
    group: 'tree-confirm-name',
    accept: async () => {
      const newName = confirmName.value?.trim()
      if (!newName || newName === node.name) return
      
      const parentPath = node.fullname.substring(0, node.fullname.lastIndexOf('/'))
      const newFullname = `${parentPath}/${newName}`
      
      try {
        await request(node.fullname, {
          method: 'PUT',
          body: JSON.stringify({ filename: newFullname }),
        })
        
        toast.add({
          severity: 'success',
          summary: 'Success',
          detail: 'Folder renamed',
          life: 2000,
        })
        
        // Reload parent node
        const parentNode = findParentNode(node.fullname)
        if (parentNode) {
          await reloadNode(parentNode)
        }
        
        emit('refresh')
      } catch (err: any) {
        toast.add({
          severity: 'error',
          summary: 'Error',
          detail: err.message || 'Failed to rename folder',
          life: 5000,
        })
      }
    },
  })
}

const deleteFolder = (node: TreeNode) => {
  confirm.require({
    message: t('deleteAsk', [node.name]),
    header: 'Danger',
    icon: 'pi pi-info-circle',
    rejectProps: {
      label: t('cancel'),
      severity: 'secondary',
      outlined: true,
    },
    acceptProps: {
      label: t('delete'),
      severity: 'danger',
    },
    accept: async () => {
      try {
        await request('/delete', {
          method: 'DELETE',
          body: JSON.stringify({
            uri: node.fullname,
            file_list: [node.fullname],
          }),
        })
        
        toast.add({
          severity: 'success',
          summary: 'Success',
          detail: 'Folder deleted',
          life: 2000,
        })
        
        // Reload parent node
        const parentNode = findParentNode(node.fullname)
        if (parentNode) {
          await reloadNode(parentNode)
        }
        
        emit('refresh')
      } catch (err: any) {
        toast.add({
          severity: 'error',
          summary: 'Error',
          detail: err.message || 'Failed to delete folder',
          life: 5000,
        })
      }
    },
  })
}

const onDragOver = (event: DragEvent, node: TreeNode) => {
  event.preventDefault()
  dragOverPath.value = node.fullname
}

const onDragLeave = () => {
  dragOverPath.value = null
}

const onDrop = async (event: DragEvent, node: TreeNode) => {
  event.preventDefault()
  dragOverPath.value = null
  
  // Get dragged files from dataTransfer
  const filesJson = event.dataTransfer?.getData('application/json')
  if (!filesJson) return
  
  try {
    const files = JSON.parse(filesJson)
    if (files && files.length > 0) {
      emit('moveFiles', files, node.fullname)
      
      // Reload target folder
      await reloadNode(node)
    }
  } catch (err) {
    console.error('Failed to parse drop data:', err)
  }
}

// Auto-expand to selected path
watch(() => props.selectedPath, async (newPath) => {
  if (!newPath) return
  
  const parts = newPath.split('/').filter(Boolean)
  let currentPath = ''
  
  for (const part of parts) {
    currentPath += '/' + part
    if (!expandedPaths.value.has(currentPath)) {
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
  // Fetch counts for all visible folders
  fetchFolderCounts('/output')
})

// Watch for folder counts updates from caching process
watch(() => cacheStatus.value.folder_counts, (newCounts) => {
  if (newCounts && Object.keys(newCounts).length > 0) {
    // Convert real paths to virtual paths and update nodes
    const virtualCounts: Record<string, number> = {}
    for (const [realPath, count] of Object.entries(newCounts)) {
      // Extract the path after 'output' folder
      const match = realPath.replace(/\\/g, '/').match(/output(.*)$/)
      if (match) {
        const virtualPath = '/output' + match[1]
        virtualCounts[virtualPath] = count
        // Also cache it
        cachedFileCounts.value[virtualPath] = count
      }
    }
    
    if (Object.keys(virtualCounts).length > 0) {
      updateNodeCounts(rootNode.value, virtualCounts)
      saveCachedCounts(cachedFileCounts.value)
    }
  }
}, { deep: true })

// Expose refresh method
const refreshTree = async () => {
  rootNode.value.loaded = false
  rootNode.value.children = []
  await loadChildren(rootNode.value)
}

const refreshNode = async (path: string) => {
  const node = findNode(rootNode.value, path)
  if (node) {
    await reloadNode(node)
  }
}

defineExpose({ refreshTree, refreshNode })
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
