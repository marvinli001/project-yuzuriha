'use client'

import { Message } from '@/types/chat'
import { User, Bot, Copy, Check, ThumbsUp, ThumbsDown, RotateCcw } from 'lucide-react'
import { useState, useRef, useEffect } from 'react'

interface ChatMessageProps {
  message: Message
  isLoading?: boolean
  onRegenerate?: (messageId: string) => void
  onFeedback?: (messageId: string, type: 'positive' | 'negative') => void
}

export default function ChatMessage({ 
  message, 
  isLoading = false, 
  onRegenerate,
  onFeedback 
}: ChatMessageProps) {
  const [copied, setCopied] = useState(false)
  const [feedback, setFeedback] = useState<'positive' | 'negative' | null>(null)
  const [isVisible, setIsVisible] = useState(false)
  const messageRef = useRef<HTMLDivElement>(null)
  const isUser = message.role === 'user'

  // 可见性观察器，用于动画
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true)
        }
      },
      { threshold: 0.1 }
    )

    if (messageRef.current) {
      observer.observe(messageRef.current)
    }

    return () => observer.disconnect()
  }, [])

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(message.content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (error) {
      console.error('Failed to copy text:', error)
      // 降级处理
      const textArea = document.createElement('textarea')
      textArea.value = message.content
      document.body.appendChild(textArea)
      textArea.select()
      document.execCommand('copy')
      document.body.removeChild(textArea)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleFeedback = (type: 'positive' | 'negative') => {
    setFeedback(type)
    onFeedback?.(message.id, type)
  }

  const handleRegenerate = () => {
    onRegenerate?.(message.id)
  }

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const formatContent = (content: string) => {
    // 简单的 Markdown 支持
    return content
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code class="bg-gray-100 px-1 py-0.5 rounded text-sm">$1</code>')
      .replace(/\n/g, '<br>')
  }

  return (
    <div 
      ref={messageRef}
      className={`group flex gap-4 p-6 ${isUser ? 'bg-transparent' : 'bg-gray-50'} rounded-lg message-item smooth-transition ${
        isVisible ? 'message-animate' : 'opacity-0'
      }`}
      role="article"
      aria-label={`${isUser ? '用户' : 'AI'} 消息`}
    >
      {/* 头像 */}
      <div className="flex-shrink-0">
        <div className={`w-8 h-8 rounded-full flex items-center justify-center smooth-transition ${
          isUser 
            ? 'bg-green-600 text-white' 
            : 'bg-blue-600 text-white'
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
          
          {/* 操作按钮 */}
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 smooth-transition">
            {!isLoading && (
              <button
                onClick={copyToClipboard}
                className="p-1 hover:bg-gray-200 rounded transition-colors touch-target focus-visible"
                title="复制消息"
                aria-label="复制消息内容"
              >
                {copied ? <Check size={14} className="text-green-600" /> : <Copy size={14} className="text-gray-400" />}
              </button>
            )}
            
            {/* AI 消息的额外操作 */}
            {!isUser && !isLoading && (
              <>
                <button
                  onClick={handleRegenerate}
                  className="p-1 hover:bg-gray-200 rounded transition-colors touch-target focus-visible"
                  title="重新生成"
                  aria-label="重新生成此回复"
                >
                  <RotateCcw size={14} className="text-gray-400" />
                </button>
                
                <button
                  onClick={() => handleFeedback('positive')}
                  className={`p-1 hover:bg-gray-200 rounded transition-colors touch-target focus-visible ${
                    feedback === 'positive' ? 'text-green-600' : 'text-gray-400'
                  }`}
                  title="好评"
                  aria-label="给此回复好评"
                >
                  <ThumbsUp size={14} />
                </button>
                
                <button
                  onClick={() => handleFeedback('negative')}
                  className={`p-1 hover:bg-gray-200 rounded transition-colors touch-target focus-visible ${
                    feedback === 'negative' ? 'text-red-600' : 'text-gray-400'
                  }`}
                  title="差评"
                  aria-label="给此回复差评"
                >
                  <ThumbsDown size={14} />
                </button>
              </>
            )}
          </div>
        </div>
        
        {/* 消息文本 */}
        <div className="prose prose-gray max-w-none">
          {isLoading ? (
            <div className="flex items-center gap-2" role="status" aria-label="AI正在生成回复">
              <div className="flex gap-1 typing-indicator">
                <div className="w-2 h-2 bg-gray-400 rounded-full dot"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full dot"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full dot"></div>
              </div>
              <span className="text-sm text-gray-400">正在生成回复...</span>
            </div>
          ) : (
            <div 
              className="whitespace-pre-wrap break-words text-black leading-relaxed"
              dangerouslySetInnerHTML={{ __html: formatContent(message.content) }}
            />
          )}
        </div>
      </div>
    </div>
  )
}