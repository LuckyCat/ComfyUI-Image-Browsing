<template>
  <ResponseDialog
    v-for="(item, index) in stack"
    v-model:visible="item.visible"
    :key="item.key"
    :keep-alive="item.keepAlive"
    :default-size="item.defaultSize"
    :default-mobile-size="item.defaultMobileSize"
    :resize-allow="item.resizeAllow"
    :min-width="item.minWidth"
    :max-width="item.maxWidth"
    :min-height="item.minHeight"
    :max-height="item.maxHeight"
    :auto-z-index="false"
    :pt:mask:style="{ zIndex: baseZIndex + index + 1 }"
    :pt:root:onMousedown="() => rise(item)"
    @hide="() => close(item)"
  >
    <template #header>
      <div class="flex flex-1 items-center justify-between pr-2">
        <div class="flex items-center gap-2">
          <span class="p-dialog-title select-none">{{ item.title }}</span>
          
          <!-- Cache controls for Output Explorer -->
          <template v-if="item.key === 'output-explorer'">
            <!-- Cache Size Display -->
            <div 
              class="cache-info flex items-center gap-1 text-xs px-2 py-1 rounded bg-gray-800 cursor-pointer select-none"
              @click="toggleCacheMenu"
              v-tooltip.bottom="'Click to configure cache'"
            >
              <i class="pi pi-database text-blue-400"></i>
              <span class="text-gray-300">{{ cacheInfo.size_gb }}GB</span>
              <span class="text-gray-500">/</span>
              <span class="text-gray-400">{{ cacheInfo.max_size_gb }}GB</span>
            </div>
            
            <!-- Cache Controls -->
            <div class="flex items-center gap-1">
              <!-- Start/Resume Button -->
              <Button
                v-if="!cacheStatus.is_running || cacheStatus.is_paused"
                :label="cacheStatus.is_paused ? 'Resume' : 'Cache All'"
                :icon="'pi pi-play'"
                severity="secondary"
                size="small"
                :text="true"
                @click="cacheStatus.is_paused ? resumeCaching() : startCacheAll()"
                v-tooltip.bottom="cacheStatus.is_paused ? 'Resume caching' : 'Cache all thumbnails'"
              />
              
              <!-- Pause Button -->
              <Button
                v-if="cacheStatus.is_running && !cacheStatus.is_paused"
                :label="cacheButtonLabel"
                icon="pi pi-pause"
                severity="secondary"
                size="small"
                :text="true"
                @click="pauseCaching"
                v-tooltip.bottom="cacheTooltip"
              />
              
              <!-- Stop Button -->
              <Button
                v-if="cacheStatus.is_running"
                icon="pi pi-stop"
                severity="danger"
                size="small"
                :text="true"
                :rounded="true"
                @click="stopCaching"
                v-tooltip.bottom="'Stop caching'"
              />
            </div>
          </template>
        </div>

        <!-- Size Selector for Output Explorer -->
        <SizeSelector
          v-if="item.key === 'output-explorer'"
          class="ml-8"
        ></SizeSelector>

        <div class="p-dialog-header-actions">
          <Button
            v-for="action in item.headerButtons"
            :key="action.key"
            severity="secondary"
            :text="true"
            :rounded="true"
            :icon="action.icon"
            @click.stop="action.command"
          ></Button>
        </div>
      </div>
    </template>

    <template #default>
      <component :is="item.content" v-bind="item.contentProps"></component>
    </template>
  </ResponseDialog>
  
  <!-- Cache Settings Menu -->
  <Menu ref="cacheMenuRef" :model="cacheMenuItems" :popup="true" />
  
  <!-- Cache Size Dialog -->
  <Dialog
    v-model:visible="showCacheSizeDialog"
    header="Cache Settings"
    :modal="true"
    :style="{ width: '400px' }"
  >
    <div class="flex flex-col gap-4">
      <div class="flex flex-col gap-2">
        <label class="text-sm text-gray-400">Maximum Cache Size (GB)</label>
        <div class="flex items-center gap-2">
          <Slider
            v-model="newCacheSize"
            :min="1"
            :max="100"
            :step="1"
            class="flex-1"
          />
          <InputNumber
            v-model="newCacheSize"
            :min="1"
            :max="100"
            :suffix="' GB'"
            class="w-24"
          />
        </div>
      </div>
      
      <div class="text-sm text-gray-500">
        Current usage: {{ cacheInfo.size_gb }}GB ({{ cacheInfo.usage_percent }}%)
      </div>
    </div>
    
    <template #footer>
      <div class="flex justify-end gap-2">
        <Button label="Cancel" severity="secondary" @click="showCacheSizeDialog = false" outlined />
        <Button label="Apply" @click="applyCacheSize" />
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import ResponseDialog from 'components/ResponseDialog.vue'
import SizeSelector from 'components/SizeSelector.vue'
import { useDialog } from 'hooks/dialog'
import { request } from 'hooks/request'
import { useToast } from 'hooks/toast'
import { useThumbnailSize, THUMBNAIL_SIZES } from 'hooks/thumbnailSize'
import { useCacheStatus } from 'hooks/cacheStatus'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import Menu from 'primevue/menu'
import Slider from 'primevue/slider'
import Tooltip from 'primevue/tooltip'
import { usePrimeVue } from 'primevue/config'
import { computed, onMounted, onUnmounted, ref } from 'vue'
import type { MenuItem } from 'primevue/menuitem'

