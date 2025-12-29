<template>
  <div class="folder-tree h-full overflow-auto" @contextmenu.prevent>
    <div class="py-2">
      <!-- Root folders -->
      <template v-for="rootNode in rootNodes" :key="rootNode.fullname">
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
              v-if="rootNode.hasSubfolders !== false"
              :class="[
                'pi text-xs transition-transform duration-200',
                expandedPaths.has(rootNode.fullname) ? 'pi-chevron-down' : 'pi-chevron-right',
              ]"
            ></i>
          </span>
          
          <span class="folder-icon w-4 h-4 flex items-center justify-center">
            <i :class="['pi', expandedPaths.has(rootNode.fullname) ? 'pi-folder-open' : 'pi-folder']" :style="{ color: getRootColor(rootNode.fullname) }"></i>
          </span>
          
          <span class="node-name truncate flex-1">{{ rootNode.name }}</span>
          
          <span v-if="rootNode.fileCount !== undefined && rootNode.fileCount > 0" class="file-count text-xs text-gray-500 ml-1">
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
            :root-type="getRootType(rootNode.fullname)"
            @select="onSelectFolder"
            @toggle="onToggleExpand"
            @contextmenu="onContextMenu"
            @dragover="onDragOver"
            @dragleave="onDragLeave"
            @drop="onDrop"
          />
        </div>
      </template>
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
import type { RootFolderType } from 'types/typings'

const { cacheStatus } = useCacheStatus()

export interface TreeNode {
  name: string
  fullname: string
  children?: TreeNode[]
  loaded?: boolean
  fileCount?: number
  hasSubfolders?: boolean
  rootType?: RootFolderType
}

const FILE_COUNTS_STORAGE_KEY = 'comfyui-image-browsing-folder-counts'
const SUBFOLDER_INFO_STORAGE_KEY = 'comfyui-image-browsing-has-subfolders'

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
  } catch {}
}

const cachedFileCounts = ref<Record<string, number>>(loadCachedCounts())

const loadCachedSubfolders = (): Record<string, boolean> => {
  try {
    const cached = localStorage.getItem(SUBFOLDER_INFO_STORAGE_KEY)
    return cached ? JSON.parse(cached) : {}
  } catch {
    return {}
  }
}

const saveCachedSubfolders = (info: Record<string, boolean>) => {
  try {
    localStorage.setItem(SUBFOLDER_INFO_STORAGE_KEY, JSON.stringify(info))
  } catch {}
}

const cachedHasSubfolders = ref<Record<string, boolean>>(loadCachedSubfolders())

const props = defineProps<{
  selectedPath: string
}>()

const emit = defineEmits<{
  (e: 'select', path: string): void
  (e: 'refresh'): void
  (e: 'moveFiles', files: string[], targetFolder: string): void
}>()

const cachedFolderSet = computed(() => new Set(cacheStatus.value.cached_folders || []))

const { toast, confirm } = useToast()
const { t } = useI18n()

// Three root nodes
const rootNodes = ref<TreeNode[]>([
  { name: 'output', fullname: '/output', children: [], loaded: false, rootType: 'output' },
  { name: 'workflows', fullname: '/workflows', children: [], loaded: false, rootType: 'workflows' },
  { name: 'prompts', fullname: '/prompts', children: [], loaded: false, rootType: 'prompts' },
])

const expandedPaths = ref<Set<string>>(new Set(['/output']))
const contextMenuRef = ref()
const contextMenuItems = ref<MenuItem[]>([])
const contextMenuNode = ref<TreeNode | null>(null)
const confirmName = ref('')
const dragOverPath = ref<string | null>(null)

const vFocus = {
  mounted: (el: HTMLInputElement) => el.focus(),
}

const getRootType = (fullname: string): RootFolderType => {
  if (fullname.startsWith('/output')) return 'output'
  if (fullname.startsWith('/workflows')) return 'workflows'
  if (fullname.startsWith('/prompts')) return 'prompts'
  return 'output'
}

