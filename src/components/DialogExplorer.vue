<template>
  <div
    ref="container"
    class="flex h-full w-full"
    @contextmenu.prevent="nonContextMenu"
  >
    <!-- Folder Tree Sidebar -->
    <div
      :class="[
        'folder-sidebar flex-shrink-0 border-r border-gray-700 overflow-hidden',
        showSidebar ? 'w-64' : 'w-0',
      ]"
    >
      <FolderTree
        ref="folderTreeRef"
        :selected-path="currentPath"
        @select="onTreeSelect"
        @refresh="onRefresh"
        @move-files="onMoveFiles"
      />
    </div>

    <!-- Main Content -->
    <div class="flex flex-1 flex-col overflow-hidden">
      <div :class="['mb-4 flex gap-4 px-4', $xl('flex-row', 'flex-col')]">
        <div class="flex flex-1 gap-1 overflow-hidden">
          <!-- Toggle Sidebar Button -->
          <Button
            class="shrink-0"
            :icon="showSidebar ? 'pi pi-chevron-left' : 'pi pi-chevron-right'"
            :text="true"
            :rounded="true"
            severity="secondary"
            @click="showSidebar = !showSidebar"
            v-tooltip.bottom="showSidebar ? 'Hide sidebar' : 'Show sidebar'"
          ></Button>

          <Button
            class="shrink-0"
            icon="pi pi-arrow-up"
            :text="true"
            :rounded="true"
            severity="secondary"
            :disabled="breadcrumb.length < 2"
            @click="goBackParentFolder"
          ></Button>

          <Button
            class="shrink-0"
            icon="pi pi-refresh"
            :text="true"
            :rounded="true"
            severity="secondary"
            @click="onRefresh"
          ></Button>

          <!-- View Mode Toggle (list mode is lighter for very large folders) -->
          <Button
            class="shrink-0"
            icon="pi pi-th-large"
            :text="true"
            :rounded="true"
            :severity="viewMode === 'grid' ? 'primary' : 'secondary'"
            @click="viewMode = 'grid'"
            v-tooltip.bottom="'Grid view'"
          ></Button>
          <Button
            class="shrink-0"
            icon="pi pi-list"
            :text="true"
            :rounded="true"
            :severity="viewMode === 'list' ? 'primary' : 'secondary'"
            @click="viewMode = 'list'"
            v-tooltip.bottom="'List view'"
          ></Button>

          <div
            :class="[
              'flex h-10 flex-1 basis-10 items-center rounded-lg px-2 py-1',
              'bg-gray-100 dark:bg-gray-900',
              'overflow-hidden *:select-none *:opacity-70',
            ]"
          >
            <div class="flex h-full items-center">
              <span class="flex h-full items-center justify-center px-2">
                <i class="pi pi-desktop"></i>
              </span>
              <span class="flex aspect-square h-full items-center justify-center">
                <i class="pi pi-angle-right"></i>
              </span>
            </div>
            <div class="flex h-full items-center justify-end overflow-hidden">
              <div
                v-for="(item, index) in breadcrumb"
                :key="item.fullname"
                class="flex h-full items-center rounded border border-solid border-transparent hover:border-gray-400 dark:hover:border-gray-700"
              >
                <span
                  class="flex h-full items-center whitespace-nowrap px-2 hover:bg-gray-400 dark:hover:bg-gray-700"
                  @click="entryFolder(item, index)"
                >
                  {{ item.name }}
                </span>
                <ResponseSelect
                  v-if="item.children.length > 0"
                  :model-value="item.fullname"
                  :items="item.children"
                >
                  <template #target="{ toggle, overlayVisible }">
                    <span
                      class="flex aspect-square h-full items-center justify-center hover:bg-gray-400 dark:hover:bg-gray-700"
                      @click="toggle"
                    >
                      <i
                        :class="[
                          'pi pi-angle-right transition-all',
                          overlayVisible ? '[transform:rotate(90deg)]' : '',
                        ]"
                      ></i>
                    </span>
                  </template>
                </ResponseSelect>
              </div>
            </div>
          </div>
        </div>

        <ResponseInput
          v-model="searchContent"
          :placeholder="$t('searchInFolder', [currentFolderName])"
          :allow-clear="true"
        ></ResponseInput>
      </div>

      <div
        class="relative flex-1 select-none overflow-hidden"
        @click="clearSelected"
        @contextmenu.stop="folderContext"
      >
        <ResponseScroll :items="folderItems" :item-size="scrollItemSize" class="h-full">
          <template #item="{ item }">
            <div
              v-if="viewMode === 'grid'"
              class="grid justify-center"
              :style="{ gridTemplateColumns: `repeat(auto-fit, ${itemSize}px)` }"
            >
              <div
                v-for="rowItem in item"
                :key="rowItem.name"
                class="px-1 pb-1"
                :style="{ width: `${itemSize}px`, height: `${itemSize}px` }"
              >
                <div
                  :class="[
                    'flex h-full w-full flex-col items-center justify-center gap-1 overflow-hidden whitespace-nowrap rounded-lg',
                    'hover:bg-gray-300 dark:hover:bg-gray-800',
                    selectedItemsName.includes(rowItem.name)
                      ? 'bg-gray-300 dark:bg-gray-800'
                      : '',
                  ]"
                  @click.stop="rowItem.onClick"
                  @dblclick.stop="rowItem.onDbClick"
                  @contextmenu.stop="rowItem.onContextMenu"
                >
                  <div
                    class="relative overflow-hidden rounded-lg"
                    :style="{
                      width: `${rowItem.type === 'folder' ? folderSize : thumbnailSize}px`,
                      height: `${rowItem.type === 'folder' ? folderSize : thumbnailSize}px`,
                    }"
                  >
                    <div v-if="rowItem.type === 'folder'" class="h-full w-full">
                      <svg
                        t="1730360536641"
                        class="icon"
                        viewBox="0 0 1024 1024"
                        version="1.1"
                        xmlns="http://www.w3.org/2000/svg"
                        p-id="5617"
                        width="100%"
                        height="100%"
                      >
                        <path
                          d="M853.333333 256H469.333333l-85.333333-85.333333H170.666667c-46.933333 0-85.333333 38.4-85.333334 85.333333v170.666667h853.333334v-85.333334c0-46.933333-38.4-85.333333-85.333334-85.333333z"
                          fill="#FFA000"
                          p-id="5618"
                        ></path>
                        <path
                          d="M853.333333 256H170.666667c-46.933333 0-85.333333 38.4-85.333334 85.333333v426.666667c0 46.933333 38.4 85.333333 85.333334 85.333333h682.666666c46.933333 0 85.333333-38.4 85.333334-85.333333V341.333333c0-46.933333-38.4-85.333333-85.333334-85.333333z"
                          fill="#FFCA28"
                          p-id="5619"
                        ></path>
                      </svg>
                    </div>
                    <div v-else-if="rowItem.type === 'image'" class="h-full w-full">
                      <LazyImage
                        v-if="thumbnailsEnabled"
                        class="h-full w-full"
                        :src="getPreviewUrl(rowItem)"
                        alt="preview"
                      />
                      <div
                        v-else
                        class="flex h-full w-full items-center justify-center opacity-50"
                      >
                        <i class="pi pi-image text-2xl"></i>
                      </div>
                    </div>
                    <div
                      v-else-if="rowItem.type === 'video'"
                      class="relative h-full w-full"
                    >
                      <LazyImage
                        v-if="thumbnailsEnabled"
                        class="h-full w-full"
                        :src="getPreviewUrl(rowItem)"
                        alt="video preview"
                      />
                      <div
                        v-else
                        class="flex h-full w-full items-center justify-center opacity-50"
                      >
                        <i class="pi pi-video text-2xl"></i>
                      </div>
                      <!-- Video play icon overlay -->
                      <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
                        <div class="bg-black/50 rounded-full p-2">
                          <i class="pi pi-play text-white text-xl"></i>
                        </div>
                      </div>
                    </div>
                    <div
                      v-else-if="rowItem.type === 'audio'"
                      class="relative flex h-full w-full items-center justify-center"
                    >
                      <svg
                        class="icon"
                        viewBox="0 0 1024 1024"
                        version="1.1"
                        xmlns="http://www.w3.org/2000/svg"
                        p-id="5617"
                        width="100%"
                        height="100%"
                      >
                        <defs>
                          <linearGradient
                            id="f1"
                            x1="0%"
                            y1="0%"
                            x2="100%"
                            y2="100%"
                          >
                            <stop offset="0%" stop-color="#f1f1f1" />
                            <stop offset="100%" stop-color="#e1e1e1" />
                          </linearGradient>
                          <linearGradient
                            id="f2"
                            x1="0%"
                            y1="0%"
                            x2="100%"
                            y2="100%"
                          >
                            <stop offset="0%" stop-color="#fb904e" />
                            <stop offset="100%" stop-color="#8861c4" />
                          </linearGradient>
                        </defs>
                        <g>
                          <path
                            d="M182,64h460l200,200v696h-660z"
                            fill="#f5f6f7"
                            stroke="#9facb5"
                            stroke-width="2"
                          ></path>
                          <path
                            d="M642,64l200,200h-200z"
                            fill="url(#f1)"
                            stroke="#9facb5"
                            stroke-width="2"
                          ></path>
                        </g>
                        <g>
                          <path
                            d="M512,262a10,10 0 1,1 0,500a10,10 0 1,1 0,-500z"
                            fill="url(#f2)"
                          ></path>
                          <path
                            d="M512,312a10,10 0 1,0 0,400a10,10 0 1,0 0,-400z"
                            fill="black"
                          ></path>
                          <path
                            d="M532,512m-100,0v-100q0,-20 20,-10l180,100q20,10 0,20l-180,100q-20,10 -20,-10 z"
                            fill="url(#f1)"
                          ></path>
                        </g>
                      </svg>
                    </div>
                    <div
                      class="absolute left-0 top-0 h-full w-full"
                      draggable="true"
                      @dragstart="(e) => onItemDragStart(e, rowItem)"
                      @dragend.stop="rowItem.onDragEnd"
                    ></div>
                  </div>
                  <div class="flex w-full justify-center overflow-hidden px-1">
                    <span class="overflow-hidden text-ellipsis text-xs">
                      {{ rowItem.name }}
                    </span>
                  </div>
                </div>
              </div>
              <div class="col-span-full"></div>
            </div>

            <!-- List view: filenames are usable immediately; previews load lazily -->
            <div v-else class="flex w-full flex-col px-2">
              <div
                v-for="rowItem in item"
                :key="rowItem.name"
                class="py-0.5"
              >
                <div
                  :class="[
                    'flex w-full items-center gap-3 rounded-lg px-2 py-1',
                    'hover:bg-gray-300 dark:hover:bg-gray-800',
                    selectedItemsName.includes(rowItem.name)
                      ? 'bg-gray-300 dark:bg-gray-800'
                      : '',
                  ]"
                  draggable="true"
                  @dragstart="(e) => onItemDragStart(e, rowItem)"
                  @dragend.stop="rowItem.onDragEnd"
                  @click.stop="rowItem.onClick"
                  @dblclick.stop="rowItem.onDbClick"
                  @contextmenu.stop="rowItem.onContextMenu"
                >
                  <div
                    class="relative overflow-hidden rounded-lg bg-gray-200 dark:bg-gray-900 flex items-center justify-center"
                    :style="{ width: `${listThumbSize}px`, height: `${listThumbSize}px` }"
                  >
                    <template v-if="rowItem.type === 'folder'">
                      <i class="pi pi-folder text-xl opacity-80"></i>
                    </template>
                    <template v-else-if="rowItem.type === 'image'">
                      <LazyImage
                        v-if="thumbnailsEnabled"
                        class="h-full w-full"
                        :src="getPreviewUrl(rowItem)"
                        alt="preview"
                      />
                      <i v-else class="pi pi-image text-xl opacity-60"></i>
                    </template>
                    <template v-else-if="rowItem.type === 'video'">
                      <LazyImage
                        v-if="thumbnailsEnabled"
                        class="h-full w-full"
                        :src="getPreviewUrl(rowItem)"
                        alt="video preview"
                      />
                      <i v-else class="pi pi-video text-xl opacity-60"></i>
                      <div
                        v-if="thumbnailsEnabled"
                        class="absolute inset-0 flex items-center justify-center pointer-events-none"
                      >
                        <div class="bg-black/50 rounded-full p-1.5">
                          <i class="pi pi-play text-white text-xs"></i>
                        </div>
                      </div>
                    </template>
                    <template v-else-if="rowItem.type === 'audio'">
                      <i class="pi pi-volume-up text-xl opacity-70"></i>
                    </template>
                    <template v-else>
                      <i class="pi pi-file text-xl opacity-70"></i>
                    </template>
                  </div>

                  <div class="min-w-0 flex-1">
                    <div class="truncate text-sm">{{ rowItem.name }}</div>
                    <div class="truncate text-xs opacity-60">{{ rowItem.type }}</div>
                  </div>
                </div>
              </div>
            </div>
          </template>

          <template #empty>
            <div></div>
          </template>
        </ResponseScroll>

        <div
          v-show="loading"
          class="absolute left-0 top-0 h-full w-full bg-black/10"
        >
          <div class="flex h-full w-full flex-col items-center justify-center">
            <div class="pi pi-spin pi-spinner"></div>
          </div>
        </div>

        <div
          v-show="!loading && folderItems.length === 0"
          class="absolute left-0 top-0 h-full w-full"
        >
          <div class="pt-20 text-center">No Data</div>
        </div>
      </div>

      <div class="flex select-none justify-between px-4 py-2 text-sm">
        <div class="flex gap-4">
          <span>{{ items.flat().length }} {{ $t('items') }}</span>
          <span v-show="selectedItems.length > 0">
            {{ $t('selected') }}
            {{ selectedItems.length }}
            {{ $t('items') }}
          </span>
        </div>
      </div>
    </div>

    <ContextMenu ref="menu" :model="contextItems"></ContextMenu>

    <ConfirmDialog group="confirm-name">
      <template #container="{ acceptCallback: accept, rejectCallback: reject }">
        <div class="flex w-90 flex-col items-end rounded px-4 pb-4 pt-8">
          <InputText
            class="w-full"
            type="text"
            v-model="confirmName"
            v-focus
            @keyup.enter="accept"
          ></InputText>
          <div class="mt-6 flex items-center gap-2">
            <Button :label="$t('cancel')" @click="reject" outlined></Button>
            <Button :label="$t('confirm')" @click="accept"></Button>
          </div>
        </div>
      </template>
    </ConfirmDialog>
  </div>
