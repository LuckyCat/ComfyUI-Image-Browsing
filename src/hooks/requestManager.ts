/**
 * Advanced request manager with batching, deduplication, and cancellation
 * Inspired by best practices from Google Drive, Dropbox, VS Code
 */

import { api } from 'scripts/comfyAPI'
import { folderCache } from 'hooks/folderCache'

// ============================================================================
// Request Deduplication
// ============================================================================

// Track in-flight requests to prevent duplicates
const inFlightRequests = new Map<string, Promise<any>>()

/**
 * Deduplicated request - if same request is already in-flight, return that promise
 */
export const deduplicatedRequest = async <T>(
  url: string,
  fetcher: () => Promise<T>
): Promise<T> => {
  // Check if request is already in-flight
  const existing = inFlightRequests.get(url)
  if (existing) {
    return existing as Promise<T>
  }

  // Create new request
  const promise = fetcher().finally(() => {
    inFlightRequests.delete(url)
  })

  inFlightRequests.set(url, promise)
  return promise
}

// ============================================================================
// Request Cancellation (AbortController)
// ============================================================================

// Track AbortControllers for cancellable requests
const abortControllers = new Map<string, AbortController>()

/**
 * Create a cancellable request - cancels previous request with same key
 */
export const cancellableRequest = async <T>(
  key: string,
  url: string,
  options?: RequestInit
): Promise<T> => {
  // Cancel previous request with same key
  const existing = abortControllers.get(key)
  if (existing) {
    existing.abort()
  }

  // Create new AbortController
  const controller = new AbortController()
  abortControllers.set(key, controller)

  try {
    const response = await api.fetchApi(`/image-browsing${url}`, {
      ...options,
      signal: controller.signal,
    })

    const data = await response.json()
    
    if (data.success) {
      return data.data
    }
    throw new Error(data.error)
  } finally {
    // Cleanup if this controller is still active
    if (abortControllers.get(key) === controller) {
      abortControllers.delete(key)
    }
  }
}

/**
 * Cancel a request by key
 */
export const cancelRequest = (key: string): void => {
  const controller = abortControllers.get(key)
  if (controller) {
    controller.abort()
    abortControllers.delete(key)
  }
}

// ============================================================================
// Batch Requests
// ============================================================================

interface BatchedRequest {
  path: string
  resolve: (data: any) => void
  reject: (error: any) => void
}

let batchQueue: BatchedRequest[] = []
let batchTimeout: ReturnType<typeof setTimeout> | null = null
const BATCH_DELAY = 10 // ms to wait before sending batch

/**
 * Add request to batch queue - requests are grouped and sent together
 */
export const batchedFolderRequest = (path: string): Promise<any> => {
  return new Promise((resolve, reject) => {
    batchQueue.push({ path, resolve, reject })

    // Schedule batch send
    if (!batchTimeout) {
      batchTimeout = setTimeout(sendBatch, BATCH_DELAY)
    }
  })
}

/**
 * Send all queued requests as a single batch
 */
const sendBatch = async () => {
  const batch = [...batchQueue]
  batchQueue = []
  batchTimeout = null

  if (batch.length === 0) return

  // Single request - no need to batch
  if (batch.length === 1) {
    const { path, resolve, reject } = batch[0]
    try {
      const response = await api.fetchApi(`/image-browsing${path}`)
      const data = await response.json()
      if (data.success) {
        // Cache the result
        const etag = response.headers.get('ETag') || ''
        if (etag) {
          folderCache.set(path, data.data, etag)
        }
        resolve(data.data)
      } else {
        reject(new Error(data.error))
      }
    } catch (err) {
      reject(err)
    }
    return
  }

  // Multiple requests - send as batch
  try {
    const paths = batch.map(b => b.path)
    const response = await api.fetchApi('/image-browsing/batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ paths }),
    })

    const data = await response.json()

    if (data.success) {
      // Resolve each request with its data
      for (const { path, resolve, reject } of batch) {
        const result = data.data[path]
        if (result !== undefined) {
          // Cache each result
          if (result.etag) {
            folderCache.set(path, result.data, result.etag)
          }
          resolve(result.data || result)
        } else {
          reject(new Error(`No data for path: ${path}`))
        }
      }
    } else {
      // Reject all
      for (const { reject } of batch) {
        reject(new Error(data.error))
      }
    }
  } catch (err) {
    // Reject all on error
    for (const { reject } of batch) {
      reject(err)
    }
  }
}

// ============================================================================
// Prefetch Queue with Priority
// ============================================================================