const getRootColor = (fullname: string): string => {
  const type = getRootType(fullname)
  switch (type) {
    case 'output': return '#FFCA28'
    case 'workflows': return '#64B5F6'
    case 'prompts': return '#81C784'
    default: return '#FFCA28'
  }
}

const loadChildren = async (node: TreeNode) => {
  if (node.loaded) return

  try {
    const resData = await request(node.fullname)
    
    const fileCount = resData.filter((item: any) => item.type !== 'folder').length
    node.fileCount = fileCount
    
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
          loaded: false,
          fileCount: cachedFileCounts.value[fullname],
          hasSubfolders: cachedHasSubfolders.value[fullname],
          rootType: node.rootType || getRootType(node.fullname),
        } as TreeNode
      })
      .sort((a: TreeNode, b: TreeNode) => a.name.localeCompare(b.name))
    
    node.hasSubfolders = folders.length > 0
    node.children = folders
    node.loaded = true
    
    if (folders.length > 0) {
      fetchFolderCounts(node.fullname)
    }
  } catch (err) {
    console.error('Failed to load folder:', err)
  }
}

const fetchFolderCounts = async (folderPath: string) => {
  // Only fetch counts for output folder (workflows/prompts don't need thumbnail counts)
  if (!folderPath.startsWith('/output')) return
  
  try {
    const response = await request(`/folder-counts${folderPath}`)
    if (response && typeof response === 'object') {
      const counts = response.counts || response
      const subfolderInfo = response.hasSubfolders || {}
      
      Object.assign(cachedFileCounts.value, counts)
      saveCachedCounts(cachedFileCounts.value)
      
      updateNodeCounts(counts)
      
      if (Object.keys(subfolderInfo).length > 0) {
        Object.assign(cachedHasSubfolders.value, subfolderInfo)
        saveCachedSubfolders(cachedHasSubfolders.value)
        updateNodeHasSubfolders(subfolderInfo)
      }
    }
  } catch (err) {
    console.error('Failed to fetch folder counts:', err)
  }
}

const updateNodeCounts = (counts: Record<string, number>) => {
  const updateNode = (node: TreeNode) => {
    if (counts[node.fullname] !== undefined) {
      node.fileCount = counts[node.fullname]
    }
    if (node.children) {
      for (const child of node.children) {
        updateNode(child)
      }
    }
  }
  
  for (const root of rootNodes.value) {
    updateNode(root)
  }
}

const updateNodeHasSubfolders = (subfolderInfo: Record<string, boolean>) => {
  const updateNode = (node: TreeNode) => {
    if (subfolderInfo[node.fullname] !== undefined) {
      node.hasSubfolders = subfolderInfo[node.fullname]
    }
    if (node.children) {
      for (const child of node.children) {
        updateNode(child)
      }
    }
  }
  
  for (const root of rootNodes.value) {
    updateNode(root)
  }
}

const onSelectFolder = (path: string) => {
  emit('select', path)
}

const onToggleExpand = async (node: TreeNode) => {
  if (expandedPaths.value.has(node.fullname)) {
    expandedPaths.value.delete(node.fullname)
  } else {
    await loadChildren(node)
    expandedPaths.value.add(node.fullname)
  }
  expandedPaths.value = new Set(expandedPaths.value)
}

const findNode = (fullname: string): TreeNode | null => {
  const searchInNode = (node: TreeNode): TreeNode | null => {
    if (node.fullname === fullname) return node
    if (node.children) {
      for (const child of node.children) {
        const found = searchInNode(child)
        if (found) return found
      }
    }
    return null
  }
  
  for (const root of rootNodes.value) {
    const found = searchInNode(root)
    if (found) return found
  }
  return null
}

const findParentNode = (fullname: string): TreeNode | null => {
  const parentPath = fullname.substring(0, fullname.lastIndexOf('/'))
  return findNode(parentPath)
}

