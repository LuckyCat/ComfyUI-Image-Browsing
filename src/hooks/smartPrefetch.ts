/**
 * Smart prefetching with predictive strategies
 * Inspired by Google Drive's predictive prefetching
 */

import { queuePrefetch } from './requestManager'

interface FolderAccessHistory {
  path: string
  timestamp: number
  count: number
}

class SmartPrefetcher {
  private history: FolderAccessHistory[] = []
  private maxHistorySize = 100
  private prefetchedPaths = new Set<string>()

  /**
   * Record folder access for pattern learning
   */
  recordAccess(path: string) {
    const now = Date.now()
    const existing = this.history.find(h => h.path === path)

    if (existing) {
      existing.timestamp = now
      existing.count++
    } else {
      this.history.push({ path, timestamp: now, count: 1 })
    }

    // Trim history
    if (this.history.length > this.maxHistorySize) {
      this.history.sort((a, b) => b.timestamp - a.timestamp)
      this.history = this.history.slice(0, this.maxHistorySize)
    }

    // Save to localStorage
    this.saveHistory()
  }

  /**
   * Prefetch on folder open
   * Strategy: Prefetch siblings, children, and frequently accessed folders
   */
  onFolderOpen(currentPath: string, siblings: string[] = [], children: string[] = []) {
    // Priority 0: Current folder's children (most likely to be opened)
    const childrenNotCached = children.filter(p => !this.prefetchedPaths.has(p))
    if (childrenNotCached.length > 0) {
      queuePrefetch(childrenNotCached.slice(0, 10), 0)  // Top 10 children
      childrenNotCached.forEach(p => this.prefetchedPaths.add(p))
    }

    // Priority 1: Siblings (user might browse nearby folders)
    const siblingsNotCached = siblings.filter(p => !this.prefetchedPaths.has(p) && p !== currentPath)
    if (siblingsNotCached.length > 0) {
      queuePrefetch(siblingsNotCached.slice(0, 5), 1)  // Top 5 siblings
      siblingsNotCached.forEach(p => this.prefetchedPaths.add(p))
    }

    // Priority 2: Frequently accessed folders
    const frequentPaths = this.getFrequentPaths(5)
      .filter(p => !this.prefetchedPaths.has(p) && p !== currentPath)

    if (frequentPaths.length > 0) {
      queuePrefetch(frequentPaths, 2)
      frequentPaths.forEach(p => this.prefetchedPaths.add(p))
    }

    // Priority 3: Recently accessed folders
    const recentPaths = this.getRecentPaths(3)
      .filter(p => !this.prefetchedPaths.has(p) && p !== currentPath)

    if (recentPaths.length > 0) {
      queuePrefetch(recentPaths, 3)
      recentPaths.forEach(p => this.prefetchedPaths.add(p))
    }
  }

  /**
   * Prefetch on hover (aggressive prediction)
   */
  onFolderHover(path: string, hoverDuration: number) {
    // If user hovers for >300ms, likely to click
    if (hoverDuration > 300 && !this.prefetchedPaths.has(path)) {
      queuePrefetch([path], 0)  // High priority
      this.prefetchedPaths.add(path)
    }
  }

  /**
   * Prefetch parent's siblings when moving up
   */
  onNavigateUp(currentPath: string, parentPath: string, parentSiblings: string[] = []) {
    // User going up - likely to explore parent's siblings
    const notCached = parentSiblings.filter(p => !this.prefetchedPaths.has(p))

    if (notCached.length > 0) {
      queuePrefetch(notCached.slice(0, 10), 0)
      notCached.forEach(p => this.prefetchedPaths.add(p))
    }
  }

  /**
   * Get frequently accessed folders
   */
  private getFrequentPaths(limit: number = 5): string[] {
    return [...this.history]
      .sort((a, b) => b.count - a.count)
      .slice(0, limit)
      .map(h => h.path)
  }

  /**
   * Get recently accessed folders
   */
  private getRecentPaths(limit: number = 3): string[] {
    return [...this.history]
      .sort((a, b) => b.timestamp - a.timestamp)
      .slice(0, limit)
      .map(h => h.path)
  }

  /**
   * Clear prefetched paths cache (call on cache invalidation)
   */
  clearPrefetchedCache() {
    this.prefetchedPaths.clear()
  }

  /**
   * Save history to localStorage
   */
  private saveHistory() {
    try {
      localStorage.setItem('prefetchHistory', JSON.stringify(this.history))
    } catch (e) {
      // Ignore storage errors
    }
  }

  /**
   * Load history from localStorage
   */
  loadHistory() {
    try {
      const stored = localStorage.getItem('prefetchHistory')
      if (stored) {
        this.history = JSON.parse(stored)
      }
    } catch (e) {
      // Ignore errors
    }
  }

  /**
   * Get statistics
   */
  getStats() {
    return {
      historySize: this.history.length,
      prefetchedCount: this.prefetchedPaths.size,
      topFolders: this.getFrequentPaths(10),
    }
  }
}

// Singleton instance
export const smartPrefetcher = new SmartPrefetcher()

// Load history on init
if (typeof window !== 'undefined') {
  smartPrefetcher.loadHistory()
}
