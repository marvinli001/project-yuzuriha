'use client'

import { useState, useRef, useEffect } from 'react'
import { Message } from '@/types/chat'
import VirtualizedMessageList from './VirtualizedMessageList'
import MessageInput from './MessageInput'
import { Menu } from 'lucide-react'

interface ChatInterfaceProps {
  messages: Message[];
  onSendMessage: (message: string) => void;
  isLoading: boolean;
  onMenuClick: () => void;
}

export default function ChatInterface({ 
  messages, 
  onSendMessage, 
  isLoading, 
  onMenuClick 
}: ChatInterfaceProps) {
  const [hasScrolled, setHasScrolled] = useState(false)

  const handleScroll = () => {
    setHasScrolled(true)
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="flex items-center p-4 border-b border-gray-700 bg-chat-bg flex-shrink-0">
        <button
          onClick={onMenuClick}
          className="p-2 rounded-lg hover:bg-gray-700 transition-colors"
          type="button"
        >
          <Menu size={20} className="text-gray-400" />
        </button>
        <h1 className="ml-2 text-xl font-semibold text-white">Yuzuriha</h1>
      </header>

      {/* Messages */}
      {messages.length === 0 ? (
        <div className="flex items-center justify-center h-full">
          <div className="text-center text-gray-400">
            <h2 className="text-2xl font-bold mb-2">Welcome to Yuzuriha</h2>
            <p>Start a conversation to begin</p>
          </div>
        </div>
      ) : (
        <VirtualizedMessageList messages={messages} isLoading={isLoading} />
      )}

      {/* Input */}
      <div className="flex-shrink-0">
        <MessageInput onSendMessage={onSendMessage} disabled={isLoading} />
      </div>
    </div>
  );
}