</template>

<script setup lang="ts">
import FolderTree from 'components/FolderTree.vue'
import LazyImage from 'components/LazyImage.vue'
import ResponseInput from 'components/ResponseInput.vue'
import ResponseScroll from 'components/ResponseScroll.vue'
import ResponseSelect from 'components/ResponseSelect.vue'
import { useContainerQueries } from 'hooks/container'
import { useExplorer } from 'hooks/explorer'
import { useContainerResize } from 'hooks/resize'
import { request } from 'hooks/request'
import { useToast } from 'hooks/toast'
import { useThumbnailSize, THUMBNAIL_SIZES } from 'hooks/thumbnailSize'
import { chunk } from 'lodash'
import Button from 'primevue/button'
import ConfirmDialog from 'primevue/confirmdialog'
import ContextMenu from 'primevue/contextmenu'
import InputText from 'primevue/inputtext'
import Tooltip from 'primevue/tooltip'
import { DirectoryItem } from 'types/typings'
import { computed, onBeforeUnmount, ref, watch } from 'vue'

const vTooltip = Tooltip

const { toast } = useToast()

const container = ref<HTMLElement | null>(null)
const folderTreeRef = ref<InstanceType<typeof FolderTree> | null>(null)
const showSidebar = ref(true)

// Grid is nice, but list mode is MUCH lighter on huge folders
const viewMode = ref<'grid' | 'list'>('grid')