const vTooltip = Tooltip

const { stack, rise, close } = useDialog()
const { toast } = useToast()
const { currentSize } = useThumbnailSize()
const { config } = usePrimeVue()
const { _cacheStatus: cacheStatus, _cacheInfo: cacheInfo } = useCacheStatus()

const baseZIndex = computed(() => {
  return config.zIndex?.modal ?? 1100
})

const cacheMenuRef = ref()
const showCacheSizeDialog = ref(false)
const newCacheSize = ref(20)

let pollInterval: number | null = null

const cacheProgress = computed(() => {
  const status = cacheStatus.value

  // Phase 1: Folder structure
  if (status.phase === 'folders') {
    if (status.folders_total === 0) return 0
    return Math.round((status.folders_done / status.folders_total) * 100)
  }

  // Phase 2: Thumbnails
  if (status.total === 0) return 0
  return Math.round((status.processed / status.total) * 100)
})

const cacheButtonLabel = computed(() => {
  const status = cacheStatus.value

  if (status.phase === 'folders') {
    return 'Folders...'
  }
  if (status.auto_paused) {
    return `${cacheProgress.value}% ⏸`
  }
  return `${cacheProgress.value}%`
})

const cacheTooltip = computed(() => {
  const status = cacheStatus.value

  // Phase-specific messages
  if (status.phase === 'folders') {
    return `Phase 1: Caching folder structure... ${status.folders_done}/${status.folders_total} folders`
  }
  if (status.phase === 'folders_done') {
    return `Folders cached. Starting thumbnails...`
  }
  if (status.phase === 'thumbnails') {
    const skippedInfo = status.skipped > 0 ? ` (${status.skipped} cached)` : ''
    const autoPauseInfo = status.auto_paused ? ' [Auto-paused]' : ''
    return `Phase 2: ${status.processed}/${status.total}${skippedInfo}${autoPauseInfo} - ${status.current_file}`
  }

  const skippedInfo = status.skipped > 0 ? ` (${status.skipped} cached)` : ''
  return `${status.processed}/${status.total}${skippedInfo} - ${status.current_file}`
})

const cacheMenuItems = computed<MenuItem[]>(() => [
  {
    label: 'Cache Settings',
    icon: 'pi pi-cog',
    command: () => {
      newCacheSize.value = cacheInfo.value.max_size_gb
      showCacheSizeDialog.value = true
    },
  },
  {
    label: 'Clear Cache',
    icon: 'pi pi-trash',
    command: clearCache,
  },
  {
    separator: true,
  },
  {
    label: `Used: ${cacheInfo.value.size_gb}GB / ${cacheInfo.value.max_size_gb}GB`,
    disabled: true,
  },
])

const toggleCacheMenu = (event: MouseEvent) => {
  cacheMenuRef.value.toggle(event)
}

