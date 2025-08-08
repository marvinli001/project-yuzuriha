export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

export interface UploadedFile {
  id: string
  filename: string
  type: 'image' | 'document' | 'audio' | 'other'
  size: number
  path: string
  url?: string
  // 添加 File 对象的其他属性以兼容
  lastModified?: number
  name?: string
  webkitRelativePath?: string
  arrayBuffer?: ArrayBuffer
}

export interface ChatHistory {
  id: string
  title: string
  messages: Message[]
  createdAt: string
  updatedAt: string
  timestamp: string
}

export interface ChatRequest {
  message: string
  history: Message[]
  files?: UploadedFile[]
}

export interface ChatResponse {
  response: string
  memories?: MemoryResult[]
}

export interface MemoryResult {
  text: string
  score: number
  timestamp: number
}

export interface HealthStatus {
  status: 'healthy' | 'unhealthy'
  timestamp: string
  services: {
    openai: boolean
    milvus: boolean
    supermemory: boolean
  }
}

// 添加 ChatInput 组件的 Props 接口
export interface ChatInputProps {
  onSendMessage: (content: string, files?: UploadedFile[]) => Promise<void>
  disabled?: boolean
  hasMessages?: boolean
}