import { UploadedFile } from '../utils/fileUtils'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  files?: UploadedFile[] // 添加文件字段
}

export interface ChatHistory {
  id: string
  title: string
  messages: Message[]
  timestamp: number
}