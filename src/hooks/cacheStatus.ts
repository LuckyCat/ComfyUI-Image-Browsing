import { ref, readonly } from 'vue'

// Shared reactive state for cache status
const cacheStatus = ref({
  is_running: false,
  is_paused: false,
  auto_paused: false,  // Automatically paused due to user activity
  phase: '',  // 'folders', 'folders_done', 'thumbnails', 'done'
  total: 0,
  processed: 0,
  skipped: 0,
  current_file: '',
  errors: 0,
  folder_counts: {} as Record<string, number>,
  cached_folders: [] as string[],
  folders_total: 0,
  folders_done: 0,
})

const cacheInfo = ref({
  size_bytes: 0,
  size_mb: 0,
  size_gb: 0,
  max_size_gb: 20,
  usage_percent: 0,
})

// Simple set to track which URLs have been loaded in browser
const browserCachedUrls = new Set<string>()

const markAsCached = (url: string) => {
  browserCachedUrls.add(url)
}

const isImageCached = (url: string): boolean => {
  return browserCachedUrls.has(url)
}

const getCachedImageCount = (): number => {
  return browserCachedUrls.size
}

export function useCacheStatus() {
  const updateStatus = (status: Partial<typeof cacheStatus.value>) => {
    Object.assign(cacheStatus.value, status)
  }
  
  const updateInfo = (info: Partial<typeof cacheInfo.value>) => {
    Object.assign(cacheInfo.value, info)
  }
  
  return {
    cacheStatus: readonly(cacheStatus),
    cacheInfo: readonly(cacheInfo),
    updateStatus,
    updateInfo,
    // Direct refs for mutation
    _cacheStatus: cacheStatus,
    _cacheInfo: cacheInfo,
    // Simple cache tracking
    markAsCached,
    isImageCached,
    getCachedImageCount,
  }
}
