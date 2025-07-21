'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, Paperclip, Mic } from 'lucide-react'

interface ChatInputProps {
  onSendMessage: (message: string) => void
  disabled?: boolean
  hasMessages?: boolean
}

export default function ChatInput({ onSendMessage, disabled = false, hasMessages = false }: ChatInputProps) {
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

  // OpenAI 风格的首页输入框样式
  const homePageStyle = !hasMessages ? {
    containerClass: "relative",
    formClass: "relative",
    inputContainerClass: "flex items-center gap-3 bg-white border border-gray-200 rounded-full px-4 py-3 shadow-lg hover:shadow-xl transition-all duration-300 focus-within:ring-2 focus-within:ring-emerald-500 focus-within:border-emerald-500 focus-within:shadow-xl max-w-3xl mx-auto",
    textareaClass: "flex-1 bg-transparent text-gray-900 placeholder-gray-500 resize-none border-0 outline-0 min-h-[24px] max-h-[120px] py-1 text-base",
    placeholder: "询问任何问题..."
  } : {
    containerClass: "fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 p-4",
    formClass: "max-w-4xl mx-auto relative",
    inputContainerClass: "flex items-end gap-3 bg-white border border-gray-300 rounded-xl p-3 focus-within:ring-2 focus-within:ring-green-500 focus-within:border-transparent shadow-sm",
    textareaClass: "flex-1 bg-transparent text-gray-900 placeholder-gray-400 resize-none border-0 outline-0 min-h-[24px] max-h-[120px] py-1",
    placeholder: "输入消息..."
  }

  return (
    <div className={homePageStyle.containerClass}>
      <form onSubmit={handleSubmit} className={homePageStyle.formClass}>
        <div className={homePageStyle.inputContainerClass}>
          {/* 附件按钮 */}
          <button
            type="button"
            className="flex-shrink-0 p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors touch-target focus-visible"
            title="附件 (即将推出)"
            disabled
            aria-label="附件"
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
            placeholder={disabled ? "AI正在回复中..." : homePageStyle.placeholder}
            className={homePageStyle.textareaClass}
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
                className="p-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors text-white"
                title="发送消息"
              >
                <Send size={18} />
              </button>
            ) : (
              <button
                type="button"
                className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                title="语音输入 (即将推出)"
                disabled
              >
                <Mic size={18} />
              </button>
            )}
          </div>
        </div>
      </form>
    </div>
  )
}