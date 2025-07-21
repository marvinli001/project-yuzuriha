'use client'

import { useState, useRef, KeyboardEvent } from 'react'
import { Send } from 'lucide-react'

interface MessageInputProps {
  onSendMessage: (message: string) => void
  disabled?: boolean
}

export default function MessageInput({ 
  onSendMessage, 
  disabled = false 
}: MessageInputProps) {
  const [message, setMessage] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = () => {
    if (!message.trim() || disabled) return
    
    onSendMessage(message.trim())
    setMessage('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleInput = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`
    }
  }

  return (
    <div className="border-t border-gray-700 p-4 bg-chat-bg">
      <div className="max-w-4xl mx-auto">
        <div className="relative flex items-end space-x-3">
          <div className="flex-1">
            <textarea
              ref={textareaRef}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onInput={handleInput}
              onKeyDown={handleKeyDown}
              placeholder="Send a message..."
              disabled={disabled}
              className="w-full resize-none rounded-lg border border-gray-600 bg-chat-input px-4 py-3 text-white placeholder-gray-400 focus:border-chat-user focus:outline-none disabled:opacity-50 min-h-[52px] max-h-32"
              rows={1}
            />
          </div>
          
          <button
            onClick={handleSubmit}
            disabled={!message.trim() || disabled}
            className="p-3 rounded-lg bg-chat-user text-white hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            type="button"
          >
            <Send size={20} />
          </button>
        </div>
      </div>
    </div>
  )
}