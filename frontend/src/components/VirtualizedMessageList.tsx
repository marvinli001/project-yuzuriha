'use client'

import { useEffect, useRef, useState, useMemo } from 'react'
import { Message } from '@/types/chat'
import MessageBubble from './MessageBubble'

interface VirtualizedMessageListProps {
  messages: Message[]
  isLoading?: boolean
}

const ITEM_HEIGHT = 120 // 估计的每条消息高度
const BUFFER_SIZE = 5 // 缓冲区大小

export default function VirtualizedMessageList({ messages, isLoading }: VirtualizedMessageListProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [scrollTop, setScrollTop] = useState(0)
  const [containerHeight, setContainerHeight] = useState(600)
  const [itemHeights, setItemHeights] = useState<Map<string, number>>(new Map())

  // 计算可见范围
  const visibleRange = useMemo(() => {
    const startIndex = Math.max(0, Math.floor(scrollTop / ITEM_HEIGHT) - BUFFER_SIZE)
    const endIndex = Math.min(
      messages.length - 1,
      Math.ceil((scrollTop + containerHeight) / ITEM_HEIGHT) + BUFFER_SIZE
    )
    return { startIndex, endIndex }
  }, [scrollTop, containerHeight, messages.length])

  // 处理滚动事件
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const target = e.target as HTMLDivElement
    setScrollTop(target.scrollTop)
  }

  // 监听容器尺寸变化
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0]
      if (entry) {
        setContainerHeight(entry.contentRect.height)
      }
    })

    resizeObserver.observe(container)
    return () => resizeObserver.disconnect()
  }, [])

  // 自动滚动到底部（新消息时）
  useEffect(() => {
    const container = containerRef.current
    if (container && messages.length > 0) {
      const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 100
      if (isNearBottom || messages.length === 1) {
        container.scrollTop = container.scrollHeight
      }
    }
  }, [messages])

  const totalHeight = messages.length * ITEM_HEIGHT
  const offsetY = visibleRange.startIndex * ITEM_HEIGHT

  return (
    <div 
      ref={containerRef}
      className="flex-1 overflow-y-auto px-4 py-6"
      onScroll={handleScroll}
      style={{ position: 'relative' }}
    >
      <div style={{ height: totalHeight, position: 'relative' }}>
        <div style={{ transform: `translateY(${offsetY}px)` }}>
          {messages.slice(visibleRange.startIndex, visibleRange.endIndex + 1).map((message, index) => (
            <div key={message.id} className="mb-6">
              <MessageBubble message={message} />
            </div>
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
        </div>
      </div>
    </div>
  )
}