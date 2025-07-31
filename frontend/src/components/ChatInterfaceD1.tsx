'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { Message, ChatHistory } from '@/types/chat'
import Sidebar from '@/components/Sidebar'
import ChatMessage from '@/components/ChatMessage'
import ChatInput from '@/components/ChatInput'
import { Menu, Plus, Cloud, CloudOff, Loader } from 'lucide-react'
import { UploadedFile } from '../utils/fileUtils'
import { useChatHistory } from '@/hooks/useChatHistory'

// API配置
const API_SECRET_KEY = process.env.NEXT_PUBLIC_API_SECRET_KEY || 'PdL3tU8YgmdAnR8p2cRa';

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [currentChatId, setCurrentChatId] = useState<string>('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)

  // 使用 D1 集成的聊天历史 Hook
  const {
    chatHistories,
    currentSession,
    isCloudEnabled,
    syncStatus,
    lastSyncTime,
    error,
    createSession,
    loadSession,
    updateSession,
    deleteSession,
    addMessage,
    refreshSessions,
    syncFromCloud,
  } = useChatHistory({
    enableCloudSync: true,
    fallbackToLocal: true,
    syncInterval: 5 * 60 * 1000, // 5分钟自动同步
  })

  // 初始化或加载当前会话
  useEffect(() => {
    if (!currentChatId && chatHistories.length === 0) {
      startNewChat()
    } else if (currentChatId && currentSession) {
      setMessages(currentSession.messages)
    }
  }, [currentChatId, currentSession, chatHistories])

  // 优化的滚动到底部函数
  const scrollToBottom = useCallback(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }
  }, [])

  // 节流的滚动处理
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      scrollToBottom()
    }, 100)
    
    return () => clearTimeout(timeoutId)
  }, [messages, scrollToBottom])

  const startNewChat = useCallback(async () => {
    try {
      const newSession = await createSession(`新对话 ${new Date().toLocaleString()}`)
      setCurrentChatId(newSession.id)
      setMessages([])
      setSidebarOpen(false)
    } catch (error) {
      console.error('Failed to create new chat:', error)
      // 回退到本地模式
      const newChatId = `chat_${Date.now()}`
      setCurrentChatId(newChatId)
      setMessages([])
      setSidebarOpen(false)
    }
  }, [createSession])

  const saveCurrentChat = useCallback(async (updatedMessages: Message[]) => {
    if (!currentChatId || updatedMessages.length === 0) return

    try {
      // 更新会话标题（如果是第一条消息）
      if (updatedMessages.length === 2) { // 用户消息 + AI回复
        const title = updatedMessages[0]?.content.slice(0, 40) + 
          (updatedMessages[0]?.content.length > 40 ? '...' : '') || 'New Chat'
        await updateSession(currentChatId, { title })
      }
    } catch (error) {
      console.error('Failed to save chat:', error)
    }
  }, [currentChatId, updateSession])

  const loadChat = useCallback(async (chatId: string) => {
    try {
      const session = await loadSession(chatId)
      if (session) {
        setCurrentChatId(chatId)
        setMessages(session.messages)
        setSidebarOpen(false)
      }
    } catch (error) {
      console.error('Failed to load chat:', error)
    }
  }, [loadSession])

  const deleteChatHandler = useCallback(async (chatId: string) => {
    try {
      await deleteSession(chatId)
      
      if (chatId === currentChatId) {
        await startNewChat()
      }
    } catch (error) {
      console.error('Failed to delete chat:', error)
    }
  }, [currentChatId, deleteSession, startNewChat])

  // 修改发送消息函数支持文件和 D1 存储
  const sendMessage = useCallback(async (content: string, files?: UploadedFile[]) => {
    if ((!content.trim() && !files?.length) || isLoading) return

    // 创建用户消息
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: files?.length ? `${content}\n\n附件: ${files.map(f => f.filename).join(', ')}` : content,
      timestamp: new Date().toISOString()
    }

    const updatedMessages = [...messages, userMessage]
    setMessages(updatedMessages)
    setIsLoading(true)

    try {
      // 添加用户消息到 D1（如果可用）
      if (currentChatId && isCloudEnabled) {
        await addMessage(currentChatId, userMessage)
      }

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${API_SECRET_KEY}`,
        },
        body: JSON.stringify({
          message: content,
          history: messages.map(msg => ({
            role: msg.role,
            content: msg.content
          })),
          files: files || [],
          session_id: currentChatId // 传递会话ID给后端进行双写
        }),
      })

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('API密钥验证失败，请检查配置')
        }
        throw new Error('Failed to send message')
      }

      const data = await response.json()
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.response,
        timestamp: new Date().toISOString(),
      }

      const finalMessages = [...updatedMessages, assistantMessage]
      setMessages(finalMessages)

      // 后端的双写机制会自动处理 AI 回复的存储
      // 但我们仍然需要更新本地状态和保存聊天
      await saveCurrentChat(finalMessages)

    } catch (error) {
      console.error('Error sending message:', error)
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: '抱歉，发送消息时出现错误。请稍后重试。',
        timestamp: new Date().toISOString(),
      }
      const finalMessages = [...updatedMessages, errorMessage]
      setMessages(finalMessages)
      await saveCurrentChat(finalMessages)
    } finally {
      setIsLoading(false)
    }
  }, [messages, isLoading, currentChatId, isCloudEnabled, addMessage, saveCurrentChat])

  // 手动同步按钮
  const handleSync = useCallback(async () => {
    try {
      await syncFromCloud()
    } catch (error) {
      console.error('Manual sync failed:', error)
    }
  }, [syncFromCloud])

  // 云端状态指示器
  const renderCloudStatus = () => {
    if (!isCloudEnabled) {
      return (
        <div className="flex items-center space-x-1 text-gray-400">
          <CloudOff className="w-3 h-3" />
          <span className="text-xs">本地模式</span>
        </div>
      )
    }

    const getStatusColor = () => {
      switch (syncStatus) {
        case 'syncing': return 'text-blue-500'
        case 'success': return 'text-green-500'
        case 'error': return 'text-red-500'
        default: return 'text-gray-500'
      }
    }

    return (
      <div className="flex items-center space-x-1">
        {syncStatus === 'syncing' ? (
          <Loader className="w-3 h-3 animate-spin text-blue-500" />
        ) : (
          <Cloud className={`w-3 h-3 ${getStatusColor()}`} />
        )}
        <span className={`text-xs ${getStatusColor()}`}>
          {syncStatus === 'syncing' && '同步中...'}
          {syncStatus === 'success' && '已同步'}
          {syncStatus === 'error' && '同步失败'}
          {syncStatus === 'idle' && '云端模式'}
        </span>
        {lastSyncTime && syncStatus === 'success' && (
          <span className="text-xs text-gray-400">
            {new Date(lastSyncTime).toLocaleTimeString()}
          </span>
        )}
      </div>
    )
  }

  return (
    <div className="h-screen flex bg-gray-50">
      <Sidebar 
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onNewChat={startNewChat}
        chatHistory={chatHistories}
        currentChatId={currentChatId}
        onLoadChat={loadChat}
        onDeleteChat={deleteChatHandler}
      />

      <div className="flex-1 flex flex-col min-h-0">
        <header className="flex-shrink-0 bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => setSidebarOpen(true)}
              className="flex items-center space-x-2 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
            >
              <Plus className="w-4 h-4" />
              <span>新对话</span>
            </button>
            
            {/* 同步按钮 */}
            {isCloudEnabled && (
              <button
                onClick={handleSync}
                disabled={syncStatus === 'syncing'}
                className="flex items-center space-x-1 px-2 py-1 text-xs text-gray-600 hover:bg-gray-100 rounded transition-colors disabled:opacity-50"
                title="手动同步云端数据"
              >
                {syncStatus === 'syncing' ? (
                  <Loader className="w-3 h-3 animate-spin" />
                ) : (
                  <Cloud className="w-3 h-3" />
                )}
                <span>同步</span>
              </button>
            )}
          </div>
          
          <div className="flex items-center space-x-4">
            {renderCloudStatus()}
            <div className="flex items-center space-x-2">
              <div className="text-sm font-medium text-gray-900">Project Yuzuriha</div>
              <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
            </div>
          </div>
        </header>

        {/* 错误提示 */}
        {error && (
          <div className="bg-red-50 border-b border-red-200 px-4 py-2">
            <div className="text-sm text-red-600">
              ⚠️ {error}
            </div>
          </div>
        )}

        <div className="flex-1 flex flex-col min-h-0">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full px-4">
              <div className="text-center mb-8">
                <h1 className="text-4xl font-semibold text-gray-900 mb-2">你好，我是 Yuzuriha</h1>
                <p className="text-gray-600">
                  {isCloudEnabled ? '云端聊天历史已启用，对话将自动同步。' : '使用本地存储模式，数据保存在您的设备上。'}
                </p>
              </div>
              <div className="w-full max-w-2xl">
                <ChatInput 
                  onSendMessage={sendMessage} 
                  disabled={isLoading} 
                  hasMessages={false}
                />
              </div>
            </div>
          ) : (
            <>
              <div 
                ref={messagesContainerRef}
                className="flex-1 overflow-y-auto px-4 py-6"
                style={{ minHeight: 0 }}
              >
                <div className="max-w-4xl mx-auto space-y-6">
                  {messages.map((message) => (
                    <ChatMessage key={message.id} message={message} />
                  ))}
                  {isLoading && (
                    <div className="flex items-start space-x-3">
                      <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
                        <div className="w-3 h-3 bg-white rounded-full animate-pulse"></div>
                      </div>
                      <div className="flex-1 bg-gray-100 rounded-lg px-4 py-3">
                        <div className="flex space-x-1">
                          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
              <ChatInput 
                onSendMessage={sendMessage} 
                disabled={isLoading} 
                hasMessages={true}
              />
              <div ref={messagesEndRef} />
            </>
          )}
        </div>
      </div>
    </div>
  )
}