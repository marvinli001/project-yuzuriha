'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, Paperclip, Mic } from 'lucide-react'

interface ChatInputProps {
  onSendMessage: (message: string) => void
  disabled?: boolean
}

export default function ChatInput({ onSendMessage, disabled = false }: ChatInputProps) {
  const [message, setMessage] = useState('')
  const [isComposing, setIsComposing] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // 自动调整文本框高度
  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`
    }
  }, [message])

  // 自动获得焦点
  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea && !disabled) {
      textarea.focus()
    }
  }, [disabled])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (message.trim() && !disabled && !isComposing) {
      onSendMessage(message.trim())
      setMessage('')
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey && !isComposing) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const handleCompositionStart = () => {
    setIsComposing(true)
  }

  const handleCompositionEnd = () => {
    setIsComposing(false)
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-chat-bg border-t border-gray-700 p-4">
      <div className="max-w-4xl mx-auto">
        <form onSubmit={handleSubmit} className="relative">
          <div className="flex items-end gap-3 bg-chat-input border border-gray-600 rounded-lg p-3 focus-within:ring-2 focus-within:ring-chat-user focus-within:border-transparent">
            {/* 附件按钮 */}
            <button
              type="button"
              className="flex-shrink-0 p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
              title="附件 (即将推出)"
              disabled
            >
              <Paperclip size={18} />
            </button>

            {/* 文本输入框 */}
            <textarea
              ref={textareaRef}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              onCompositionStart={handleCompositionStart}
              onCompositionEnd={handleCompositionEnd}
              placeholder={disabled ? "AI正在回复中..." : "输入消息..."}
              className="flex-1 bg-transparent text-black placeholder-gray-400 resize-none border-0 outline-0 min-h-[24px] max-h-[120px] py-1"
              rows={1}
              disabled={disabled}
              style={{ lineHeight: '1.5' }}
            />

            {/* 发送/语音按钮 */}
            <div className="flex-shrink-0 flex items-center gap-2">
              {message.trim() ? (
                <button
                  type="submit"
                  disabled={disabled || isComposing}
                  className="p-2 bg-chat-user hover:bg-chat-user/80 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors"
                  title="发送消息"
                >
                  <Send size={18} className="text-white" />
                </button>
              ) : (
                <button
                  type="button"
                  className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
                  title="语音输入 (即将推出)"
                  disabled
                >
                  <Mic size={18} />
                </button>
              )}
            </div>
          </div>
        </form>
        
        {/* 提示文本 */}
        <div className="text-xs text-gray-500 mt-2 text-center">
          按 Enter 发送消息，Shift + Enter 换行
        </div>
      </div>
    </div>
  )
}