interface PrefetchItem {
  path: string
  priority: number // lower = higher priority
}

let prefetchQueue: PrefetchItem[] = []
let isPrefetching = false
const MAX_CONCURRENT_PREFETCH = 6  // Increased from 3 for aggressive prefetching
let activePrefetches = 0

/**
 * Add paths to prefetch queue with priority
 * Priority 0 = immediate (visible folders)
 * Priority 1 = soon (siblings)
 * Priority 2 = later (deeper folders)
 */
export const queuePrefetch = (paths: string[], priority: number = 1): void => {
  for (const path of paths) {
    // Skip if already cached or in queue
    if (folderCache.has(path)) continue
    if (prefetchQueue.some(item => item.path === path)) continue

    prefetchQueue.push({ path, priority })
  }

  // Sort by priority
  prefetchQueue.sort((a, b) => a.priority - b.priority)

  // Start processing if not already
  processPrefetchQueue()
}

const processPrefetchQueue = async (): Promise<void> => {
  if (isPrefetching || prefetchQueue.length === 0) return
  if (activePrefetches >= MAX_CONCURRENT_PREFETCH) return

  isPrefetching = true

  while (prefetchQueue.length > 0 && activePrefetches < MAX_CONCURRENT_PREFETCH) {
    const item = prefetchQueue.shift()
    if (!item) break

    // Skip if already cached (might have been cached while waiting)
    if (folderCache.has(item.path)) continue

    activePrefetches++

    // Fire and forget
    fetchAndCache(item.path)
      .catch(() => {}) // Ignore prefetch errors
      .finally(() => {
        activePrefetches--
        // Continue processing queue
        if (prefetchQueue.length > 0) {
          processPrefetchQueue()
        }
      })
  }

  isPrefetching = false
}

const fetchAndCache = async (path: string): Promise<void> => {
  const response = await api.fetchApi(`/image-browsing${path}`)
  const data = await response.json()

  if (data.success) {
    const etag = response.headers.get('ETag') || ''
    if (etag) {
      folderCache.set(path, data.data, etag)
    }
  }
}

// ============================================================================
// Navigation Debounce
// ============================================================================

let navigationDebounceTimer: ReturnType<typeof setTimeout> | null = null
let lastNavigationPath: string | null = null

/**
 * Debounced navigation - prevents rapid folder switching from flooding requests
 * Returns true if navigation should proceed, false if debounced
 */
export const debounceNavigation = (
  path: string,
  callback: () => void,
  delay: number = 50
): boolean => {
  // Same path - ignore
  if (path === lastNavigationPath) return false

  // Clear previous timer
  if (navigationDebounceTimer) {
    clearTimeout(navigationDebounceTimer)
  }

  lastNavigationPath = path

  // If cached, execute immediately (instant feel)
  if (folderCache.has(path)) {
    callback()
    return true
  }

  // Not cached - debounce to prevent rapid switching
  navigationDebounceTimer = setTimeout(() => {
    callback()
    navigationDebounceTimer = null
  }, delay)

  return true
}

/**
 * Clear navigation debounce (e.g., on component unmount)
 */
export const clearNavigationDebounce = (): void => {
  if (navigationDebounceTimer) {
    clearTimeout(navigationDebounceTimer)
    navigationDebounceTimer = null
  }
  lastNavigationPath = null
}

// ============================================================================
// Optimistic Updates
// ============================================================================

/**
 * Optimistically add item to cache before server confirms
 */
export const optimisticAdd = (folderPath: string, newItem: any): void => {
  const cached = folderCache.getData<any[]>(folderPath)
  if (cached) {
    // Add to cached data
    const updated = [...cached, newItem]
    folderCache.set(folderPath, updated, '') // Empty etag - will revalidate
  }
}

/**
 * Optimistically remove item from cache before server confirms
 */
export const optimisticRemove = (folderPath: string, itemName: string): void => {
  const cached = folderCache.getData<any[]>(folderPath)
  if (cached) {
    const updated = cached.filter(item => item.name !== itemName)
    folderCache.set(folderPath, updated, '') // Empty etag - will revalidate
  }
}

/**
 * Optimistically rename item in cache before server confirms
 */
export const optimisticRename = (
  folderPath: string,
  oldName: string,
  newName: string
): void => {
  const cached = folderCache.getData<any[]>(folderPath)
  if (cached) {
    const updated = cached.map(item => {
      if (item.name === oldName) {
        return { ...item, name: newName }
      }
      return item
    })
    folderCache.set(folderPath, updated, '') // Empty etag - will revalidate
  }
}
