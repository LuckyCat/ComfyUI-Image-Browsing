import { defineStore } from 'hooks/store'
import { app } from 'scripts/comfyAPI'
import { onMounted, ref } from 'vue'

// API endpoints for paths configuration
const API_BASE = '/image-browsing/paths'

interface PathsStatus {
  thumbnail_cache: PathInfo
  output: PathInfo
  workflows: PathInfo
  prompts: PathInfo
}

interface PathInfo {
  current: string
  default: string
  is_default: boolean
  exists: boolean
  valid: boolean
}

const useAddPathsSettings = (paths: {
  thumbnailCachePath: ReturnType<typeof ref<string>>
  outputPath: ReturnType<typeof ref<string>>
  workflowsPath: ReturnType<typeof ref<string>>
  promptsPath: ReturnType<typeof ref<string>>
  ffmpegPath: ReturnType<typeof ref<string>>
}) => {

  /**
   * Set a path configuration
   */
  async function setPath(type: 'thumbnail_cache' | 'output' | 'workflows' | 'prompts', path: string) {
    try {
      const response = await fetch(`${API_BASE}/set`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type, path })
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const data = await response.json()

      if (data.success) {
        // Update local state
        switch (type) {
          case 'thumbnail_cache':
            paths.thumbnailCachePath.value = path
            console.log('[PathsSettings] Thumbnail cache path updated. Restart required.')
            break
          case 'output':
            paths.outputPath.value = path
            console.log('[PathsSettings] Output path updated:', path)
            break
          case 'workflows':
            paths.workflowsPath.value = path
            console.log('[PathsSettings] Workflows path updated:', path)
            break
          case 'prompts':
            paths.promptsPath.value = path
            console.log('[PathsSettings] Prompts path updated:', path)
            break
        }
      } else {
        console.error('[PathsSettings] Failed to set path:', data.error)
        throw new Error(data.error)
      }
    } catch (error) {
      console.error('[PathsSettings] Error setting path:', error)
      throw error
    }
  }

  /**
   * Set FFmpeg path
   */
  async function setFFmpegPath(path: string) {
    try {
      const response = await fetch('/image-browsing/ffmpeg/set-path', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path })
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const data = await response.json()

      if (data.success) {
        paths.ffmpegPath.value = path
        console.log('[PathsSettings] FFmpeg path updated:', path)
        console.log('[PathsSettings] FFmpeg info:', data.data)
      } else {
        console.error('[PathsSettings] Failed to set FFmpeg path:', data.error)
        throw new Error(data.error)
      }
    } catch (error) {
      console.error('[PathsSettings] Error setting FFmpeg path:', error)
      throw error
    }
  }

  onMounted(async () => {
    console.log('[PathsSettings] Initializing...')

    try {
      // Load current paths from backend
      const response = await fetch(`${API_BASE}/status`)

      if (response.ok) {
        const data = await response.json()

        if (data.success) {
          const pathsData = data.data as PathsStatus

          // Update state with current values
          paths.thumbnailCachePath.value = pathsData.thumbnail_cache.current
          paths.outputPath.value = pathsData.output.current
          paths.workflowsPath.value = pathsData.workflows.current
          paths.promptsPath.value = pathsData.prompts.current

          console.log('[PathsSettings] Loaded paths from backend:', pathsData)
        }
      }
    } catch (error) {
      console.error('[PathsSettings] Failed to load paths:', error)
    }

    try {
      // Load FFmpeg path
      const response = await fetch('/image-browsing/ffmpeg/status')

      if (response.ok) {
        const data = await response.json()

        if (data.success) {
          paths.ffmpegPath.value = data.data.current_path
          console.log('[PathsSettings] Loaded FFmpeg path:', paths.ffmpegPath.value)
        }
      }
    } catch (error) {
      console.error('[PathsSettings] Failed to load FFmpeg path:', error)
    }

    // Register Thumbnail Cache Path setting
    app.ui?.settings.addSetting({
      id: 'ImageBrowsing.Paths.ThumbnailCache',
      category: ['Output Explorer', 'ThumbnailCache'],
      name: 'Thumbnail Cache Directory',
      type: 'text',
      defaultValue: app.ui?.settings.getSettingValue('ImageBrowsing.Paths.ThumbnailCache') ?? paths.thumbnailCachePath.value,
      tooltip: 'Directory where thumbnail cache files are stored (requires restart to take effect)',
      onChange: async (value: string) => {
        await setPath('thumbnail_cache', value)
      },
    })

    // Register Output Path setting
    app.ui?.settings.addSetting({
      id: 'ImageBrowsing.Paths.Output',
      category: ['Output Explorer', 'Output'],
      name: 'Output Directory',
      type: 'text',
      defaultValue: paths.outputPath.value,
      tooltip: 'Custom output directory path (absolute path required)',
      onChange: async (value: string) => {
        await setPath('output', value)
      },
    })

    // Register Workflows Path setting
    app.ui?.settings.addSetting({
      id: 'ImageBrowsing.Paths.Workflows',
      category: ['Output Explorer', 'Workflows'],
      name: 'Workflows Directory',
      type: 'text',
      defaultValue: paths.workflowsPath.value,
      tooltip: 'Directory for workflow files (.json)',
      onChange: async (value: string) => {
        await setPath('workflows', value)
      },
    })

    // Register Prompts Path setting
    app.ui?.settings.addSetting({
      id: 'ImageBrowsing.Paths.Prompts',
      category: ['Output Explorer', 'Prompts'],
      name: 'Prompts Directory',
      type: 'text',
      defaultValue: paths.promptsPath.value,
      tooltip: 'Directory for prompt files (.txt)',
      onChange: async (value: string) => {
        await setPath('prompts', value)
      },
    })

    // Register FFmpeg Path setting
    app.ui?.settings.addSetting({
      id: 'ImageBrowsing.FFmpeg.Path',
      category: ['Output Explorer','FFmpeg'],
      name: 'FFmpeg Path',
      type: 'text',
      defaultValue: paths.ffmpegPath.value,
      tooltip: 'Path to FFmpeg executable (e.g., "ffmpeg", "C:\\ffmpeg\\bin\\ffmpeg.exe", or "/usr/bin/ffmpeg")',
      onChange: async (value: string) => {
        await setFFmpegPath(value)
      },
    })

    console.log('[PathsSettings] All settings registered successfully')
  })
}

export const usePathsSettings = defineStore('pathsSettings', () => {
  const thumbnailCachePath = ref('')
  const outputPath = ref('')
  const workflowsPath = ref('')
  const promptsPath = ref('')
  const ffmpegPath = ref('ffmpeg')

  const pathsState = {
    thumbnailCachePath,
    outputPath,
    workflowsPath,
    promptsPath,
    ffmpegPath,
  }

  useAddPathsSettings(pathsState)

  return pathsState
})

export type PathsSettingsStore = ReturnType<typeof usePathsSettings>

declare module 'hooks/store' {
  interface StoreProvider {
    pathsSettings: PathsSettingsStore
  }
}
