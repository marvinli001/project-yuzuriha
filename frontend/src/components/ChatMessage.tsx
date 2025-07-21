'use client'

import { Message } from '@/types/chat'
import { User, Bot, Copy, Check } from 'lucide-react'
import { useState } from 'react'

interface ChatMessageProps {
  message: Message
  isLoading?: boolean
}

export default function ChatMessage({ message, isLoading = false }: ChatMessageProps) {
  const [copied, setCopied] = useState(false)
  const isUser = message.role === 'user'

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(message.content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (error) {
      console.error('Failed to copy text:', error)
    }
  }

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className={`group flex gap-4 p-6 ${isUser ? 'bg-transparent' : 'bg-gray-800/30'} rounded-lg`}>
      {/* 头像 */}
      <div className="flex-shrink-0">
        <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
          isUser 
            ? 'bg-chat-user text-white' 
            : 'bg-gray-600 text-white'
        }`}>
          {isUser ? <User size={16} /> : <Bot size={16} />}
        </div>
      </div>
      
      {/* 消息内容 */}
      <div className="flex-1 min-w-0">
        {/* 消息头部 */}
        <div className="flex items-center gap-3 mb-2">
          <span className="font-medium text-sm text-black">
            {isUser ? 'You' : 'Yuzuriha'}
          </span>
          <span className="text-xs text-gray-500">
            {formatTime(message.timestamp)}
          </span>
          {!isLoading && (
            <button
              onClick={copyToClipboard}
              className="opacity-0 group-hover:opacity-100 p-1 hover:bg-gray-700 rounded transition-all"
              title="复制消息"
            >
              {copied ? <Check size={14} className="text-green-400" /> : <Copy size={14} className="text-gray-400" />}
            </button>
          )}
        </div>
        
        {/* 消息文本 */}
        <div className="prose prose-invert max-w-none">
          {isLoading ? (
            <div className="flex items-center gap-2">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
              </div>
              <span className="text-sm text-gray-400">正在生成回复...</span>
            </div>
          ) : (
            <div className="whitespace-pre-wrap break-words text-black leading-relaxed">
              {message.content}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}