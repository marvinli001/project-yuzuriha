'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, Paperclip, Mic, MicOff } from 'lucide-react'

interface ChatInputProps {
  onSendMessage: (message: string) => void
  disabled?: boolean
  hasMessages?: boolean
}

export default function ChatInput({ onSendMessage, disabled = false, hasMessages = false }: ChatInputProps) {
  const [message, setMessage] = useState('')
  const [isComposing, setIsComposing] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [characterCount, setCharacterCount] = useState(0)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const MAX_CHARS = 4000

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

  // 更新字符计数
  useEffect(() => {
    setCharacterCount(message.length)
  }, [message])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (message.trim() && !disabled && !isComposing && message.length <= MAX_CHARS) {
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

  const handleVoiceToggle = () => {
    setIsRecording(!isRecording)
    // TODO: 实现语音识别功能
  }

  const handlePaste = (e: React.ClipboardEvent) => {
    // 处理粘贴事件，可以添加图片粘贴支持
    const items = e.clipboardData?.items
    if (items) {
      for (const item of Array.from(items)) {
        if (item.type.startsWith('image/')) {
          e.preventDefault()
          // TODO: 处理图片粘贴
          console.log('Image pasted:', item.type)
        }
      }
    }
  }

  const isOverLimit = characterCount > MAX_CHARS
  const isNearLimit = characterCount > MAX_CHARS * 0.9

  return (
    <div className={`${hasMessages ? 'border-t' : ''} bg-white border-gray-200 p-4`}>
      <div className="max-w-4xl mx-auto">
        <form onSubmit={handleSubmit} className="relative">
          <div className={`flex items-end gap-3 bg-white border ${isOverLimit ? 'border-red-300' : 'border-gray-300'} rounded-xl p-3 focus-within:ring-2 focus-within:ring-green-500 focus-within:border-transparent shadow-sm smooth-transition`}>
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
            <div className="flex-1 relative">
              <textarea
                ref={textareaRef}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                onCompositionStart={handleCompositionStart}
                onCompositionEnd={handleCompositionEnd}
                onPaste={handlePaste}
                placeholder={disabled ? "AI正在回复中..." : "输入消息... (Shift+Enter 换行)"}
                className="w-full bg-transparent text-gray-900 placeholder-gray-400 resize-none border-0 outline-0 min-h-[24px] max-h-[120px] py-1"
                rows={1}
                disabled={disabled}
                maxLength={MAX_CHARS}
                style={{ lineHeight: '1.5' }}
                aria-label="消息输入框"
              />
              
              {/* 字符计数 */}
              {(isNearLimit || isOverLimit) && (
                <div className={`absolute -top-6 right-0 text-xs ${isOverLimit ? 'text-red-500' : 'text-gray-400'} smooth-transition`}>
                  {characterCount}/{MAX_CHARS}
                </div>
              )}
            </div>

            {/* 发送/语音按钮 */}
            <div className="flex-shrink-0 flex items-center gap-2">
              {message.trim() ? (
                <button
                  type="submit"
                  disabled={disabled || isComposing || isOverLimit}
                  className="p-2 rounded-lg bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors touch-target focus-visible"
                  aria-label="发送消息"
                >
                  <Send size={18} />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleVoiceToggle}
                  disabled={disabled}
                  className={`p-2 rounded-lg transition-colors touch-target focus-visible ${
                    isRecording 
                      ? 'bg-red-100 text-red-600 hover:bg-red-200' 
                      : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'
                  }`}
                  aria-label={isRecording ? "停止录音" : "开始语音输入"}
                  title={isRecording ? "停止录音" : "语音输入 (即将推出)"}
                >
                  {isRecording ? <MicOff size={18} /> : <Mic size={18} />}
                </button>
              )}
            </div>
          </div>

          {/* 快捷提示 */}
          {!hasMessages && !message && (
            <div className="mt-2 text-xs text-gray-400 text-center">
              提示: 使用 Shift+Enter 换行，Enter 发送消息
            </div>
          )}
        </form>
      </div>
    </div>
  )
}