const reloadNode = async (node: TreeNode) => {
  node.loaded = false
  node.children = []
  await loadChildren(node)
}

const onContextMenu = (event: MouseEvent, node: TreeNode) => {
  contextMenuNode.value = node
  
  const rootType = getRootType(node.fullname)
  const isRoot = rootNodes.value.some(r => r.fullname === node.fullname)
  
  const items: MenuItem[] = []
  
  // Add folder option (for all types)
  items.push({
    label: t('addFolder'),
    icon: 'pi pi-folder-plus',
    command: () => createFolder(node),
  })
  
  if (!isRoot) {
    items.push({
      label: t('rename'),
      icon: 'pi pi-file-edit',
      command: () => renameFolder(node),
    })
    
    items.push({
      label: t('delete'),
      icon: 'pi pi-trash',
      command: () => deleteFolder(node),
    })
  }
  
  contextMenuItems.value = items
  contextMenuRef.value.show(event)
}

const createFolder = (parentNode: TreeNode) => {
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
  // Only allow drag over for same root type
  const filesJson = event.dataTransfer?.getData('application/json')
  if (filesJson) {
    try {
      const files = JSON.parse(filesJson)
      if (files && files.length > 0) {
        const sourceRoot = getRootType(files[0])
        const targetRoot = getRootType(node.fullname)
        if (sourceRoot !== targetRoot) {
          return // Don't allow cross-root drag
        }
      }
    } catch {}
  }
  
  event.preventDefault()
  event.stopPropagation()
  dragOverPath.value = node.fullname
}

const onDragLeave = () => {
  dragOverPath.value = null
}

const onDrop = async (event: DragEvent, node: TreeNode) => {
  event.preventDefault()
  event.stopPropagation()
  dragOverPath.value = null
  
  const filesJson = event.dataTransfer?.getData('application/json')
  if (!filesJson) return
  
  try {
    const files = JSON.parse(filesJson)
    if (files && files.length > 0) {
      // Validate same root type
      const sourceRoot = getRootType(files[0])
      const targetRoot = getRootType(node.fullname)
      if (sourceRoot !== targetRoot) {
        toast.add({
          severity: 'warn',
          summary: 'Warning',
          detail: `Cannot move files between ${sourceRoot} and ${targetRoot}`,
          life: 3000,
        })
        return
      }
      
      emit('moveFiles', files, node.fullname)
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
      const node = findNode(currentPath)
      if (node) {
        await loadChildren(node)
        expandedPaths.value.add(currentPath)
      }
    }
  }
  expandedPaths.value = new Set(expandedPaths.value)
}, { immediate: true })

onMounted(async () => {
  // Load children for all root nodes
  for (const root of rootNodes.value) {
    await loadChildren(root)
  }
  fetchFolderCounts('/output')
})

watch(() => cacheStatus.value.folder_counts, (newCounts) => {
  if (newCounts && Object.keys(newCounts).length > 0) {
    const virtualCounts: Record<string, number> = {}
    for (const [realPath, count] of Object.entries(newCounts)) {
      const match = realPath.replace(/\\/g, '/').match(/output(.*)$/)
      if (match) {
        const virtualPath = '/output' + match[1]
        virtualCounts[virtualPath] = count
        cachedFileCounts.value[virtualPath] = count
      }
    }
    
    if (Object.keys(virtualCounts).length > 0) {
      updateNodeCounts(virtualCounts)
      saveCachedCounts(cachedFileCounts.value)
    }
  }
}, { deep: true })

const refreshTree = async () => {
  for (const root of rootNodes.value) {
    root.loaded = false
    root.children = []
    await loadChildren(root)
  }
  expandedPaths.value = new Set(['/output'])
  fetchFolderCounts('/output')
}

const refreshNode = async (path: string) => {
  const node = findNode(path)
  if (node) {
    await reloadNode(node)
    if (path.startsWith('/output')) {
      fetchFolderCounts(path)
    }
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
