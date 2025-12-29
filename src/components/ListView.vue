<template>
  <div class="list-view h-full flex flex-col">
    <!-- Header -->
    <div class="list-header flex items-center border-b border-gray-700 px-4 py-2 text-sm font-medium text-gray-400">
      <div 
        class="flex-1 cursor-pointer hover:text-white flex items-center gap-1"
        @click="toggleSort('name')"
      >
        {{ $t('name') }}
        <i v-if="sortBy === 'name'" :class="['pi text-xs', sortDesc ? 'pi-sort-down' : 'pi-sort-up']"></i>
      </div>
      <div 
        class="w-40 text-right cursor-pointer hover:text-white flex items-center justify-end gap-1"
        @click="toggleSort('date')"
      >
        {{ $t('dateModified') }}
        <i v-if="sortBy === 'date'" :class="['pi text-xs', sortDesc ? 'pi-sort-down' : 'pi-sort-up']"></i>
      </div>
    </div>
    
    <!-- List -->
    <div class="flex-1 overflow-auto">
      <div
        v-for="item in sortedItems"
        :key="item.name"
        :class="[
          'list-item flex items-center px-4 py-2 cursor-pointer',
          'hover:bg-gray-800',
          selectedItemsName.includes(item.name) ? 'bg-gray-700' : '',
        ]"
        draggable="true"
        @click="item.onClick?.($event)"
        @dblclick="item.onDbClick?.($event)"
        @contextmenu.stop="item.onContextMenu?.($event)"
        @dragstart="onDragStart($event, item)"
      >
        <div class="flex-1 flex items-center gap-2 overflow-hidden">
          <i :class="['pi', getIcon(item.type)]" :style="{ color: getIconColor(item.type) }"></i>
          <span class="truncate">{{ item.name }}</span>
        </div>
        <div class="w-40 text-right text-sm text-gray-400">
          {{ formatDate(item.updatedAt) }}
        </div>
      </div>
      
      <div v-if="items.length === 0" class="text-center text-gray-500 py-8">
        No items
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { DirectoryItem, RootFolderType } from 'types/typings'

const props = defineProps<{
  items: DirectoryItem[]
  selectedItems: DirectoryItem[]
  rootType: RootFolderType
}>()

const emit = defineEmits<{
  (e: 'dragstart', event: DragEvent, item: DirectoryItem): void
}>()

const sortBy = ref<'name' | 'date'>('date')
const sortDesc = ref(true) // Default: newest first

const selectedItemsName = computed(() => props.selectedItems.map(i => i.name))

const sortedItems = computed(() => {
  const items = [...props.items]
  
  // Always put folders first
  items.sort((a, b) => {
    // Folders first
    if (a.type === 'folder' && b.type !== 'folder') return -1
    if (a.type !== 'folder' && b.type === 'folder') return 1
    
    // Then sort by selected criterion
    if (sortBy.value === 'name') {
      const cmp = a.name.localeCompare(b.name)
      return sortDesc.value ? -cmp : cmp
    } else {
      const cmp = a.updatedAt - b.updatedAt
      return sortDesc.value ? -cmp : cmp
    }
  })
  
  return items
})

const toggleSort = (by: 'name' | 'date') => {
  if (sortBy.value === by) {
    sortDesc.value = !sortDesc.value
  } else {
    sortBy.value = by
    sortDesc.value = by === 'date' // Default desc for date, asc for name
  }
}

const getIcon = (type: string) => {
  switch (type) {
    case 'folder': return 'pi-folder'
    case 'workflow': return 'pi-file'
    case 'prompt': return 'pi-file-edit'
    default: return 'pi-file'
  }
}

const getIconColor = (type: string) => {
  switch (type) {
    case 'folder': return '#FFCA28'
    case 'workflow': return '#64B5F6'
    case 'prompt': return '#81C784'
    default: return '#9E9E9E'
  }
}

const formatDate = (timestamp: number) => {
  const date = new Date(timestamp)
  const day = date.getDate().toString().padStart(2, '0')
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  const month = months[date.getMonth()]
  const year = date.getFullYear().toString().slice(-2)
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  
  return `${day}-${month}-${year} ${hours}:${minutes}`
}

const onDragStart = (event: DragEvent, item: DirectoryItem) => {
  emit('dragstart', event, item)
}
</script>

<style scoped>
.list-view {
  font-size: 14px;
}

.list-item {
  border-bottom: 1px solid rgba(75, 85, 99, 0.3);
}

.list-item:last-child {
  border-bottom: none;
}
</style>