// Defer thumbnails so filenames + interactions are instant
const thumbnailsEnabled = ref(false)

const {
  loading,
  breadcrumb,
  items,
  selectedItems,
  menuRef: menu,
  contextItems,
  confirmName,
  refresh,
  entryFolder,
  folderContext,
  goBackParentFolder,
  navigateToPath,
} = useExplorer()

const { currentSize, thumbnailSize, folderSize, itemSize } = useThumbnailSize()

const LIST_THUMB_SIZES: Record<string, number> = {
  small: 56,
  medium: 80,
  large: 120,
}

const listThumbSize = computed(() => LIST_THUMB_SIZES[currentSize.value] ?? 56)
const listRowHeight = computed(() => Math.max(48, listThumbSize.value + 12))

const scrollItemSize = computed(() =>
  viewMode.value === 'list' ? listRowHeight.value : itemSize.value,
)

const searchContent = ref('')

const { width } = useContainerResize(container)
const { $xl } = useContainerQueries(container)

const currentPath = computed(() => {
  return breadcrumb.value[breadcrumb.value.length - 1].fullname
})

const cols = computed(() => {
  const sidebarWidth = showSidebar.value ? 256 : 0
  const containerWidth = width.value - sidebarWidth
  return Math.max(1, Math.floor(containerWidth / itemSize.value))
})

