'use client'

import { useState, useEffect, useRef } from 'react'
import ChatInterface from '@/components/ChatInterface'
import Sidebar from '@/components/Sidebar'
import { Message, ChatHistory } from '@/types/chat'

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [chatHistory, setChatHistory] = useState<ChatHistory[]>([])
  const [currentChatId, setCurrentChatId] = useState<string>('')

  useEffect(() => {
    // Load chat history from localStorage
    const saved = localStorage.getItem('yuzuriha_chats')
    if (saved) {
      const parsed = JSON.parse(saved)
      setChatHistory(parsed)
    }
    
    // Create new chat if none exists
    if (!currentChatId) {
      createNewChat()
    }
  }, [])

  const createNewChat = () => {
    const newChatId = Date.now().toString()
    setCurrentChatId(newChatId)
    setMessages([])
    setSidebarOpen(false)
  }

  const saveCurrentChat = (newMessages: Message[]) => {
    if (!currentChatId || newMessages.length === 0) return
    
    const chatTitle = newMessages[0]?.content.slice(0, 50) + '...' || 'New Chat'
    const chatData: ChatHistory = {
      id: currentChatId,
      title: chatTitle,
      messages: newMessages,
      timestamp: new Date().toISOString()
    }

    const updatedHistory = chatHistory.filter(chat => chat.id !== currentChatId)
    updatedHistory.unshift(chatData)
    
    setChatHistory(updatedHistory)
    localStorage.setItem('yuzuriha_chats', JSON.stringify(updatedHistory))
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
    localStorage.setItem('yuzuriha_chats', JSON.stringify(updatedHistory))
    
    if (chatId === currentChatId) {
      createNewChat()
    }
  }

  const sendMessage = async (content: string) => {
    const newMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date().toISOString()
    }

    const updatedMessages = [...messages, newMessage]
    setMessages(updatedMessages)
    setIsLoading(true)

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: content,
          history: messages.slice(-10), // Send last 10 messages for context
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to send message')
      }

      const data = await response.json()
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
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
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString()
      }
      const finalMessages = [...updatedMessages, errorMessage]
      setMessages(finalMessages)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex h-screen w-full">
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        chatHistory={chatHistory}
        onNewChat={createNewChat}
        onLoadChat={loadChat}
        onDeleteChat={deleteChat}
        currentChatId={currentChatId}
      />
      
      <div className="flex-1 flex flex-col">
        <ChatInterface
          messages={messages}
          onSendMessage={sendMessage}
          isLoading={isLoading}
          onMenuClick={() => setSidebarOpen(true)}
        />
      </div>
    </div>
  )
}