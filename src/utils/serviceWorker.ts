/**
 * Service Worker registration and management
 */

export interface CacheSize {
  entries: number
  bytes: number
  mb: string
}

class ServiceWorkerManager {
  private registration: ServiceWorkerRegistration | null = null

  /**
   * Register service worker
   */
  async register(): Promise<boolean> {
    if (!('serviceWorker' in navigator)) {
      console.warn('Service Worker not supported')
      return false
    }

    try {
      this.registration = await navigator.serviceWorker.register('/extensions/ComfyUI-Image-Browsing/sw.js', {
        scope: '/'
      })

      console.log('Service Worker registered:', this.registration)

      // Handle updates
      this.registration.addEventListener('updatefound', () => {
        const newWorker = this.registration!.installing

        if (newWorker) {
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              console.log('New Service Worker available! Please refresh.')
              // Could show notification to user
            }
          })
        }
      })

      return true
    } catch (error) {
      console.error('Service Worker registration failed:', error)
      return false
    }
  }

  /**
   * Unregister service worker
   */
  async unregister(): Promise<boolean> {
    if (!this.registration) {
      return false
    }

    try {
      const success = await this.registration.unregister()
      console.log('Service Worker unregistered:', success)
      return success
    } catch (error) {
      console.error('Service Worker unregistration failed:', error)
      return false
    }
  }

  /**
   * Clear service worker cache
   */
  async clearCache(): Promise<boolean> {
    if (!this.registration || !this.registration.active) {
      return false
    }

    return new Promise((resolve) => {
      const messageChannel = new MessageChannel()

      messageChannel.port1.onmessage = (event) => {
        resolve(event.data.success || false)
      }

      this.registration!.active!.postMessage(
        { type: 'CLEAR_CACHE' },
        [messageChannel.port2]
      )
    })
  }

  /**
   * Get cache size
   */
  async getCacheSize(): Promise<CacheSize | null> {
    if (!this.registration || !this.registration.active) {
      return null
    }

    return new Promise((resolve) => {
      const messageChannel = new MessageChannel()

      messageChannel.port1.onmessage = (event) => {
        resolve(event.data.size || null)
      }

      this.registration!.active!.postMessage(
        { type: 'CACHE_SIZE' },
        [messageChannel.port2]
      )
    })
  }

  /**
   * Check if service worker is active
   */
  isActive(): boolean {
    return !!this.registration && !!this.registration.active
  }
}

// Singleton instance
export const swManager = new ServiceWorkerManager()

// Auto-register on module load (optional - can be manual)
if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    swManager.register().catch(console.error)
  })
}
