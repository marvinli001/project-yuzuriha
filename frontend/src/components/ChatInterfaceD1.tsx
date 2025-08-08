import React, { useState, useRef, useCallback, useEffect } from 'react'
import { Message, UploadedFile } from '../types/chat'
import { useChatHistory } from '../hooks/useChatHistory'
import ChatInput from './ChatInput'
import MessageBubble from './MessageBubble'
import Sidebar from './Sidebar'
import { Menu, Wifi, WifiOff, CheckCircle, XCircle, Clock, Bot } from 'lucide-react'

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
    syncInterval: 5 * 60 * 1000,
  })

  // 初始化
  useEffect(() => {
    if (!currentChatId && chatHistories.length === 0) {
      startNewChat()
    } else if (currentChatId && currentSession && currentSession.id === currentChatId) {
      setMessages(currentSession.messages)
    }
  }, [currentChatId, currentSession])

  const scrollToBottom = useCallback(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }
  }, [])

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
      const newChatId = `chat_${Date.now()}`
      setCurrentChatId(newChatId)
      setMessages([])
      setSidebarOpen(false)
    }
  }, [createSession])

  const saveCurrentChat = useCallback(async (updatedMessages: Message[]) => {
    if (!currentChatId || updatedMessages.length === 0) return

    try {
      if (updatedMessages.length === 2) {
        const title = updatedMessages[0]?.content.slice(0, 40) + 
          (updatedMessages[0]?.content.length > 40 ? '...' : '') || 'New Chat'
        await updateSession(currentChatId, { title })
      }
    } catch (error) {
      console.error('Failed to save chat:', error)
    }
  }, [currentChatId, updateSession])

  const loadChat = useCallback(async (chatId: string) => {
    if (chatId === currentChatId) return
    
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
  }, [currentChatId, loadSession])

  const deleteChatHandler = useCallback(async (chatId: string) => {
    try {
      await deleteSession(chatId)
      
      if (chatId === currentChatId) {
        const remainingChats = chatHistories.filter(chat => chat.id !== chatId)
        if (remainingChats.length > 0) {
          const latestChat = remainingChats.sort((a, b) => 
            new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
          )[0]
          await loadChat(latestChat.id)
        } else {
          setCurrentChatId('')
          setMessages([])
          await startNewChat()
        }
      }
    } catch (error) {
      console.error('Failed to delete chat:', error)
    }
  }, [currentChatId, chatHistories, deleteSession, loadChat, startNewChat])

  // 修改 sendMessage 函数，确保类型匹配
  const sendMessage = useCallback(async (content: string, files?: UploadedFile[]): Promise<void> => {
    if (!content.trim() || isLoading) return

    let sessionId = currentChatId
    if (!sessionId) {
      try {
        const newSession = await createSession(`新对话 ${new Date().toLocaleString()}`)
        sessionId = newSession.id
        setCurrentChatId(sessionId)
      } catch (error) {
        console.error('Failed to create session:', error)
        return
      }
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    }

    const updatedMessages = [...messages, userMessage]
    setMessages(updatedMessages)
    setIsLoading(true)

    try {
      if (isCloudEnabled) {
        await addMessage(sessionId, userMessage)
      }

      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: content,
          history: updatedMessages.map(msg => ({
            role: msg.role,
            content: msg.content
          })),
          files: files || [],
          session_id: sessionId
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

      await saveCurrentChat(finalMessages)
    } catch (error) {
      console.error('Failed to send message:', error)
      setMessages(messages)
    } finally {
      setIsLoading(false)
    }
  }, [messages, isLoading, currentChatId, createSession, addMessage, isCloudEnabled, saveCurrentChat])

  const renderSyncStatus = () => {
    if (!isCloudEnabled) return null

    return (
      <div className="flex items-center space-x-2 px-3 py-1 bg-gray-100 rounded-full text-xs">
        {syncStatus === 'syncing' && <Clock size={12} className="text-yellow-500" />}
        {syncStatus === 'success' && <CheckCircle size={12} className="text-green-500" />}
        {syncStatus === 'error' && <XCircle size={12} className="text-red-500" />}
        <span className="text-gray-600">
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
        <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-2 rounded-lg hover:bg-gray-100 transition-colors md:hidden"
              aria-label="打开侧边栏"
            >
              <Menu size={20} className="text-gray-600" />
            </button>
            <h1 className="text-lg font-semibold text-gray-900">
              {currentSession?.title || 'Yuzuriha AI'}
            </h1>
          </div>
          
          <div className="flex items-center space-x-3">
            {renderSyncStatus()}
            <div className="flex items-center text-sm text-gray-500">
              {isCloudEnabled ? (
                <Wifi size={16} className="text-green-500" />
              ) : (
                <WifiOff size={16} className="text-gray-400" />
              )}
            </div>
          </div>
        </header>

<div 
  ref={messagesContainerRef}
  className="flex-1 overflow-y-auto"
>
  {messages.length === 0 ? (
    <div className="flex flex-col items-center justify-center h-full text-center px-4">
      <div className="max-w-md">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          你好，我是 Yuzuriha
        </h2>
        <p className="text-gray-600 mb-8">
          云端数据的忠实管家，对话者自己的助手。
        </p>
      </div>
    </div>
  ) : (
    <>
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
      {isLoading && (
        <div className="bg-gray-50 py-6">
          <div className="max-w-3xl mx-auto px-4">
            <div className="flex gap-4">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 rounded-full flex items-center justify-center bg-gray-600">
                  <Bot size={16} className="text-white" />
                </div>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-sm font-semibold text-gray-900">Yuzuriha</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  </div>
                  <span className="text-gray-500 text-sm">正在思考...</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )}
  <div ref={messagesEndRef} />
</div>

        <div className="border-t border-gray-200 bg-white p-4">
          <ChatInput 
            onSendMessage={sendMessage}
            disabled={isLoading}
            hasMessages={messages.length > 0}
          />
        </div>
      </div>
    </div>
  )
}