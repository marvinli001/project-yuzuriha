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
  timestamp: string
}

export interface ChatRequest {
  message: string
  history: Message[]
}

export interface ChatResponse {
  response: string
  memories?: any[]
}