import { app } from 'scripts/comfyAPI'

type DraggedItem = {
  fullname: string
  name: string
  type: 'folder' | 'image' | 'video' | 'audio'
}

const MIME = 'application/x-comfyui-image-browsing'

function isInsidePlugin(target: EventTarget | null) {
  // PrimeVue dialogs are teleported to <body>, so containment checks against our mount
  // container won't work reliably. We instead detect by known plugin dialog/tree classes.
  if (!(target instanceof Element)) return false
  return !!target.closest('.folder-tree, .p-dialog, .p-dialog-mask, .p-contextmenu')
}

function parseDraggedItems(ev: DragEvent): DraggedItem[] | null {
  try {
    const raw = ev.dataTransfer?.getData(MIME)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    const items = parsed?.items ?? []
    if (!Array.isArray(items)) return null
    return items as DraggedItem[]
  } catch {
    return null
  }
}

async function fetchAsFile(item: DraggedItem): Promise<File> {
  const response = await fetch(`/image-browsing${item.fullname}`)
  const blob = await response.blob()
  const fallbackType =
    item.type === 'video'
      ? 'video/mp4'
      : item.type === 'audio'
        ? 'audio/mpeg'
        : 'image/png'
  return new File([blob], item.name, { type: blob.type || fallbackType })
}

async function uploadToInput(file: File): Promise<string> {
  const form = new FormData()
  // ComfyUI core has POST /upload/image. It places the file into ComfyUI/input.
  // Many nodes (including LoadImage) read from that folder.
  form.append('image', file, file.name)

  const res = await fetch('/upload/image', { method: 'POST', body: form })
  if (!res.ok) {
    throw new Error(`Upload failed: ${res.status}`)
  }
  const data = await res.json().catch(() => ({}))
  const name = data?.name || data?.filename || file.name
  const subfolder = data?.subfolder || ''
  return subfolder ? `${subfolder}/${name}` : name
}

function normalizeNodeName(node: any): string {
  const s = String(node?.title || node?.type || node?.comfyClass || '')
  return s.toLowerCase().replace(/\s+/g, '')
}

function getNodeAtEvent(ev: DragEvent): any | null {
  try {
    const canvas: any = (app as any)?.canvas
    const graph: any = (app as any)?.graph
    if (!canvas || !graph) return null

    // LiteGraph provides this helper on LGraphCanvas in ComfyUI builds
    const pos: any = canvas.convertEventToCanvasPos
      ? canvas.convertEventToCanvasPos([ev.clientX, ev.clientY])
      : canvas.convertEventToCanvasOffset
        ? canvas.convertEventToCanvasOffset(ev)
        : null

    if (!pos || pos.length < 2) return null
    const x = pos[0]
    const y = pos[1]

    if (typeof graph.getNodeOnPos === 'function') return graph.getNodeOnPos(x, y)
    if (typeof canvas.getNodeOnPos === 'function') return canvas.getNodeOnPos(x, y)
  } catch {
    // ignore
  }
  return null
}

function setNodeWidgetValue(node: any, value: string, keys: string[]) {
  const widgets = node?.widgets
  if (!Array.isArray(widgets) || widgets.length === 0) return false

  const lower = (v: any) => String(v ?? '').toLowerCase()
  const w =
    widgets.find((wi: any) => keys.includes(lower(wi?.name)) || keys.includes(lower(wi?.label))) ?? widgets[0]
  if (!w) return false

  w.value = value

  // Best-effort: trigger callbacks so the UI updates immediately.
  try {
    if (typeof w.callback === 'function') w.callback(value, app, node)
  } catch {}
  try {
    if (typeof node.onWidgetChanged === 'function') node.onWidgetChanged(w.name, value, w)
  } catch {}

  try {
    ;(app as any)?.graph?.setDirtyCanvas?.(true, true)
    ;(app as any)?.canvas?.setDirty?.(true, true)
  } catch {}

  return true
}

/**
 * Enables:
 * - Drag image -> LoadImage node (uploads to input and sets widget, does NOT auto-load workflow)
 * - Drag video -> LoadVideo node (uploads to input and sets widget)
 * - Drag image -> empty graph loads workflow (embedded metadata)
 */
export function installGraphDropHandler() {
  const w = window as any
  if (w.__comfyuiImageBrowsingDropInstalled) return
  w.__comfyuiImageBrowsingDropInstalled = true

  const onDragOver = (ev: DragEvent) => {
    const items = parseDraggedItems(ev)
    if (!items) return
    if (isInsidePlugin(ev.target)) return
    ev.preventDefault()
    if (ev.dataTransfer) ev.dataTransfer.dropEffect = 'copy'
  }

  const onDrop = async (ev: DragEvent) => {
    const items = parseDraggedItems(ev)
    if (!items) return
    if (isInsidePlugin(ev.target)) return

    // We are handling this drop; prevent ComfyUI's default URL/file handler from also running.
    ev.preventDefault()
    ev.stopPropagation()
    ;(ev as any).stopImmediatePropagation?.()

    const first = items[0]
    if (!first) return

    const node = getNodeAtEvent(ev)
    const n = normalizeNodeName(node)

    // Drop on node: treat as file input, not as workflow.
    if (node && first.type === 'image' && n.includes('loadimage')) {
      try {
        const file = await fetchAsFile(first)
        const uploaded = await uploadToInput(file)
        setNodeWidgetValue(node, uploaded, ['image', 'filename', 'file'])
      } catch (e) {
        console.warn('[ImageBrowsing] Failed to drop image onto LoadImage:', e)
      }
      return
    }

    if (
      node &&
      first.type === 'video' &&
      (n.includes('loadvideo') || n.includes('vhs_loadvideo') || n.includes('vhsloadvideo'))
    ) {
      try {
        const file = await fetchAsFile(first)
        const uploaded = await uploadToInput(file)
        setNodeWidgetValue(node, uploaded, ['video', 'filename', 'file'])
      } catch (e) {
        console.warn('[ImageBrowsing] Failed to drop video onto LoadVideo:', e)
      }
      return
    }

    // Empty graph: load workflow only for images.
    if (first.type === 'image') {
      try {
        const file = await fetchAsFile(first)
        app.handleFile(file)
      } catch (e) {
        console.warn('[ImageBrowsing] Failed to drop image to load workflow:', e)
      }
    }
  }

  // Capture phase so we can prevent the browser from navigating away on drop.
  document.addEventListener('dragover', onDragOver, true)
  document.addEventListener('drop', onDrop, true)
}
