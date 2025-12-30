import { 
  request, 
  invalidateCache, 
  invalidateCachePrefix, 
  prefetchFolders, 
  getCachedData, 
  revalidateInBackground,
  optimisticRemove,
  cancelRequest,
} from 'hooks/request'
import { defineStore } from 'hooks/store'
import { useToast } from 'hooks/toast'
import { MenuItem } from 'primevue/menuitem'
import { app } from 'scripts/comfyAPI'
import { DirectoryItem, SelectOptions, RootFolderType } from 'types/typings'
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

interface DirectoryBreadcrumb extends DirectoryItem {
  children: SelectOptions[]
}

// Helper to get root type from path
const getRootType = (path: string): RootFolderType => {
  if (path.startsWith('/workflows')) return 'workflows'
  if (path.startsWith('/prompts')) return 'prompts'
  return 'output'
}

// Helper to get root directory for a type
const getRootDirectory = (type: RootFolderType): DirectoryBreadcrumb => ({
  name: type,
  type: 'folder',
  size: 0,
  fullname: `/${type}`,
  createdAt: 0,
  updatedAt: 0,
  children: [],
})

export const useExplorer = defineStore('explorer', (store) => {
  const { toast, confirm } = useToast()
  const { t } = useI18n()

  const loading = ref(false)
  const currentRootType = ref<RootFolderType>('output')

  const rootDirectory: DirectoryBreadcrumb = getRootDirectory('output')

  const breadcrumb = ref<DirectoryBreadcrumb[]>([rootDirectory])
  const currentPath = computed(() => {
    return breadcrumb.value[breadcrumb.value.length - 1].fullname
  })

  const items = ref<DirectoryItem[]>([])
  const menuRef = ref()
  const contextItems = ref<MenuItem[]>([])
  const selectedItems = ref<DirectoryItem[]>([])
  const currentSelected = ref<DirectoryItem>()

  const entryFolder = async (item: DirectoryItem, breadcrumbIndex: number) => {
    if (breadcrumbIndex === breadcrumb.value.length - 1) {
      const lastItem = breadcrumb.value[breadcrumbIndex]
      if (item.fullname === lastItem.fullname) {
        return
      }
    }

    breadcrumb.value.splice(breadcrumbIndex)
    breadcrumb.value.push({ ...item, children: [] })
    await refresh()
  }

  const goBackParentFolder = async () => {
    breadcrumb.value.pop()
    await refresh()
  }

  const confirmName = ref<string | undefined>(undefined)

  const assertValidName = (name: string) => {
    if (items.value.some((c) => c.name == name)) {
      const message = 'Name was existed.'
      toast.add({
        severity: 'warn',
        summary: 'Warning',
        detail: message,
        life: 2000,
      })
      throw new Error(message)
    }

    if (name.endsWith(' ') || name.endsWith('.')) {
      const message = 'Name cannot end with space or period.'
      toast.add({
        severity: 'warn',
        summary: 'Warning',
        detail: message,
        life: 2000,
      })
      throw new Error(message)
    }

    const windowsInvalidChars = /[<>:"/\\|?*]/
    const linuxInvalidChars = /[/\0]/

    if (windowsInvalidChars.test(name) || linuxInvalidChars.test(name)) {
      const message = 'Name contains illegal characters: <>:"/\\|?*'
      toast.add({
        severity: 'warn',
        summary: 'Warning',
        detail: message,
        life: 2000,
      })
      throw new Error(message)
    }

    const windowsReservedNames = /^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$/i
    if (windowsReservedNames.test(name.split('.')[0])) {
      const message = 'Name cannot be reserved name.'
      toast.add({
        severity: 'warn',
        summary: 'Warning',
        detail: message,
        life: 2000,
      })
      throw new Error(message)
    }
  }

  const createItems = (formData: FormData) => {
    loading.value = true
    request(currentPath.value, {
      method: 'POST',
      body: formData,
    })
      .then(() => {
        return forceRefresh()
      })
      .catch((err) => {
        toast.add({
          severity: 'error',
          summary: 'Error',
          detail: err.message || 'Failed to upload files.',
          life: 5000,
        })
      })
      .finally(() => {
        loading.value = false
      })
  }

  const deleteItems = () => {
    // Check if there are items to delete
    if (selectedItems.value.length === 0) {
      toast.add({
        severity: 'warn',
        summary: 'Warning',
        detail: 'No items selected to delete.',
        life: 2000,
      })
      return
    }
    
    const handleDelete = () => {
      // Optimistic update - remove from UI immediately
      const deletedNames = selectedItems.value.map(item => item.name)
      const deletedFullnames = selectedItems.value.map(item => item.fullname)
      
      // Remove from current items immediately (optimistic)
      items.value = items.value.filter(item => !deletedFullnames.includes(item.fullname))
      
      // Also update cache optimistically
      deletedNames.forEach(name => optimisticRemove(currentPath.value, name))
      
      // Clear selection
      const previousSelected = [...selectedItems.value]
      selectedItems.value = []
      currentSelected.value = undefined
      
      request(`/delete`, {
        method: 'DELETE',
        body: JSON.stringify({
          uri: currentPath.value,
          file_list: deletedFullnames,
        }),
      })
        .then(() => {
          toast.add({
            severity: 'success',
            summary: 'Success',
            detail: 'Deleted successfully.',
            life: 2000,
          })
          // Invalidate cache for deleted folders
          previousSelected.forEach(item => {
            if (item.type === 'folder') {
              invalidateCachePrefix(item.fullname)
            }
          })
          // Force refresh to sync with server
          return forceRefresh()
        })
        .catch((err) => {
          toast.add({
            severity: 'error',
            summary: 'Error',
            detail: err.message || 'Failed to delete.',
            life: 15000,
          })
          // Rollback optimistic update on error
          forceRefresh()
        })
    }

    if (store.config.showDeleteConfirm.value) {
      confirm.require({
        message: t('deleteAsk', [t('selectedItems').toLowerCase()]),
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
        accept: handleDelete,
        reject: () => {},
      })
    } else {
      handleDelete()
    }
  }


  const formatTimestamp = () => {
    const d = new Date()
    const pad = (n: number) => String(n).padStart(2, '0')
    return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`
  }

  const mergeSelectedVideos = () => {
    const selectedVideos = selectedItems.value.filter((c) => c.type === 'video')

    if (selectedItems.value.length < 2 || selectedVideos.length !== selectedItems.value.length) {
      toast.add({
        severity: 'warn',
        summary: 'Warning',
        detail: 'Select 2+ videos to merge.',
        life: 3000,
      })
      return
    }

    const defaultName = `merged_${formatTimestamp()}.mp4`
    confirmName.value = defaultName

    toast.add({
      severity: 'info',
      summary: 'Merge videos',
      detail: 'Enter output filename and press Confirm.',
      life: 3000,
    })

    confirm.require({
      group: 'confirm-name',
      accept: () => {
        const name = (confirmName.value?.trim() || defaultName).trim()
        if (name === '') return

        assertValidName(name)

        const orderedVideos = items.value.filter((it) =>
          selectedVideos.some((s) => s.fullname === it.fullname),
        )

        loading.value = true
        request('/merge-videos', {
          method: 'POST',
          body: JSON.stringify({
            file_list: orderedVideos.map((c) => c.fullname),
            output_name: name,
          }),
        })
          .then(() => {
            toast.add({
              severity: 'success',
              summary: 'Success',
              detail: 'Merged video created.',
              life: 3000,
            })
            return forceRefresh()
          })
          .catch((err) => {
            toast.add({
              severity: 'error',
              summary: 'Error',
              detail: err.message || 'Failed to merge videos.',
              life: 15000,
            })
          })
          .finally(() => {
            loading.value = false
          })
      },
      reject: () => {},
    })
  }

  const openWorkflow = async (item: DirectoryItem) => {
    try {
      // Fetch the image file
      const response = await fetch(`/image-browsing${item.fullname}`)
      const blob = await response.blob()
      
      // Create a File object and use ComfyUI's handleFile method
      const file = new File([blob], item.name, { type: blob.type })
      app.handleFile(file)
      
      toast.add({
        severity: 'success',
        summary: 'Workflow Loading',
        detail: 'Attempting to load workflow from image...',
        life: 3000,
      })
    } catch (err: any) {
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: err.message || 'Failed to load workflow',
        life: 5000,
      })
    }
  }

  const openWorkflowFile = async (item: DirectoryItem) => {
    try {
      // Fetch the workflow JSON file
      const response = await fetch(`/image-browsing${item.fullname}`)
      const blob = await response.blob()
      
      // Create a File object and use ComfyUI's handleFile method
      const file = new File([blob], item.name, { type: 'application/json' })
      app.handleFile(file)
      
      toast.add({
        severity: 'success',
        summary: 'Workflow Loading',
        detail: 'Loading workflow...',
        life: 2000,
      })
    } catch (err: any) {
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: err.message || 'Failed to load workflow',
        life: 5000,
      })
    }
  }

  const duplicateWorkflow = async (item: DirectoryItem) => {
    loading.value = true
    try {
      await request('/duplicate-workflow', {
        method: 'POST',
        body: JSON.stringify({
          file_path: item.fullname,
        }),
      })
      
      toast.add({
        severity: 'success',
        summary: 'Success',
        detail: 'Workflow duplicated.',
        life: 2000,
      })
      
      await refresh()
    } catch (err: any) {
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: err.message || 'Failed to duplicate workflow.',
        life: 5000,
      })
    } finally {
      loading.value = false
    }
  }

  const extractVideoFrame = async (item: DirectoryItem, frameType: 'first' | 'last') => {
    loading.value = true
    try {
      await request('/extract-frame', {
        method: 'POST',
        body: JSON.stringify({
          video_path: item.fullname,
          frame_type: frameType,
        }),
      })
      
      toast.add({
        severity: 'success',
        summary: 'Success',
        detail: `Extracted ${frameType} frame successfully.`,
        life: 3000,
      })
      
      await refresh()
    } catch (err: any) {
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: err.message || `Failed to extract ${frameType} frame.`,
        life: 5000,
      })
    } finally {
      loading.value = false
    }
  }

  const reverseVideo = async (item: DirectoryItem) => {
    loading.value = true
    try {
      const result = await request('/reverse-video', {
        method: 'POST',
        body: JSON.stringify({
          video_path: item.fullname,
        }),
      })
      
      toast.add({
        severity: 'success',
        summary: 'Success',
        detail: `Reversed video created: ${result.output}`,
        life: 3000,
      })
      
      await forceRefresh()
    } catch (err: any) {
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: err.message || 'Failed to reverse video.',
        life: 5000,
      })
    } finally {
      loading.value = false
    }
  }

  const refreshThumbnail = async (item: DirectoryItem) => {
    loading.value = true
    try {
      await request('/refresh-thumbnail', {
        method: 'POST',
        body: JSON.stringify({
          file_path: item.fullname,
        }),
      })
      
      toast.add({
        severity: 'success',
        summary: 'Success',
        detail: 'Thumbnail regenerated',
        life: 2000,
      })
      
      // Force reload the thumbnail by adding a cache-busting param
      // This will be handled by the LazyImage component
      await forceRefresh()
    } catch (err: any) {
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: err.message || 'Failed to refresh thumbnail',
        life: 5000,
      })
    } finally {
      loading.value = false
    }
  }

  const copyLoadNode = async (item: DirectoryItem, type: 'image' | 'video') => {
    loading.value = true
    try {
      const result = await request('/copy-to-input', {
        method: 'POST',
        body: JSON.stringify({
          file_path: item.fullname,
          type: type,
        }),
      })
      
      // Create ComfyUI node data for clipboard
      const nodeData = result.nodeData
      
      // Copy to clipboard
      await navigator.clipboard.writeText(JSON.stringify(nodeData))
      
      toast.add({
        severity: 'success',
        summary: 'Success',
        detail: `${type === 'image' ? 'LoadImage' : 'LoadVideo'} node copied to clipboard. File copied to input folder.`,
        life: 3000,
      })
    } catch (err: any) {
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: err.message || 'Failed to copy node',
        life: 5000,
      })
    } finally {
      loading.value = false
    }
  }

  const renameItem = (item: DirectoryItem) => {
    confirmName.value = item.name

    confirm.require({
      group: 'confirm-name',
      accept: () => {
        const name = confirmName.value?.trim() ?? ''
        const filename = `${currentPath.value}/${name}`

        // If name is empty or same as current name, do nothing
        if (name === '' || name === item.name) {
          return
        }

        assertValidName(name)

        request(item.fullname, {
          method: 'PUT',
          body: JSON.stringify({
            filename: filename,
          }),
        })
          .then(() => {
            item.name = name
            item.fullname = filename
          })
          .catch((err) => {
            toast.add({
              severity: 'error',
              summary: 'Error',
              detail: err.message || 'Failed to load folder list.',
              life: 5000,
            })
          })
      },
    })
  }

  const bindEvents = (item: DirectoryItem, index: number) => {
    item.onClick = ($event) => {
      menuRef.value.hide($event)

      const isSelected = selectedItems.value.some((c) => c.name === item.name)

      if ($event.shiftKey) {
        const startIndex = Math.max(
          items.value.findIndex((c) => c.name === currentSelected.value?.name),
          0,
        )
        const endIndex = index
        const rangeItems = items.value.slice(
          Math.min(startIndex, endIndex),
          Math.max(startIndex, endIndex) + 1,
        )
        selectedItems.value = rangeItems
        return
      }

      currentSelected.value = item

      if ($event.ctrlKey) {
        selectedItems.value = isSelected
          ? selectedItems.value.filter((c) => c.name !== item.name)
          : [...selectedItems.value, item]
      } else {
        selectedItems.value = [item]
      }
    }

    item.onDbClick = () => {
      if (item.type === 'folder') {
        entryFolder(item, breadcrumb.value.length)
      } else if (item.type === 'workflow') {
        // Open workflow in ComfyUI
        openWorkflowFile(item)
      } else if (item.type === 'prompt') {
        // Open text preview
        store.preview.open(item)
      } else {
        store.preview.open(item)
      }
    }

    item.onContextMenu = ($event) => {
      const isSelected = selectedItems.value.some((c) => c.name === item.name)

      if (!isSelected) {
        selectedItems.value = [item]
        currentSelected.value = item
      }

      const contextMenu: MenuItem[] = []
      const rootType = getRootType(item.fullname)

      if (item.type === 'folder') {
        contextMenu.push({
          label: t('open'),
          icon: 'pi pi-folder',
          command: () => {
            item.onDbClick?.($event)
          },
        })
      } else if (item.type === 'workflow') {
        // Workflow context menu
        contextMenu.push(
          {
            label: t('openWorkflow'),
            icon: 'pi pi-play',
            command: () => openWorkflowFile(item),
          },
          {
            label: t('duplicate'),
            icon: 'pi pi-copy',
            command: () => duplicateWorkflow(item),
          },
        )
      } else if (item.type === 'prompt') {
        // Prompt context menu
        contextMenu.push({
          label: t('open'),
          icon: 'pi pi-file-edit',
          command: () => {
            item.onDbClick?.($event)
          },
        })
      } else {
        // Media file context menu (images, videos, audio)
        contextMenu.push(
          {
            label: t('open'),
            icon: 'pi pi-image',
            command: () => {
              item.onDbClick?.($event)
            },
          },
          {
            label: t('openInNewTab'),
            icon: 'pi pi-external-link',
            command: () => {
              window.open(`/image-browsing${item.fullname}`, '_blank')
            },
          },
          {
            label: t('openWorkflow'),
            icon: 'pi pi-sitemap',
            command: () => {
              openWorkflow(item)
            },
          },
          {
            label: t('save'),
            icon: 'pi pi-save',
            command: () => {
              const link = document.createElement('a')
              link.href = `/image-browsing${item.fullname}`
              link.download = item.name
              link.click()
            },
          },
        )
        
        // Copy LoadImage/LoadVideo to clipboard (for ComfyUI workflow)
        if (item.type === 'image') {
          contextMenu.push({
            label: 'Copy LoadImage',
            icon: 'pi pi-copy',
            command: () => copyLoadNode(item, 'image'),
          })
        }
        if (item.type === 'video') {
          contextMenu.push({
            label: 'Copy LoadVideo',
            icon: 'pi pi-copy',
            command: () => copyLoadNode(item, 'video'),
          })
        }
        
        // Refresh thumbnail
        contextMenu.push({
          label: t('refreshThumbnail'),
          icon: 'pi pi-refresh',
          command: () => refreshThumbnail(item),
        })
      }

      // Video-specific options: Extract First/Last Frame, Reverse
      if (item.type === 'video') {
        contextMenu.push(
          {
            label: t('extractFirstFrame'),
            icon: 'pi pi-step-backward',
            command: () => extractVideoFrame(item, 'first'),
          },
          {
            label: t('extractLastFrame'),
            icon: 'pi pi-step-forward',
            command: () => extractVideoFrame(item, 'last'),
          },
          {
            label: 'Reverse Video',
            icon: 'pi pi-replay',
            command: () => reverseVideo(item),
          },
        )
      }

      const canMergeVideos =
        selectedItems.value.length >= 2 &&
        selectedItems.value.every((c) => c.type === 'video')

      if (canMergeVideos) {
        contextMenu.push({
          label: 'Merge videos',
          icon: 'pi pi-clone',
          command: mergeSelectedVideos,
        })
      }

      // Rename option for all types
      contextMenu.push({
        label: t('rename'),
        icon: 'pi pi-file-edit',
        command: () => {
          renameItem(item)
        },
      })

      // Delete option for all types
      contextMenu.push({
        label: t('delete'),
        icon: 'pi pi-trash',
        command: deleteItems,
      })

      // Download/Archive only for output folder (media files)
      if (rootType === 'output' && (selectedItems.value.length > 1 || item.type === 'folder')) {
        contextMenu.push({
          label: t('download'),
          icon: 'pi pi-download',
          command: () => {
            loading.value = true
            request('/archive', {
              method: 'POST',
              body: JSON.stringify({
                uri: currentPath.value,
                file_list: selectedItems.value.map((c) => c.fullname),
              }),
            })
              .then((tmp_name) => {
                const link = document.createElement('a')
                link.href = `/image-browsing/archive/${tmp_name}`
                link.download = tmp_name
                link.click()
              })
              .catch((err) => {
                toast.add({
                  severity: 'error',
                  summary: 'Error',
                  detail: err.message || 'Failed to download.',
                  life: 15000,
                })
              })
              .finally(() => {
                loading.value = false
              })
          },
        })
      }

      contextItems.value = contextMenu
      menuRef.value.show($event)
    }

    item.onDragEnd = ($event) => {
      const target = document.elementFromPoint($event.clientX, $event.clientY)

      if (
        target?.tagName.toLocaleLowerCase() === 'canvas' &&
        target.id === 'graph-canvas'
      ) {
        const imageSource = `/image-browsing${item.fullname}`
        fetch(imageSource)
          .then((response) => response.blob())
          .then((data) => {
            const type = data.type
            const file = new File([data], item.name, { type })
            app.handleFile(file)
          })
      }
    }
  }

  const createNewPrompt = async () => {
    loading.value = true
    try {
      await request('/create-prompt', {
        method: 'POST',
        body: JSON.stringify({
          folder_path: currentPath.value,
          filename: 'New Prompt.txt',
        }),
      })
      
      toast.add({
        severity: 'success',
        summary: 'Success',
        detail: 'New prompt created.',
        life: 2000,
      })
      
      await refresh()
    } catch (err: any) {
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: err.message || 'Failed to create prompt.',
        life: 5000,
      })
    } finally {
      loading.value = false
    }
  }

  const folderContext = ($event: MouseEvent) => {
    selectedItems.value = []
    const rootType = getRootType(currentPath.value)
    const contextMenu: MenuItem[] = []
    
    // Add folder option (for all types)
    contextMenu.push({
      label: t('addFolder'),
      icon: 'pi pi-folder-plus',
      command: () => {
        confirmName.value = t('newFolderName')

        confirm.require({
          group: 'confirm-name',
          accept: () => {
            const name = confirmName.value ?? ''
            assertValidName(name)
            const formData = new FormData()
            formData.append('folders', name)
            createItems(formData)
          },
        })
      },
    })
    
    // Upload file option (only for output)
    if (rootType === 'output') {
      contextMenu.push({
        label: t('uploadFile'),
        icon: 'pi pi-upload',
        command: () => {
          const fileInput = document.createElement('input')
          fileInput.type = 'file'
          fileInput.multiple = true
          fileInput.accept = 'image/*,audio/*,video/*'
          fileInput.onchange = (e) => {
            const files = (e.target as HTMLInputElement).files
            if (!files) {
              return
            }
            const formData = new FormData()
            for (let i = 0; i < files.length; i++) {
              formData.append('files', files[i])
            }
            createItems(formData)
          }
          fileInput.click()
        },
      })
    }
    
    // New prompt option (only for prompts)
    if (rootType === 'prompts') {
      contextMenu.push({
        label: 'New Prompt',
        icon: 'pi pi-file-edit',
        command: createNewPrompt,
      })
    }

    contextItems.value = contextMenu
    menuRef.value.show($event)
  }

  /**
   * Process response data and update UI
   */
  const processData = (resData: any[]) => {
    const folders: DirectoryItem[] = []
    const files: DirectoryItem[] = []
    for (const item of resData) {
      item.fullname = `${currentPath.value}/${item.name}`
      if (item.type === 'folder') {
        folders.push(item)
      } else {
        files.push(item)
      }
    }
    folders.sort((a, b) => a.name.localeCompare(b.name))
    files.sort((a, b) => a.name.localeCompare(b.name))
    items.value = [...folders, ...files]
    items.value.forEach(bindEvents)
    breadcrumb.value[breadcrumb.value.length - 1].children = folders.map(
      (item) => {
        const folderLevel = breadcrumb.value.length
        return {
          label: item.name,
          value: item.fullname,
          command: () => {
            entryFolder(item, folderLevel)
          },
        }
      },
    )
    
    // Prefetch subfolders in background for instant navigation
    if (folders.length > 0 && folders.length <= 20) {
      const folderPaths = folders.map(f => f.fullname)
      prefetchFolders(folderPaths)
    }
  }

  // Track current navigation to prevent race conditions
  let currentNavigationId = 0

  /**
   * Refresh with cache-first strategy:
   * 1. If cached: show instantly, revalidate in background
   * 2. If not cached: show loading, fetch from server
   * 3. Cancel previous request if navigating quickly
   */
  const refresh = async () => {
    // Increment navigation ID to invalidate previous requests
    const navigationId = ++currentNavigationId
    
    selectedItems.value = []
    currentSelected.value = undefined
    
    // Try to get from cache first (instant)
    const cachedData = getCachedData<any[]>(currentPath.value)
    
    if (cachedData) {
      // INSTANT: Show cached data immediately
      processData(cachedData)
      loading.value = false
      
      // Revalidate in background (stale-while-revalidate)
      revalidateInBackground(currentPath.value)
      return
    }
    
    // Not cached - need to fetch from network
    loading.value = true
    items.value = []
    
    // Cancel any previous navigation request
    cancelRequest('navigation')
    
    try {
      const resData = await request(currentPath.value)
      
      // Check if this navigation is still current
      if (navigationId !== currentNavigationId) {
        return // Newer navigation started, ignore this result
      }
      
      processData(resData)
    } catch (err: any) {
      // Ignore abort errors (from cancelled requests)
      if (err.name === 'AbortError') return
      
      // Check if this navigation is still current
      if (navigationId !== currentNavigationId) return
      
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: err.message || 'Failed to load folder list.',
        life: 15000,
      })
    } finally {
      // Only hide loading if this is still the current navigation
      if (navigationId === currentNavigationId) {
        loading.value = false
      }
    }
  }

  /**
   * Force refresh - always fetch from network (after mutations)
   */
  const forceRefresh = async () => {
    const navigationId = ++currentNavigationId
    
    loading.value = true
    items.value = []
    selectedItems.value = []
    currentSelected.value = undefined
    
    // Invalidate cache first
    invalidateCache(currentPath.value)
    
    try {
      const resData = await request(currentPath.value)
      
      if (navigationId !== currentNavigationId) return
      
      processData(resData)
    } catch (err: any) {
      if (err.name === 'AbortError') return
      if (navigationId !== currentNavigationId) return
      
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: err.message || 'Failed to load folder list.',
        life: 15000,
      })
    } finally {
      if (navigationId === currentNavigationId) {
        loading.value = false
      }
    }
  }

  const clearStatus = () => {
    selectedItems.value = []
    currentSelected.value = undefined
  }

  const navigateToPath = async (path: string) => {
    // Parse the path and build breadcrumb
    const parts = path.split('/').filter(Boolean)
    
    // Determine root type from path
    const rootType = getRootType(path)
    currentRootType.value = rootType
    const newRootDirectory = getRootDirectory(rootType)
    
    // Reset to appropriate root
    breadcrumb.value = [newRootDirectory]
    
    // Build path step by step
    let currentFullPath = ''
    for (const part of parts) {
      currentFullPath += '/' + part
      // Skip root folder itself
      if (currentFullPath === `/${rootType}`) continue
      
      breadcrumb.value.push({
        name: part,
        type: 'folder',
        size: 0,
        fullname: currentFullPath,
        createdAt: 0,
        updatedAt: 0,
        children: [],
      })
    }
    
    await refresh()
  }

  return {
    loading: loading,
    items: items,
    breadcrumb: breadcrumb,
    menuRef: menuRef,
    contextItems: contextItems,
    selectedItems: selectedItems,
    confirmName: confirmName,
    currentRootType: currentRootType,
    refresh: refresh,
    forceRefresh: forceRefresh,
    deleteItems: deleteItems,
    renameItem: renameItem,
    entryFolder: entryFolder,
    folderContext: folderContext,
    goBackParentFolder: goBackParentFolder,
    clearStatus: clearStatus,
    navigateToPath: navigateToPath,
  }
})

declare module 'hooks/store' {
  interface StoreProvider {
    explorer: ReturnType<typeof useExplorer>
  }
}