const pollCacheStatus = async () => {
  try {
    const response = await request('/cache-status')
    
    const wasRunning = cacheStatus.value.is_running
    cacheStatus.value = response
    
    if (response.cache_info) {
      cacheInfo.value = response.cache_info
    }
    
    // Stop polling and show notification when done
    if (wasRunning && !response.is_running && pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null

      if (response.phase === 'done') {
        // Load folder metadata cache for instant navigation
        try {
          const { folderMetadataCache } = await import('hooks/folderMetadataCache')
          await folderMetadataCache.loadAll()
          console.log('[Cache] Folder metadata loaded for instant browsing!')
        } catch (err) {
          console.error('[Cache] Failed to load folder metadata:', err)
        }

        toast.add({
          severity: 'success',
          summary: 'Caching Complete',
          detail: `Processed ${response.total} files (${response.skipped} already cached). All folders cached for instant browsing!`,
          life: 5000,
        })
      }
    }
  } catch (err) {
    console.error('Failed to get cache status:', err)
  }
}

const startCacheAll = async () => {
  try {
    const size = THUMBNAIL_SIZES[currentSize.value]

    // Get current folder from explorer if available
    let priorityFolder: string | null = null
    try {
      // Try to get current path from URL or some global state
      const hashPath = window.location.hash.includes('/output')
        ? decodeURIComponent(window.location.hash.split('/output')[1]?.split('?')[0] || '')
        : null
      if (hashPath) {
        priorityFolder = '/output' + hashPath
      }
    } catch {
      // Ignore
    }

    await request('/cache-all', {
      method: 'POST',
      body: JSON.stringify({
        max_size: size,
        priority_folder: priorityFolder,
        cache_folders: true  // NEW: also cache folder listings
      }),
    })

    toast.add({
      severity: 'info',
      summary: 'Caching Started',
      detail: 'Scanning folders, processing thumbnails, and caching folder listings...',
      life: 3000,
    })

    cacheStatus.value.is_running = true
    cacheStatus.value.is_paused = false
    cacheStatus.value.phase = 'counting'

    if (!pollInterval) {
      pollInterval = window.setInterval(pollCacheStatus, 500)
    }

  } catch (err: any) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: err.message || 'Failed to start caching',
      life: 5000,
    })
  }
}

const pauseCaching = async () => {
  try {
    await request('/cache-pause', { method: 'POST' })
    cacheStatus.value.is_paused = true
    
    toast.add({
      severity: 'info',
      summary: 'Paused',
      detail: 'Caching paused',
      life: 2000,
    })
  } catch (err: any) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: err.message || 'Failed to pause',
      life: 5000,
    })
  }
}

const resumeCaching = async () => {
  try {
    await request('/cache-resume', { method: 'POST' })
    cacheStatus.value.is_paused = false
    
    toast.add({
      severity: 'info',
      summary: 'Resumed',
      detail: 'Caching resumed',
      life: 2000,
    })
  } catch (err: any) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: err.message || 'Failed to resume',
      life: 5000,
    })
  }
}

const stopCaching = async () => {
  try {
    await request('/cache-stop', { method: 'POST' })
    cacheStatus.value.is_running = false
    cacheStatus.value.is_paused = false
    
    if (pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
    }
    
    toast.add({
      severity: 'warn',
      summary: 'Stopped',
      detail: 'Caching stopped',
      life: 2000,
    })
  } catch (err: any) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: err.message || 'Failed to stop',
      life: 5000,
    })
  }
}

const applyCacheSize = async () => {
  try {
    const response = await request('/cache-config', {
      method: 'POST',
      body: JSON.stringify({ max_size_gb: newCacheSize.value }),
    })
    
    if (response) {
      cacheInfo.value = response
    }
    
    toast.add({
      severity: 'success',
      summary: 'Settings Saved',
      detail: `Cache size set to ${newCacheSize.value}GB`,
      life: 3000,
    })
    
    showCacheSizeDialog.value = false
  } catch (err: any) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: err.message || 'Failed to save settings',
      life: 5000,
    })
  }
}

const clearCache = async () => {
  try {
    await request('/cache', { method: 'DELETE' })
    
    toast.add({
      severity: 'success',
      summary: 'Cache Cleared',
      detail: 'All cached thumbnails removed',
      life: 3000,
    })
    
    pollCacheStatus()
  } catch (err: any) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: err.message || 'Failed to clear cache',
      life: 5000,
    })
  }
}

onMounted(() => {
  for (const key in config.zIndex) {
    config.zIndex[key] = baseZIndex.value
  }
  
  pollCacheStatus()
})

onUnmounted(() => {
  if (pollInterval) {
    clearInterval(pollInterval)
  }
})
</script>

<style scoped>
.cache-info:hover {
  background: rgba(55, 65, 81, 0.8);
}
</style>
