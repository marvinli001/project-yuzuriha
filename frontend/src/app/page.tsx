'use client'

import { useState, useEffect, useRef } from 'react'
import { Message, ChatHistory } from '@/types/chat'
import Sidebar from '@/components/Sidebar'
import ChatMessage from '@/components/ChatMessage'
import ChatInput from '@/components/ChatInput'
import { Menu, Plus } from 'lucide-react'

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
    
    // 如果没有当前聊天，创建新的
    if (!currentChatId) {
      startNewChat()
    }
  }, [currentChatId])

  // 自动滚动到底部
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
      updatedAt: new Date().toISOString()
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
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: content,
          history: messages.slice(-10) // 发送最近10条消息作为上下文
        }),
      })

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`)
      }

      const data = await response.json()
      
      const assistantMessage: Message = {
        id: `msg_${Date.now() + 1}`,
        role: 'assistant',
        content: data.response || '抱歉，我无法生成回复。',
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
        content: '抱歉，发生了错误。请检查网络连接后重试。',
        timestamp: new Date().toISOString()
      }
      const finalMessages = [...updatedMessages, errorMessage]
      setMessages(finalMessages)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex h-screen w-screen bg-chat-bg overflow-hidden">
      {/* 侧边栏 */}
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        chatHistory={chatHistory}
        onNewChat={startNewChat}
        onLoadChat={loadChat}
        onDeleteChat={deleteChat}
        currentChatId={currentChatId}
      />

      {/* 主聊天区域 */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* 顶部导航栏 */}
        <header className="flex items-center justify-between px-4 py-3 border-b border-gray-700 bg-chat-bg/95 backdrop-blur-sm">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
            aria-label="打开菜单"
          >
            <Menu size={20} className="text-gray-300" />
          </button>
          
          <h1 className="text-lg font-semibold text-white">Project Yuzuriha</h1>
          
          <button
            onClick={startNewChat}
            className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
            aria-label="新建对话"
          >
            <Plus size={20} className="text-gray-300" />
          </button>
        </header>

        {/* 消息区域 */}
        <div 
          ref={messagesContainerRef}
          className="flex-1 overflow-y-auto p-4 pb-20"
        >
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center max-w-2xl mx-auto">
              <div className="mb-8">
                <h2 className="text-3xl font-bold mb-4 text-white">欢迎使用 Project Yuzuriha</h2>
                <p className="text-gray-400 text-lg">一个拥有记忆能力的AI聊天助手</p>
                <p className="text-gray-500 text-sm mt-2">开始对话，我会记住我们的交流内容</p>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full">
                <div className="p-4 bg-gray-800/50 rounded-lg border border-gray-700">
                  <h3 className="font-semibold mb-2 text-white">🧠 持久记忆</h3>
                  <p className="text-sm text-gray-400">记住过往对话，提供个性化体验</p>
                </div>
                <div className="p-4 bg-gray-800/50 rounded-lg border border-gray-700">
                  <h3 className="font-semibold mb-2 text-white">🔍 智能检索</h3>
                  <p className="text-sm text-gray-400">基于向量数据库的语义搜索</p>
                </div>
                <div className="p-4 bg-gray-800/50 rounded-lg border border-gray-700">
                  <h3 className="font-semibold mb-2 text-white">💬 流畅对话</h3>
                  <p className="text-sm text-gray-400">类似 ChatGPT 的用户体验</p>
                </div>
                <div className="p-4 bg-gray-800/50 rounded-lg border border-gray-700">
                  <h3 className="font-semibold mb-2 text-white">📱 PWA 支持</h3>
                  <p className="text-sm text-gray-400">可安装为原生应用</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="max-w-4xl mx-auto space-y-6">
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}
              {isLoading && (
                <ChatMessage 
                  message={{
                    id: 'loading',
                    role: 'assistant',
                    content: '思考中...',
                    timestamp: new Date().toISOString()
                  }}
                  isLoading
                />
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* 输入区域 */}
        <ChatInput 
          onSendMessage={sendMessage} 
          disabled={isLoading}
        />
      </div>
    </div>
  )
}