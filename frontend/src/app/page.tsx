'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { Message, ChatHistory } from '@/types/chat'
import Sidebar from '@/components/Sidebar'
import ChatMessage from '@/components/ChatMessage'
import ChatInput from '@/components/ChatInput'
import { Menu, Plus} from 'lucide-react'
import { UploadedFile } from '../utils/fileUtils'

// API配置
const API_SECRET_KEY = process.env.NEXT_PUBLIC_API_SECRET_KEY || 'PdL3tU8YgmdAnR8p2cRa';

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [chatHistory, setChatHistory] = useState<ChatHistory[]>([])
  const [currentChatId, setCurrentChatId] = useState<string>('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)

  // 初始化聊天历史
  useEffect(() => {
    const savedHistory = localStorage.getItem('yuzuriha_chat_history')
    if (savedHistory) {
      try {
        const parsed = JSON.parse(savedHistory)
        setChatHistory(parsed)
      } catch (error) {
        console.error('Error parsing chat history:', error)
      }
    }
    
    if (!currentChatId) {
      startNewChat()
    }
  }, [currentChatId])

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

  const startNewChat = useCallback(() => {
    const newChatId = `chat_${Date.now()}`
    setCurrentChatId(newChatId)
    setMessages([])
    setSidebarOpen(false)
  }, [])

  const saveCurrentChat = useCallback((updatedMessages: Message[]) => {
    if (!currentChatId || updatedMessages.length === 0) return

    const chatTitle = updatedMessages[0]?.content.slice(0, 40) + (updatedMessages[0]?.content.length > 40 ? '...' : '') || 'New Chat'
    
    const chatData: ChatHistory = {
      id: currentChatId,
      title: chatTitle,
      messages: updatedMessages,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      timestamp: new Date().toISOString()
    }

    setChatHistory(prev => {
      const updatedHistory = prev.filter(chat => chat.id !== currentChatId)
      updatedHistory.unshift(chatData)
      localStorage.setItem('yuzuriha_chat_history', JSON.stringify(updatedHistory))
      return updatedHistory
    })
  }, [currentChatId])

  const loadChat = useCallback((chatId: string) => {
    const chat = chatHistory.find(c => c.id === chatId)
    if (chat) {
      setCurrentChatId(chatId)
      setMessages(chat.messages)
      setSidebarOpen(false)
    }
  }, [chatHistory])

  const deleteChat = useCallback((chatId: string) => {
    setChatHistory(prev => {
      const updatedHistory = prev.filter(chat => chat.id !== chatId)
      localStorage.setItem('yuzuriha_chat_history', JSON.stringify(updatedHistory))
      return updatedHistory
    })
    
    if (chatId === currentChatId) {
      startNewChat()
    }
  }, [currentChatId, startNewChat])

  // 修改发送消息函数支持文件 - 只修改这个函数
  const sendMessage = useCallback(async (content: string, files?: UploadedFile[]) => {
    if ((!content.trim() && !files?.length) || isLoading) return

    // 创建用户消息 - 使用现有的 Message 类型
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: files?.length ? `${content}\n\n附件: ${files.map(f => f.filename).join(', ')}` : content,
      timestamp: new Date().toISOString() // 使用 string 类型
    }

    const updatedMessages = [...messages, userMessage]
    setMessages(updatedMessages)
    setIsLoading(true)

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${API_SECRET_KEY}`, // 添加鉴权头
        },
        body: JSON.stringify({
          message: content,
          history: messages.map(msg => ({
            role: msg.role,
            content: msg.content
          })),
          files: files || []
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
        timestamp: new Date().toISOString(), // 使用 string 类型
      }

      const finalMessages = [...updatedMessages, assistantMessage]
      setMessages(finalMessages)
      saveCurrentChat && saveCurrentChat(finalMessages)

    } catch (error) {
      console.error('Error sending message:', error)
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: '抱歉，发送消息时出现错误。请稍后重试。',
        timestamp: new Date().toISOString(), // 使用 string 类型
      }
      const finalMessages = [...updatedMessages, errorMessage]
      setMessages(finalMessages)
      saveCurrentChat && saveCurrentChat(finalMessages)
    } finally {
      setIsLoading(false)
    }
  }, [messages, isLoading])

  // ... 保持现有的其他代码不变 ...

  return (
    <div className="h-screen flex bg-gray-50">
      {/* 修正 Sidebar 的属性名 */}
      <Sidebar 
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onNewChat={startNewChat || (() => {})}
        chatHistory={chatHistory}
        currentChatId={currentChatId}
        onLoadChat={loadChat || ((chatId: string) => {})} // 改为 onLoadChat
        onDeleteChat={deleteChat || ((chatId: string) => {})}
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
          </div>
          
          <div className="flex items-center space-x-2">
            <div className="text-sm font-medium text-gray-900">Project Yuzuriha</div>
            <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
          </div>
        </header>

        <div className="flex-1 flex flex-col min-h-0">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full px-4">
              <div className="text-center mb-8">
                <h1 className="text-4xl font-semibold text-gray-900 mb-2">你好，我是 Yuzuriha</h1>
                <p className="text-gray-600">在时刻准备着。</p>
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