/**
 * 聊天历史管理 Hook
 * 支持 localStorage 和 Cloudflare D1 云端同步
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import {
  chatApi,
  ChatSession,
  ChatMessage,
  isChatApiError,
  convertFromD1Session,
  convertFromD1Message,
  convertToD1Session,
  convertToD1Message,
} from '../lib/chatApi'
import { ChatHistory, Message } from '../types/chat'

interface UseChatHistoryOptions {
  enableCloudSync?: boolean
  fallbackToLocal?: boolean
  syncInterval?: number // 自动同步间隔（毫秒）
}

interface UseChatHistoryReturn {
  // 状态
  chatHistories: ChatHistory[]
  currentSession: ChatHistory | null
  isLoading: boolean
  isCloudEnabled: boolean
  syncStatus: 'idle' | 'syncing' | 'error' | 'success'
  lastSyncTime: Date | null
  error: string | null

  // 操作
  createSession: (title?: string) => Promise<ChatHistory>
  loadSession: (sessionId: string) => Promise<ChatHistory | null>
  updateSession: (sessionId: string, updates: Partial<ChatHistory>) => Promise<void>
  deleteSession: (sessionId: string) => Promise<void>
  addMessage: (sessionId: string, message: Message) => Promise<void>
  refreshSessions: () => Promise<void>
  syncToCloud: () => Promise<void>
  syncFromCloud: () => Promise<void>
  migrateToCloud: () => Promise<void>

  // 工具函数
  searchMessages: (query: string) => Promise<Array<ChatMessage & { session_title?: string }>>
  getStats: () => Promise<any>
}

const STORAGE_KEY = 'chat-histories'
const LAST_SYNC_KEY = 'last-sync-time'

export function useChatHistory(options: UseChatHistoryOptions = {}): UseChatHistoryReturn {
  const {
    enableCloudSync = true,
    fallbackToLocal = true,
    syncInterval = 5 * 60 * 1000, // 5分钟
  } = options

  // 状态
  const [chatHistories, setChatHistories] = useState<ChatHistory[]>([])
  const [currentSession, setCurrentSession] = useState<ChatHistory | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isCloudEnabled, setIsCloudEnabled] = useState(false)
  const [syncStatus, setSyncStatus] = useState<'idle' | 'syncing' | 'error' | 'success'>('idle')
  const [lastSyncTime, setLastSyncTime] = useState<Date | null>(null)
  const [error, setError] = useState<string | null>(null)

  // 引用
  const syncIntervalRef = useRef<NodeJS.Timeout | null>(null)

  // 检查云端服务可用性
  const checkCloudAvailability = useCallback(async () => {
    if (!enableCloudSync) return false

    try {
      const available = await chatApi.isD1Available()
      setIsCloudEnabled(available)
      return available
    } catch (error) {
      console.warn('检查云端服务失败:', error)
      setIsCloudEnabled(false)
      return false
    }
  }, [enableCloudSync])

  // 从 localStorage 加载数据
  const loadFromLocal = useCallback((): ChatHistory[] => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        const parsed = JSON.parse(stored)
        return Array.isArray(parsed) ? parsed : []
      }
    } catch (error) {
      console.error('从本地存储加载数据失败:', error)
    }
    return []
  }, [])

  // 保存到 localStorage
  const saveToLocal = useCallback((histories: ChatHistory[]) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(histories))
    } catch (error) {
      console.error('保存到本地存储失败:', error)
    }
  }, [])

  // 从云端加载数据
  const loadFromCloud = useCallback(async (): Promise<ChatHistory[]> => {
    if (!isCloudEnabled) return []

    try {
      const response = await chatApi.getSessions()
      const cloudHistories: ChatHistory[] = []

      for (const session of response.sessions) {
        const messagesResponse = await chatApi.getMessages(session.id)
        const messages = messagesResponse.messages.map(convertFromD1Message)

        cloudHistories.push({
          ...convertFromD1Session(session),
          messages,
        })
      }

      return cloudHistories
    } catch (error) {
      console.error('从云端加载数据失败:', error)
      throw error
    }
  }, [isCloudEnabled])

  // 同步到云端
  const syncToCloud = useCallback(async () => {
    if (!isCloudEnabled || !enableCloudSync) return

    setSyncStatus('syncing')
    try {
      // 这里可以实现将本地数据同步到云端的逻辑
      // 目前主要依赖实时双写，这里作为备份机制
      setSyncStatus('success')
      setLastSyncTime(new Date())
      localStorage.setItem(LAST_SYNC_KEY, new Date().toISOString())
    } catch (error) {
      console.error('同步到云端失败:', error)
      setSyncStatus('error')
      setError(error instanceof Error ? error.message : '同步失败')
    }
  }, [isCloudEnabled, enableCloudSync])

  // 从云端同步
  const syncFromCloud = useCallback(async () => {
    if (!isCloudEnabled || !enableCloudSync) return

    setSyncStatus('syncing')
    try {
      const cloudHistories = await loadFromCloud()
      setChatHistories(cloudHistories)
      
      // 合并本地数据（如果需要）
      if (fallbackToLocal) {
        const localHistories = loadFromLocal()
        const mergedHistories = [...cloudHistories]
        
        // 简单的合并逻辑：添加云端没有的本地会话
        localHistories.forEach(localHistory => {
          const exists = cloudHistories.some(cloudHistory => cloudHistory.id === localHistory.id)
          if (!exists) {
            mergedHistories.push(localHistory)
          }
        })
        
        setChatHistories(mergedHistories)
        saveToLocal(mergedHistories)
      }

      setSyncStatus('success')
      setLastSyncTime(new Date())
      localStorage.setItem(LAST_SYNC_KEY, new Date().toISOString())
    } catch (error) {
      console.error('从云端同步失败:', error)
      setSyncStatus('error')
      setError(error instanceof Error ? error.message : '同步失败')
      
      // 回退到本地数据
      if (fallbackToLocal) {
        const localHistories = loadFromLocal()
        setChatHistories(localHistories)
      }
    }
  }, [isCloudEnabled, enableCloudSync, fallbackToLocal, loadFromCloud, loadFromLocal, saveToLocal])

  // 创建会话
  const createSession = useCallback(async (title?: string): Promise<ChatHistory> => {
    const sessionTitle = title || `新对话 ${new Date().toLocaleString()}`
    
    try {
      if (isCloudEnabled) {
        // 创建云端会话
        const response = await chatApi.createSession({ title: sessionTitle })
        const newSession = {
          ...convertFromD1Session(response.session),
          messages: [],
        }
        
        setChatHistories(prev => [newSession, ...prev])
        return newSession
      } else {
        // 创建本地会话
        const newSession: ChatHistory = {
          id: Date.now().toString(),
          title: sessionTitle,
          messages: [],
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          timestamp: new Date().toISOString(),
        }
        
        const updatedHistories = [newSession, ...chatHistories]
        setChatHistories(updatedHistories)
        saveToLocal(updatedHistories)
        return newSession
      }
    } catch (error) {
      console.error('创建会话失败:', error)
      throw error
    }
  }, [isCloudEnabled, chatHistories, saveToLocal])

// 在 loadSession 函数中添加防重复加载逻辑
const loadSession = useCallback(async (sessionId: string): Promise<ChatHistory | null> => {
  // 防止重复加载同一个会话
  if (currentSession?.id === sessionId) {
    return currentSession
  }

  try {
    if (isCloudEnabled) {
      const [sessionResponse, messagesResponse] = await Promise.all([
        chatApi.getSession(sessionId),
        chatApi.getMessages(sessionId, 100)
      ])
      
      const session: ChatHistory = {
        id: sessionResponse.session.id,
        title: sessionResponse.session.title,
        messages: messagesResponse.messages.map(convertFromD1Message),
        createdAt: new Date(sessionResponse.session.created_at).toISOString(),
        updatedAt: new Date(sessionResponse.session.updated_at).toISOString(),
        timestamp: new Date(sessionResponse.session.created_at).toISOString(),
      }
      
      setCurrentSession(session)
      return session
    } else {
      const session = chatHistories.find(h => h.id === sessionId) || null
      setCurrentSession(session)
      return session
    }
  } catch (error) {
    console.error('加载会话失败:', error)
    setError(error instanceof Error ? error.message : '加载失败')
    return null
  }
}, [isCloudEnabled, currentSession?.id, chatHistories]) // 添加 currentSession?.id 依赖

  // 更新会话
  const updateSession = useCallback(async (sessionId: string, updates: Partial<ChatHistory>) => {
    try {
      if (isCloudEnabled && updates.title) {
        await chatApi.updateSession(sessionId, { title: updates.title })
      }
      
      setChatHistories(prev => 
        prev.map(history => 
          history.id === sessionId 
            ? { ...history, ...updates, updatedAt: new Date().toISOString() }
            : history
        )
      )
      
      if (!isCloudEnabled) {
        const updatedHistories = chatHistories.map(history => 
          history.id === sessionId 
            ? { ...history, ...updates, updatedAt: new Date().toISOString() }
            : history
        )
        saveToLocal(updatedHistories)
      }
    } catch (error) {
      console.error('更新会话失败:', error)
      throw error
    }
  }, [isCloudEnabled, chatHistories, saveToLocal])

// 修改 deleteSession 函数，添加状态清理
const deleteSession = useCallback(async (sessionId: string) => {
  try {
    if (isCloudEnabled) {
      await chatApi.deleteSession(sessionId)
    }
    
    // 更新本地状态
    setChatHistories(prev => prev.filter(history => history.id !== sessionId))
    
    // 如果删除的是当前会话，清除当前会话状态
    if (currentSession?.id === sessionId) {
      setCurrentSession(null)
    }
    
    if (!isCloudEnabled) {
      const updatedHistories = chatHistories.filter(history => history.id !== sessionId)
      saveToLocal(updatedHistories)
    }
  } catch (error) {
    console.error('删除会话失败:', error)
    throw error
  }
}, [isCloudEnabled, currentSession?.id, chatHistories, saveToLocal]) // 修改依赖项

  // 添加消息
  const addMessage = useCallback(async (sessionId: string, message: Message) => {
    try {
      if (isCloudEnabled) {
        await chatApi.addMessage(sessionId, convertToD1Message(message))
      }
      
      setChatHistories(prev => 
        prev.map(history => 
          history.id === sessionId 
            ? { 
                ...history, 
                messages: [...history.messages, message],
                updatedAt: new Date().toISOString()
              }
            : history
        )
      )
      
      if (currentSession?.id === sessionId) {
        setCurrentSession(prev => prev ? {
          ...prev,
          messages: [...prev.messages, message],
          updatedAt: new Date().toISOString()
        } : null)
      }
      
      if (!isCloudEnabled) {
        const updatedHistories = chatHistories.map(history => 
          history.id === sessionId 
            ? { 
                ...history, 
                messages: [...history.messages, message],
                updatedAt: new Date().toISOString()
              }
            : history
        )
        saveToLocal(updatedHistories)
      }
    } catch (error) {
      console.error('添加消息失败:', error)
      throw error
    }
  }, [isCloudEnabled, currentSession, chatHistories, saveToLocal])

  // 刷新会话列表
  const refreshSessions = useCallback(async () => {
    setIsLoading(true)
    try {
      if (isCloudEnabled) {
        await syncFromCloud()
      } else {
        const localHistories = loadFromLocal()
        setChatHistories(localHistories)
      }
    } catch (error) {
      console.error('刷新会话列表失败:', error)
      setError(error instanceof Error ? error.message : '刷新失败')
    } finally {
      setIsLoading(false)
    }
  }, [isCloudEnabled, syncFromCloud, loadFromLocal])

  // 迁移到云端
  const migrateToCloud = useCallback(async () => {
    if (!isCloudEnabled) {
      throw new Error('云端服务不可用')
    }

    setIsLoading(true)
    try {
      const localHistories = loadFromLocal()
      
      for (const history of localHistories) {
        // 创建云端会话
        const sessionResponse = await chatApi.createSession({ title: history.title })
        
        // 添加消息
        for (const message of history.messages) {
          await chatApi.addMessage(sessionResponse.session.id, convertToD1Message(message))
        }
      }
      
      // 重新加载云端数据
      await syncFromCloud()
    } catch (error) {
      console.error('迁移到云端失败:', error)
      throw error
    } finally {
      setIsLoading(false)
    }
  }, [isCloudEnabled, loadFromLocal, syncFromCloud])

  // 搜索消息
  const searchMessages = useCallback(async (query: string) => {
    if (!isCloudEnabled) {
      // 本地搜索
      const results: Array<ChatMessage & { session_title?: string }> = []
      chatHistories.forEach(history => {
        history.messages.forEach(message => {
          if (message.content.toLowerCase().includes(query.toLowerCase())) {
            results.push({
              id: message.id,
              session_id: history.id,
              role: message.role,
              content: message.content,
              timestamp: new Date(message.timestamp).getTime(),
              session_title: history.title,
            })
          }
        })
      })
      return results
    }
    
    const response = await chatApi.searchMessages(query)
    return response.messages.map(msg => ({
      ...msg,
      session_title: '',
    }))
  }, [isCloudEnabled, chatHistories])

  // 获取统计信息
  const getStats = useCallback(async () => {
    if (isCloudEnabled) {
      return await chatApi.getStats()
    }
    
    const totalSessions = chatHistories.length
    const totalMessages = chatHistories.reduce((sum, history) => sum + history.messages.length, 0)
    
    return {
      enabled: false,
      session_count: totalSessions,
      message_count: totalMessages,
      database_name: 'localStorage',
    }
  }, [isCloudEnabled, chatHistories])

  // 初始化
  useEffect(() => {
    const init = async () => {
      setIsLoading(true)
      try {
        // 检查云端可用性
        await checkCloudAvailability()
        
        // 加载上次同步时间
        const lastSync = localStorage.getItem(LAST_SYNC_KEY)
        if (lastSync) {
          setLastSyncTime(new Date(lastSync))
        }
        
        // 刷新数据
        await refreshSessions()
      } catch (error) {
        console.error('初始化失败:', error)
        setError(error instanceof Error ? error.message : '初始化失败')
      } finally {
        setIsLoading(false)
      }
    }

    init()
  }, [checkCloudAvailability, refreshSessions])

  // 自动同步
  useEffect(() => {
    if (!isCloudEnabled || !enableCloudSync || syncInterval <= 0) return

    syncIntervalRef.current = setInterval(() => {
      syncFromCloud()
    }, syncInterval)

    return () => {
      if (syncIntervalRef.current) {
        clearInterval(syncIntervalRef.current)
      }
    }
  }, [isCloudEnabled, enableCloudSync, syncInterval, syncFromCloud])

  return {
    // 状态
    chatHistories,
    currentSession,
    isLoading,
    isCloudEnabled,
    syncStatus,
    lastSyncTime,
    error,

    // 操作
    createSession,
    loadSession,
    updateSession,
    deleteSession,
    addMessage,
    refreshSessions,
    syncToCloud,
    syncFromCloud,
    migrateToCloud,

    // 工具函数
    searchMessages,
    getStats,
  }
}