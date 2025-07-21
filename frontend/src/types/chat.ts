export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

export interface ChatHistory {
  id: string
  title: string
  messages: Message[]
  createdAt: string
  updatedAt: string
}

export interface ChatRequest {
  message: string
  history: Message[]
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