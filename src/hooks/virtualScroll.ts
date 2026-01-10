/**
 * Virtual scrolling hook for rendering large lists efficiently
 * Only renders visible items + buffer for smooth scrolling
 */

import { ref, computed, onMounted, onUnmounted, watch } from 'vue'

export interface VirtualScrollOptions {
  itemHeight: number // Fixed height per item (or estimated)
  containerHeight?: number // Container height (auto-detect if not provided)
  bufferSize?: number // Number of items to render outside viewport
  dynamic?: boolean // Support dynamic item heights
}

export function useVirtualScroll<T>(
  items: T[],
  options: VirtualScrollOptions
) {
  const {
    itemHeight,
    containerHeight: fixedContainerHeight,
    bufferSize = 5,
    dynamic = false,
  } = options

  const scrollTop = ref(0)
  const containerHeight = ref(fixedContainerHeight || 600)
  const containerRef = ref<HTMLElement | null>(null)

  // Calculate visible range
  const visibleRange = computed(() => {
    const start = Math.floor(scrollTop.value / itemHeight)
    const end = Math.ceil((scrollTop.value + containerHeight.value) / itemHeight)

    return {
      start: Math.max(0, start - bufferSize),
      end: Math.min(items.length, end + bufferSize),
    }
  })

  // Visible items only
  const visibleItems = computed(() => {
    return items.slice(visibleRange.value.start, visibleRange.value.end)
  })

  // Offset for positioning
  const offsetY = computed(() => {
    return visibleRange.value.start * itemHeight
  })

  // Total height of all items
  const totalHeight = computed(() => {
    return items.length * itemHeight
  })

  // Scroll handler
  const onScroll = (event: Event) => {
    const target = event.target as HTMLElement
    scrollTop.value = target.scrollTop
  }

  // Auto-detect container height
  const updateContainerHeight = () => {
    if (containerRef.value && !fixedContainerHeight) {
      containerHeight.value = containerRef.value.clientHeight
    }
  }

  // Scroll to index
  const scrollToIndex = (index: number, behavior: ScrollBehavior = 'smooth') => {
    if (!containerRef.value) return

    const targetScroll = index * itemHeight
    containerRef.value.scrollTo({
      top: targetScroll,
      behavior,
    })
  }

  // Scroll to top
  const scrollToTop = (behavior: ScrollBehavior = 'smooth') => {
    scrollToIndex(0, behavior)
  }

  // Mount/unmount
  onMounted(() => {
    updateContainerHeight()
    window.addEventListener('resize', updateContainerHeight)
  })

  onUnmounted(() => {
    window.removeEventListener('resize', updateContainerHeight)
  })

  return {
    // Refs
    containerRef,
    scrollTop,

    // Computed
    visibleItems,
    visibleRange,
    offsetY,
    totalHeight,

    // Methods
    onScroll,
    scrollToIndex,
    scrollToTop,
    updateContainerHeight,
  }
}

/**
 * Virtual grid for image thumbnails
 * Supports dynamic column count based on container width
 */
export function useVirtualGrid<T>(
  items: T[],
  options: {
    itemWidth: number
    itemHeight: number
    gap?: number
    bufferRows?: number
  }
) {
  const {
    itemWidth,
    itemHeight,
    gap = 8,
    bufferRows = 2,
  } = options

  const scrollTop = ref(0)
  const containerWidth = ref(800)
  const containerHeight = ref(600)
  const containerRef = ref<HTMLElement | null>(null)

  // Calculate columns
  const columns = computed(() => {
    return Math.floor((containerWidth.value + gap) / (itemWidth + gap))
  })

  // Calculate rows
  const rows = computed(() => {
    return Math.ceil(items.length / columns.value)
  })

  // Row height
  const rowHeight = computed(() => itemHeight + gap)

  // Visible row range
  const visibleRowRange = computed(() => {
    const start = Math.floor(scrollTop.value / rowHeight.value)
    const end = Math.ceil((scrollTop.value + containerHeight.value) / rowHeight.value)

    return {
      start: Math.max(0, start - bufferRows),
      end: Math.min(rows.value, end + bufferRows),
    }
  })

  // Visible items
  const visibleItems = computed(() => {
    const startIndex = visibleRowRange.value.start * columns.value
    const endIndex = visibleRowRange.value.end * columns.value

    return items.slice(startIndex, endIndex).map((item, idx) => ({
      item,
      index: startIndex + idx,
      row: Math.floor((startIndex + idx) / columns.value),
      col: (startIndex + idx) % columns.value,
    }))
  })

  // Offset
  const offsetY = computed(() => {
    return visibleRowRange.value.start * rowHeight.value
  })

  // Total height
  const totalHeight = computed(() => {
    return rows.value * rowHeight.value
  })

  // Scroll handler
  const onScroll = (event: Event) => {
    const target = event.target as HTMLElement
    scrollTop.value = target.scrollTop
  }

  // Update dimensions
  const updateDimensions = () => {
    if (containerRef.value) {
      containerWidth.value = containerRef.value.clientWidth
      containerHeight.value = containerRef.value.clientHeight
    }
  }

  // Scroll to item
  const scrollToItem = (index: number, behavior: ScrollBehavior = 'smooth') => {
    if (!containerRef.value) return

    const row = Math.floor(index / columns.value)
    const targetScroll = row * rowHeight.value

    containerRef.value.scrollTo({
      top: targetScroll,
      behavior,
    })
  }

  // Mount/unmount
  onMounted(() => {
    updateDimensions()
    window.addEventListener('resize', updateDimensions)
  })

  onUnmounted(() => {
    window.removeEventListener('resize', updateDimensions)
  })

  // Watch items for changes
  watch(() => items.length, () => {
    // Reset scroll if items changed dramatically
    if (scrollTop.value > totalHeight.value) {
      scrollTop.value = 0
    }
  })

  return {
    // Refs
    containerRef,
    scrollTop,

    // Computed
    visibleItems,
    columns,
    rows,
    offsetY,
    totalHeight,
    rowHeight,

    // Methods
    onScroll,
    scrollToItem,
    updateDimensions,
  }
}
