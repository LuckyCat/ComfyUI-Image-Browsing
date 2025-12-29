/**
 * Client-side folder cache with ETag support for instant navigation
 */

interface CacheEntry<T> {
  data: T
  etag: string
  timestamp: number
  path: string
}

interface FolderCacheConfig {
  maxEntries: number
  maxAgeMs: number
}

const DEFAULT_CONFIG: FolderCacheConfig = {
  maxEntries: 500,           // Store up to 500 folders
  maxAgeMs: 24 * 60 * 60 * 1000, // 24 hours - ETag validation ensures freshness anyway
}

class FolderCache {
  private cache: Map<string, CacheEntry<any>> = new Map()
  private config: FolderCacheConfig
  private accessOrder: string[] = []

  constructor(config: Partial<FolderCacheConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config }
    this.loadFromStorage()
  }

  private loadFromStorage() {
    try {
      const stored = sessionStorage.getItem('folderCache')
      if (stored) {
        const parsed = JSON.parse(stored)
        const now = Date.now()
        // Only load entries that aren't expired
        for (const [key, entry] of Object.entries(parsed)) {
          const e = entry as CacheEntry<any>
          if (now - e.timestamp < this.config.maxAgeMs) {
            this.cache.set(key, e)
            this.accessOrder.push(key)
          }
        }
      }
    } catch (e) {
      // Ignore storage errors
    }
  }

  private saveToStorage() {
    try {
      const obj: Record<string, CacheEntry<any>> = {}
      for (const [key, entry] of this.cache.entries()) {
        obj[key] = entry
      }
      sessionStorage.setItem('folderCache', JSON.stringify(obj))
    } catch (e) {
      // Storage full or unavailable - clear old entries
      try {
        this.evictOldest(this.cache.size / 2)
        const obj: Record<string, CacheEntry<any>> = {}
        for (const [key, entry] of this.cache.entries()) {
          obj[key] = entry
        }
        sessionStorage.setItem('folderCache', JSON.stringify(obj))
      } catch {
        // Give up on storage
      }
    }
  }

  private evictOldest(count: number = 1) {
    for (let i = 0; i < count && this.accessOrder.length > 0; i++) {
      const oldest = this.accessOrder.shift()
      if (oldest) {
        this.cache.delete(oldest)
      }
    }
  }

  private updateAccessOrder(key: string) {
    const idx = this.accessOrder.indexOf(key)
    if (idx > -1) {
      this.accessOrder.splice(idx, 1)
    }
    this.accessOrder.push(key)
  }

  get<T>(path: string): CacheEntry<T> | null {
    const entry = this.cache.get(path)
    if (!entry) return null

    // Check if expired
    if (Date.now() - entry.timestamp > this.config.maxAgeMs) {
      this.cache.delete(path)
      const idx = this.accessOrder.indexOf(path)
      if (idx > -1) this.accessOrder.splice(idx, 1)
      return null
    }

    this.updateAccessOrder(path)
    return entry as CacheEntry<T>
  }

  /**
   * Get data directly from cache (for instant display)
   * Returns null if not cached
   */
  getData<T>(path: string): T | null {
    const entry = this.get<T>(path)
    return entry ? entry.data : null
  }

  /**
   * Check if path is in cache
   */
  has(path: string): boolean {
    return this.get(path) !== null
  }

  getEtag(path: string): string | null {
    const entry = this.cache.get(path)
    if (!entry) return null
    if (Date.now() - entry.timestamp > this.config.maxAgeMs) return null
    return entry.etag
  }

  set<T>(path: string, data: T, etag: string) {
    // Evict if at capacity
    if (this.cache.size >= this.config.maxEntries && !this.cache.has(path)) {
      this.evictOldest()
    }

    const entry: CacheEntry<T> = {
      data,
      etag,
      timestamp: Date.now(),
      path,
    }

    this.cache.set(path, entry)
    this.updateAccessOrder(path)
    this.saveToStorage()
  }

  invalidate(path: string) {
    this.cache.delete(path)
    const idx = this.accessOrder.indexOf(path)
    if (idx > -1) this.accessOrder.splice(idx, 1)
    this.saveToStorage()
  }

  invalidatePrefix(prefix: string) {
    const keysToDelete: string[] = []
    for (const key of this.cache.keys()) {
      if (key.startsWith(prefix)) {
        keysToDelete.push(key)
      }
    }
    for (const key of keysToDelete) {
      this.invalidate(key)
    }
  }

  clear() {
    this.cache.clear()
    this.accessOrder = []
    sessionStorage.removeItem('folderCache')
  }

  getStats() {
    return {
      entries: this.cache.size,
      maxEntries: this.config.maxEntries,
      paths: Array.from(this.cache.keys()),
    }
  }
}

// Singleton instance
export const folderCache = new FolderCache()

// Export type for use in other modules
export type { CacheEntry, FolderCacheConfig }
