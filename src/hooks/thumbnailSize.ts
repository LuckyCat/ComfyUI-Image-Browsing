import { defineStore } from 'hooks/store'
import { app } from 'scripts/comfyAPI'
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

export type ThumbnailSizeType = 'small' | 'medium' | 'large'

export const THUMBNAIL_SIZES: Record<ThumbnailSizeType, number> = {
  small: 128,
  medium: 512,
  large: 1024,
}

export const FOLDER_SIZES: Record<ThumbnailSizeType, number> = {
  small: 96,
  medium: 400,
  large: 768,
}

export const ITEM_SIZES: Record<ThumbnailSizeType, number> = {
  small: 128,
  medium: 512,
  large: 1024,
}

const useAddThumbnailSettings = (
  currentSize: ReturnType<typeof ref<ThumbnailSizeType>>,
) => {
  const { t } = useI18n()

  onMounted(() => {
    app.ui?.settings.addSetting({
      id: 'ImageBrowsing.Thumbnail.Size',
      category: [t('outputExplorer'), t('thumbnailSize')],
      name: t('setting.thumbnailSize'),
      type: 'combo',
      defaultValue: 'small',
      options: [
        { text: 'Small', value: 'small' },
        { text: 'Medium', value: 'medium' },
        { text: 'Large', value: 'large' },
      ],
      onChange: (value: ThumbnailSizeType) => {
        currentSize.value = value
      },
    })
  })
}

export const useThumbnailSize = defineStore('thumbnailSize', () => {
  const savedSize =
    (app.ui?.settings.getSettingValue(
      'ImageBrowsing.Thumbnail.Size',
    ) as ThumbnailSizeType) ?? 'small'

  const currentSize = ref<ThumbnailSizeType>(savedSize)

  const thumbnailSize = computed(() => THUMBNAIL_SIZES[currentSize.value])
  const folderSize = computed(() => FOLDER_SIZES[currentSize.value])
  const itemSize = computed(() => ITEM_SIZES[currentSize.value])

  const setSize = (size: ThumbnailSizeType) => {
    currentSize.value = size
    app.ui?.settings.setSettingValue('ImageBrowsing.Thumbnail.Size', size)
  }

  useAddThumbnailSettings(currentSize)

  return {
    currentSize,
    thumbnailSize,
    folderSize,
    itemSize,
    setSize,
  }
})

export type ThumbnailSizeStore = ReturnType<typeof useThumbnailSize>

declare module 'hooks/store' {
  interface StoreProvider {
    thumbnailSize: ThumbnailSizeStore
  }
}
