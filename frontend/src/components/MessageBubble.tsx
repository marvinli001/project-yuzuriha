import { Message } from '@/types/chat'
import { User, Bot } from 'lucide-react'

interface MessageBubbleProps {
  message: Message
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  return (
    <div className="flex items-start space-x-3">
      <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
        isUser ? 'bg-chat-user' : 'bg-gray-600'
      }`}>
        {isUser ? (
          <User size={16} className="text-white" />
        ) : (
          <Bot size={16} className="text-white" />
        )}
      </div>
      
      <div className="flex-1 space-y-2">
        <div className={`prose prose-invert max-w-none ${
          isUser ? 'text-gray-100' : 'text-gray-200'
        }`}>
          <div className="whitespace-pre-wrap break-words">
            {message.content}
          </div>
        </div>
        
        <div className="text-xs text-gray-500">
          {new Date(message.timestamp).toLocaleTimeString()}
        </div>
      </div>
    </div>
  )
}