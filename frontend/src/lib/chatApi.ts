/**
 * Cloudflare D1 聊天 API 客户端
 * 处理云端聊天历史的 CRUD 操作
 */

import { apiClient } from './api'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface ChatSession {
  id: string
  title: string
  created_at: number
  updated_at: number
}

export interface ChatMessage {
  id: string
  session_id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

export interface CreateSessionRequest {
  title: string
}

export interface UpdateSessionRequest {
  title?: string
}

export interface AddMessageRequest {
  role: 'user' | 'assistant'
  content: string
}

export interface SessionsResponse {
  sessions: ChatSession[]
  total: number
}

export interface MessagesResponse {
  messages: ChatMessage[]
  total: number
}

export interface SessionResponse {
  session: ChatSession
}

export interface MessageResponse {
  message: ChatMessage
}

export interface SearchMessagesResponse {
  messages: ChatMessage[]
  query: string
  total: number
}

export interface D1StatsResponse {
  enabled: boolean
  session_count: number
  message_count: number
  database_name: string
  error?: string
}

export interface ApiResponse {
  success: boolean
  message: string
  data?: any
}

class ChatApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message)
    this.name = 'ChatApiError'
  }
}

/**
 * D1 聊天 API 客户端类
 */
export class ChatApiClient {
  private baseUrl: string
  private headers: Record<string, string>

  constructor() {
    this.baseUrl = API_BASE_URL
    this.headers = apiClient.headers
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`
    
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          ...this.headers,
          ...options.headers,
        },
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new ChatApiError(
          `API request failed: ${response.status} ${response.statusText} - ${errorText}`,
          response.status
        )
      }

      return await response.json()
    } catch (error) {
      if (error instanceof ChatApiError) {
        throw error
      }
      throw new ChatApiError(`Network error: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  /**
   * 获取所有聊天会话
   */
  async getSessions(limit: number = 50): Promise<SessionsResponse> {
    return this.request<SessionsResponse>(`/api/chat/sessions?limit=${limit}`)
  }

  /**
   * 创建新的聊天会话
   */
  async createSession(request: CreateSessionRequest): Promise<SessionResponse> {
    return this.request<SessionResponse>('/api/chat/sessions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })
  }

  /**
   * 获取特定聊天会话
   */
  async getSession(sessionId: string): Promise<SessionResponse> {
    return this.request<SessionResponse>(`/api/chat/sessions/${sessionId}`)
  }

  /**
   * 更新聊天会话
   */
  async updateSession(sessionId: string, request: UpdateSessionRequest): Promise<SessionResponse> {
    return this.request<SessionResponse>(`/api/chat/sessions/${sessionId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })
  }

  /**
   * 删除聊天会话
   */
  async deleteSession(sessionId: string): Promise<ApiResponse> {
    return this.request<ApiResponse>(`/api/chat/sessions/${sessionId}`, {
      method: 'DELETE',
    })
  }

  /**
   * 获取特定会话的消息
   */
  async getMessages(sessionId: string, limit: number = 100): Promise<MessagesResponse> {
    return this.request<MessagesResponse>(`/api/chat/sessions/${sessionId}/messages?limit=${limit}`)
  }

  /**
   * 添加消息到会话
   */
  async addMessage(sessionId: string, request: AddMessageRequest): Promise<MessageResponse> {
    return this.request<MessageResponse>(`/api/chat/sessions/${sessionId}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })
  }

  /**
   * 搜索聊天消息
   */
  async searchMessages(query: string, limit: number = 20): Promise<SearchMessagesResponse> {
    const encodedQuery = encodeURIComponent(query)
    return this.request<SearchMessagesResponse>(`/api/chat/search?q=${encodedQuery}&limit=${limit}`)
  }

  /**
   * 获取 D1 统计信息
   */
  async getStats(): Promise<D1StatsResponse> {
    return this.request<D1StatsResponse>('/api/chat/stats')
  }

  /**
   * 检查 D1 服务是否可用
   */
  async isD1Available(): Promise<boolean> {
    try {
      const stats = await this.getStats()
      return stats.enabled
    } catch (error) {
      console.warn('D1 服务检查失败:', error)
      return false
    }
  }
}

/**
 * 全局 Chat API 客户端实例
 */
export const chatApi = new ChatApiClient()

/**
 * 错误处理工具函数
 */
export function isChatApiError(error: unknown): error is ChatApiError {
  return error instanceof ChatApiError
}

/**
 * 将时间戳转换为可读的日期字符串
 */
export function formatTimestamp(timestamp: number): string {
  return new Date(timestamp).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

/**
 * 从前端消息格式转换为 D1 API 格式
 */
export function convertToD1Message(message: any): AddMessageRequest {
  return {
    role: message.role,
    content: message.content,
  }
}

/**
 * 从 D1 API 格式转换为前端消息格式
 */
export function convertFromD1Message(d1Message: ChatMessage): any {
  return {
    id: d1Message.id,
    role: d1Message.role,
    content: d1Message.content,
    timestamp: new Date(d1Message.timestamp).toISOString(),
  }
}

/**
 * 从前端会话格式转换为 D1 API 格式
 */
export function convertToD1Session(session: any): CreateSessionRequest {
  return {
    title: session.title || '新对话',
  }
}

/**
 * 从 D1 API 格式转换为前端会话格式
 */
export function convertFromD1Session(d1Session: ChatSession): any {
  return {
    id: d1Session.id,
    title: d1Session.title,
    messages: [], // 需要单独获取
    createdAt: new Date(d1Session.created_at).toISOString(),
    updatedAt: new Date(d1Session.updated_at).toISOString(),
    timestamp: new Date(d1Session.updated_at).toISOString(),
  }
}