const folderItems = computed(() => {
  const filterItems = items.value.filter((item) => {
    return item.name.toLowerCase().includes(searchContent.value.toLowerCase())
  })
  // In list mode we keep just 1 item per virtual row
  return chunk(filterItems, viewMode.value === 'list' ? 1 : cols.value)
})

let thumbTimer: number | null = null
let thumbIdle: number | null = null

const scheduleEnableThumbnails = () => {
  thumbnailsEnabled.value = false

  if (thumbTimer != null) {
    window.clearTimeout(thumbTimer)
    thumbTimer = null
  }

  const w = window as any
  if (thumbIdle != null && typeof w.cancelIdleCallback === 'function') {
    w.cancelIdleCallback(thumbIdle)
    thumbIdle = null
  }

  // Start thumbnail loading when the browser is idle (fallback to short delay)
  if (typeof w.requestIdleCallback === 'function') {
    thumbIdle = w.requestIdleCallback(
      () => {
        thumbnailsEnabled.value = true
        thumbIdle = null
      },
      { timeout: 600 },
    )
  } else {
    thumbTimer = window.setTimeout(() => {
      thumbnailsEnabled.value = true
      thumbTimer = null
    }, 200)
  }
}

watch(currentPath, scheduleEnableThumbnails, { immediate: true })

