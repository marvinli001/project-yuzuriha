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
      className={`w-full ${
        isVisible ? 'message-animate' : 'opacity-0'
      } smooth-transition`}
      role="article"
      aria-label={`${isUser ? '用户' : 'AI'} 消息`}
    >
      {/* OpenAI 风格的中置布局 */}
      <div className={`${isUser ? 'bg-transparent' : 'bg-gray-50'} py-6`}>
        <div className="max-w-3xl mx-auto px-4">
          <div className="group flex gap-4">
            {/* 头像 */}
            <div className="flex-shrink-0">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                isUser ? 'bg-green-600' : 'bg-gray-600'
              }`}>
                {isUser ? (
                  <User size={16} className="text-white" />
                ) : (
                  <Bot size={16} className="text-white" />
                )}
              </div>
            </div>

            {/* 消息内容 */}
            <div className="flex-1 min-w-0">
              {/* 角色标识 */}
              <div className="flex items-center gap-2 mb-2">
                <span className="text-sm font-semibold text-gray-900">
                  {isUser ? '你' : 'Yuzuriha'}
                </span>
                <span className="text-xs text-gray-500">
                  {formatTime(message.timestamp)}
                </span>
              </div>

              {/* 消息文本 */}
              <div className="prose max-w-none text-gray-800 leading-relaxed">
                {isLoading ? (
                  <div className="flex items-center space-x-2">
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    </div>
                    <span className="text-gray-500 text-sm">正在思考...</span>
                  </div>
                ) : (
                  <div 
                    className="whitespace-pre-wrap break-words"
                    dangerouslySetInnerHTML={{ __html: formatContent(message.content) }}
                  />
                )}
              </div>

              {/* 操作按钮 */}
              {!isLoading && !isUser && (
                <div className="flex items-center gap-2 mt-3 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={copyToClipboard}
                    className="p-1.5 rounded-md hover:bg-gray-200 transition-colors"
                    title="复制消息"
                  >
                    {copied ? (
                      <Check size={14} className="text-green-600" />
                    ) : (
                      <Copy size={14} className="text-gray-500" />
                    )}
                  </button>

                  {onRegenerate && (
                    <button
                      onClick={handleRegenerate}
                      className="p-1.5 rounded-md hover:bg-gray-200 transition-colors"
                      title="重新生成"
                    >
                      <RotateCcw size={14} className="text-gray-500" />
                    </button>
                  )}

                  {onFeedback && (
                    <>
                      <button
                        onClick={() => handleFeedback('positive')}
                        className={`p-1.5 rounded-md hover:bg-gray-200 transition-colors ${
                          feedback === 'positive' ? 'bg-green-100 text-green-600' : 'text-gray-500'
                        }`}
                        title="好评"
                      >
                        <ThumbsUp size={14} />
                      </button>
                      <button
                        onClick={() => handleFeedback('negative')}
                        className={`p-1.5 rounded-md hover:bg-gray-200 transition-colors ${
                          feedback === 'negative' ? 'bg-red-100 text-red-600' : 'text-gray-500'
                        }`}
                        title="差评"
                      >
                        <ThumbsDown size={14} />
                      </button>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}