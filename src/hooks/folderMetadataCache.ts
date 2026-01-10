/**
 * Folder metadata cache for instant navigation
 * Stores folder counts and structure for ultra-fast browsing
 */

import { request } from './request'

interface FolderMetadata {
  file_count: number
  has_subfolders: boolean
  mtime: number
}

class FolderMetadataCache {
  private storageKey = 'folderMetadata'
  private metadata: Record<string, FolderMetadata> = {}

  constructor() {
    this.loadFromStorage()
  }

  /**
   * Load folder metadata from all sources
   */
  async loadAll(): Promise<void> {
    try {
      console.log('[FolderMetadata] Loading metadata from server...')
      const response = await request('/folder-metadata')

      if (response && typeof response === 'object') {
        this.metadata = response
        this.saveToStorage()
        console.log(`[FolderMetadata] Loaded ${Object.keys(this.metadata).length} folders`)
      }
    } catch (err) {
      console.error('[FolderMetadata] Failed to load:', err)
    }
  }

  /**
   * Get metadata for a folder
   */
  get(path: string): FolderMetadata | null {
    return this.metadata[path] || null
  }

  /**
   * Check if folder has metadata
   */
  has(path: string): boolean {
    return path in this.metadata
  }

  /**
   * Get all folder paths
   */
  getAllPaths(): string[] {
    return Object.keys(this.metadata)
  }

  /**
   * Get folders with subfolders (for tree view)
   */
  getFoldersWithSubfolders(): string[] {
    return Object.entries(this.metadata)
      .filter(([_, meta]) => meta.has_subfolders)
      .map(([path, _]) => path)
  }

  /**
   * Get folder count
   */
  getFileCount(path: string): number {
    return this.metadata[path]?.file_count || 0
  }

  /**
   * Clear metadata
   */
  clear(): void {
    this.metadata = {}
    localStorage.removeItem(this.storageKey)
  }

  /**
   * Get statistics
   */
  getStats() {
    const totalFolders = Object.keys(this.metadata).length
    const totalFiles = Object.values(this.metadata).reduce((sum, m) => sum + m.file_count, 0)
    const foldersWithSubfolders = Object.values(this.metadata).filter(m => m.has_subfolders).length

    return {
      totalFolders,
      totalFiles,
      foldersWithSubfolders,
      cacheSize: this.calculateSize()
    }
  }

  /**
   * Load from localStorage
   */
  private loadFromStorage(): void {
    try {
      const stored = localStorage.getItem(this.storageKey)
      if (stored) {
        this.metadata = JSON.parse(stored)
        console.log(`[FolderMetadata] Loaded ${Object.keys(this.metadata).length} folders from cache`)
      }
    } catch (err) {
      console.warn('[FolderMetadata] Failed to load from storage:', err)
    }
  }

  /**
   * Save to localStorage
   */
  private saveToStorage(): void {
    try {
      localStorage.setItem(this.storageKey, JSON.stringify(this.metadata))
    } catch (err) {
      console.error('[FolderMetadata] Failed to save to storage:', err)
    }
  }

  /**
   * Calculate cache size in KB
   */
  private calculateSize(): string {
    const str = JSON.stringify(this.metadata)
    return `${(str.length / 1024).toFixed(2)} KB`
  }
}

// Singleton instance
export const folderMetadataCache = new FolderMetadataCache()

// Auto-load on startup (in background)
if (typeof window !== 'undefined') {
  // Load after a short delay to not block initial render
  setTimeout(() => {
    folderMetadataCache.loadAll().catch(console.error)
  }, 2000)
}
