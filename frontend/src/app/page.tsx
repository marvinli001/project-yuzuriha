'use client'

import { useState, useEffect, useRef } from 'react'
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

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const startNewChat = () => {
    const newChatId = `chat_${Date.now()}`
    setCurrentChatId(newChatId)
    setMessages([])
    setSidebarOpen(false)
  }

  const saveCurrentChat = (updatedMessages: Message[]) => {
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

    const updatedHistory = chatHistory.filter(chat => chat.id !== currentChatId)
    updatedHistory.unshift(chatData)
    
    setChatHistory(updatedHistory)
    localStorage.setItem('yuzuriha_chat_history', JSON.stringify(updatedHistory))
  }

  const loadChat = (chatId: string) => {
    const chat = chatHistory.find(c => c.id === chatId)
    if (chat) {
      setCurrentChatId(chatId)
      setMessages(chat.messages)
      setSidebarOpen(false)
    }
  }

  const deleteChat = (chatId: string) => {
    const updatedHistory = chatHistory.filter(chat => chat.id !== chatId)
    setChatHistory(updatedHistory)
    localStorage.setItem('yuzuriha_chat_history', JSON.stringify(updatedHistory))
    
    if (chatId === currentChatId) {
      startNewChat()
    }
  }

  const sendMessage = async (content: string) => {
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
  }

  const handleExampleClick = (prompt: string) => {
    sendMessage(prompt)
  }

  return (
    <div className="flex h-full bg-white">
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        chatHistory={chatHistory}
        onNewChat={startNewChat}
        onLoadChat={loadChat}
        onDeleteChat={deleteChat}
        currentChatId={currentChatId}
      />

      <div className="flex flex-col flex-1 relative">
        {/* 顶部导航栏 */}
        <header className="flex items-center justify-between p-4 border-b border-gray-200 bg-white">
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
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
          </div>
        </header>

        {/* 主要内容区域 */}
        <div className="flex-1 flex flex-col">
          {messages.length === 0 ? (
            /* 欢迎页面 */
            <div className="flex-1 flex flex-col items-center justify-center px-4 py-8">
              <div className="text-center max-w-4xl mx-auto">
                <div className="mb-8">
                  <h1 className="text-4xl font-bold text-gray-900 mb-4">
                    你好，我是 Yuzuriha
                  </h1>
                </div>
              </div>
            </div>
          ) : (
            /* 聊天消息区域 */
            <div 
              ref={messagesContainerRef}
              className="flex-1 overflow-y-auto px-4 py-6"
            >
              <div className="max-w-3xl mx-auto space-y-6">
                {messages.map((message) => (
                  <ChatMessage key={message.id} message={message} />
                ))}
                {isLoading && (
                  <div className="flex justify-start">
                    <div className="max-w-xs lg:max-w-2xl px-4 py-3 rounded-lg bg-gray-100">
                      <div className="flex items-center space-x-2">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            </div>
          )}

          {/* 输入区域 */}
          <div className="border-t border-gray-200 bg-white">
            <div className="max-w-3xl mx-auto px-4 py-4">
              <ChatInput
                onSendMessage={sendMessage}
                disabled={isLoading}
              />
              <div className="text-xs text-gray-500 text-center mt-2">
                Yuzuriha 可能会出错。请核实重要信息。
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}