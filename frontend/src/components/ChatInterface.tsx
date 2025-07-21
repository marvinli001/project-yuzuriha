'use client'

import { useState, useRef, useEffect } from 'react'
import { Message } from '@/types/chat'
import MessageBubble from './MessageBubble'  // 确保这个路径正确
import MessageInput from './MessageInput'    // 确保这个路径正确
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
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [hasScrolled, setHasScrolled] = useState(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (!hasScrolled) {
      scrollToBottom();
    }
  }, [messages, hasScrolled]);

  const handleScroll = () => {
    setHasScrolled(true);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="flex items-center p-4 border-b border-gray-700 bg-chat-bg">
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
      <div 
        className="flex-1 overflow-y-auto px-4 py-6"
        onScroll={handleScroll}
      >
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-gray-400">
              <h2 className="text-2xl font-bold mb-2">Welcome to Yuzuriha</h2>
              <p>Start a conversation to begin</p>
            </div>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto space-y-6">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            {isLoading && (
              <div className="flex items-start space-x-3">
                <div className="w-8 h-8 bg-chat-user rounded-full flex items-center justify-center">
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
        )}
      </div>

      {/* Input */}
      <MessageInput onSendMessage={onSendMessage} disabled={isLoading} />
    </div>
  );
}