watch(viewMode, () => {
  // Switching views can trigger a lot of new previews; defer again
  scheduleEnableThumbnails()
})

watch(
  () => items.value.length,
  (len) => {
    // Auto-switch to list view on very large folders to avoid UI freezes
  },
)

onBeforeUnmount(() => {
  const w = window as any
  if (thumbTimer != null) window.clearTimeout(thumbTimer)
  if (thumbIdle != null && typeof w.cancelIdleCallback === 'function') {
    w.cancelIdleCallback(thumbIdle)
  }
})

const currentFolderName = computed(() => {
  return breadcrumb.value[breadcrumb.value.length - 1].name
})

const selectedItemsName = computed(() => {
  return selectedItems.value.map((item) => item.name)
})

const getPreviewUrl = (item: DirectoryItem) => {
  const size = THUMBNAIL_SIZES[currentSize.value]
  return `/image-browsing${item.fullname}?preview=true&max_size=${size}`
}

const onTreeSelect = async (path: string) => {
  if (path === currentPath.value) return
  await navigateToPath(path)
  scheduleEnableThumbnails()
}

const onRefresh = async () => {
  await refresh()
  folderTreeRef.value?.refreshTree()
  scheduleEnableThumbnails()
}

const nonContextMenu = ($event: MouseEvent) => {
  menu.value.hide($event)
}

const clearSelected = () => {
  selectedItems.value = []
}

const vFocus = {
  mounted: (el: HTMLInputElement) => el.focus(),
}

const onItemDragStart = (event: DragEvent, item: DirectoryItem) => {
  // If this item is selected, drag all selected items
  // Otherwise, drag just this item
  const itemsToMove = selectedItems.value.some(i => i.fullname === item.fullname)
    ? selectedItems.value.map(i => i.fullname)
    : [item.fullname]
  
  event.dataTransfer?.setData('application/json', JSON.stringify(itemsToMove))
  event.dataTransfer!.effectAllowed = 'move'
}

const onMoveFiles = async (files: string[], targetFolder: string) => {
  try {
    await request('/move', {
      method: 'POST',
      body: JSON.stringify({
        file_list: files,
        target_folder: targetFolder,
      }),
    })
    
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: `Moved ${files.length} item(s)`,
      life: 2000,
    })
    
    // Refresh current view
    await refresh()
    folderTreeRef.value?.refreshTree()
  } catch (err: any) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: err.message || 'Failed to move files',
      life: 5000,
    })
  }
}
</script>

<style scoped>
.folder-sidebar {
  transition: width 0.2s ease;
}
</style>