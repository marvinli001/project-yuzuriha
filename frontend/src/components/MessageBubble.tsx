import { Message } from '@/types/chat'
import { User, Bot } from 'lucide-react'

interface MessageBubbleProps {
  message: Message
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className="w-full">
      {/* OpenAI 风格的中置布局 */}
      <div className={`${isUser ? 'bg-transparent' : 'bg-gray-50'} py-6`}>
        <div className="max-w-3xl mx-auto px-4">
          <div className="flex gap-4">
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
                <div className="whitespace-pre-wrap break-words">
                  {message.content}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}