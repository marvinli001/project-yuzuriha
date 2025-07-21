'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { Message, ChatHistory } from '@/types/chat'
import Sidebar from '@/components/Sidebar'
import ChatMessage from '@/components/ChatMessage'
import ChatInput from '@/components/ChatInput'
import { Menu, Plus, MessageCircle, Lightbulb, Code, Zap } from 'lucide-react'

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

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return

    const userMessage: Message = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: content.trim(),
      timestamp: new Date().toISOString()
    }

    const updatedMessages = [...messages, userMessage]
    setMessages(updatedMessages)
    setIsLoading(true)

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: content.trim(),
          history: messages.map(msg => ({
            role: msg.role,
            content: msg.content
          }))
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      
      const assistantMessage: Message = {
        id: `msg_${Date.now() + 1}`,
        role: 'assistant',
        content: data.response,
        timestamp: new Date().toISOString()
      }

      const finalMessages = [...updatedMessages, assistantMessage]
      setMessages(finalMessages)
      saveCurrentChat(finalMessages)

    } catch (error) {
      console.error('Error sending message:', error)
      const errorMessage: Message = {
        id: `msg_${Date.now() + 1}`,
        role: 'assistant',
        content: '抱歉，发送消息时出现错误。请检查网络连接并重试。',
        timestamp: new Date().toISOString()
      }
      const finalMessages = [...updatedMessages, errorMessage]
      setMessages(finalMessages)
    } finally {
      setIsLoading(false)
    }
  }, [messages, isLoading, saveCurrentChat])

  return (
    <div className="flex h-screen bg-white overflow-hidden">
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        chatHistory={chatHistory}
        onNewChat={startNewChat}
        onLoadChat={loadChat}
        onDeleteChat={deleteChat}
        currentChatId={currentChatId}
      />

      <div className="flex flex-col flex-1 min-w-0">
        {/* 顶部导航栏 - 固定定位 */}
        <header className="flex items-center justify-between p-4 border-b border-gray-200 bg-white flex-shrink-0 z-10">
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-2 hover:bg-gray-100 rounded-md transition-colors"
            >
              <Menu className="w-5 h-5 text-gray-600" />
            </button>
            <button
              onClick={startNewChat}
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

        {/* 主要内容区域 */}
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
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                        <div 
                          className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" 
                          style={{ animationDelay: '0.1s' }}
                        ></div>
                        <div 
                          className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" 
                          style={{ animationDelay: '0.2s' }}
                        ></div>
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>
              </div>

              <div className="flex-shrink-0 px-4 py-6 border-t border-gray-200 bg-white">
                <div className="max-w-4xl mx-auto">
                  <ChatInput 
                    onSendMessage={sendMessage} 
                    disabled={isLoading} 
                    hasMessages={true}
                  />
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}