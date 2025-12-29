export type ContainerSize = { width: number; height: number }
export type ContainerPosition = { left: number; top: number }

export type RootFolderType = 'output' | 'workflows' | 'prompts'

export interface DirectoryItem {
  name: string
  type: 'folder' | 'image' | 'video' | 'audio' | 'workflow' | 'prompt'
  size: number
  fullname: string
  createdAt: number
  updatedAt: number
  onClick?: ($event: MouseEvent) => void
  onDbClick?: ($event: MouseEvent) => void
  onContextMenu?: ($event: MouseEvent) => void
  onDragEnd?: ($event: DragEvent) => void
}

export interface SelectOptions {
  label: string
  value: any
  icon?: string
  command: () => void
}
