/**
 * Thumbnail Queue Utilities
 *
 * Simplified module for:
 * 1. High-priority file preview loading
 * 2. Signaling user activity to pause background caching
 *
 * Note: Regular thumbnails use browser's native loading and caching.
 */

// Current folder tracking - used for backend caching priority
let currentFolder = ''

/**
 * Set current folder - used for backend caching priority
 * Call this when navigating to a new folder
 */
export const setCurrentFolder = (folderPath: string) => {
  currentFolder = folderPath
}

/**
 * Get current folder
 */
export const getCurrentFolder = () => currentFolder

/**
 * Fetch with high priority (for file preview)
 * Uses native fetch with priority hint for maximum speed
 */
export const fetchHighPriority = (url: string): Promise<Response> => {
  // Use native fetch with high priority
  return fetch(url, {
    priority: 'high',
    // @ts-ignore - priority is a valid fetch option in modern browsers
    importance: 'high',
  } as RequestInit)
}

/**
 * Preload an image for instant display (called before user clicks)
 */
export const preloadImage = (url: string): void => {
  // Use link preload for browser-level optimization
  const link = document.createElement('link')
  link.rel = 'preload'
  link.as = 'image'
  link.href = url
  document.head.appendChild(link)

  // Remove after 30 seconds to avoid memory leaks
  setTimeout(() => link.remove(), 30000)
}

/**
 * Cancel pending thumbnail requests - now a no-op since we use browser native loading
 * Kept for API compatibility
 */
export const cancelThumbnails = (_folderPath?: string) => {
  // No-op: browser handles its own request management
}

/**
 * Signal user activity - signals to backend to pause background caching
 */
export const signalUserActivity = () => {
  // Call backend to signal user activity (pause background caching)
  fetch('/image-browsing/signal-activity', { method: 'POST' }).catch(() => {
    // Ignore errors - this is just a hint to backend
  })
}
