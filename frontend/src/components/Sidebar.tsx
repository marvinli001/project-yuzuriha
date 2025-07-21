'use client'

import { useEffect, useRef, useState } from 'react'
import { ChatHistory } from '@/types/chat'
import { X, Plus, MessageSquare, Trash2, Search, Settings, Moon, Sun } from 'lucide-react'

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
  chatHistory: ChatHistory[]
  onNewChat: () => void
  onLoadChat: (chatId: string) => void
  onDeleteChat: (chatId: string) => void
  currentChatId: string
}

export default function Sidebar({
  isOpen,
  onClose,
  chatHistory,
  onNewChat,
  onLoadChat,
  onDeleteChat,
  currentChatId
}: SidebarProps) {
  const sidebarRef = useRef<HTMLDivElement>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [isDarkMode, setIsDarkMode] = useState(false)
  const [filteredHistory, setFilteredHistory] = useState(chatHistory)

  // 搜索功能
  useEffect(() => {
    if (searchTerm) {
      const filtered = chatHistory.filter(chat =>
        chat.title.toLowerCase().includes(searchTerm.toLowerCase())
      )
      setFilteredHistory(filtered)
    } else {
      setFilteredHistory(chatHistory)
    }
  }, [searchTerm, chatHistory])

  // 点击外部关闭
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (sidebarRef.current && !sidebarRef.current.contains(event.target as Node)) {
        onClose()
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen, onClose])

  // 键盘导航
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (isOpen && event.key === 'Escape') {
        onClose()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  const handleDeleteChat = (e: React.MouseEvent, chatId: string) => {
    e.stopPropagation()
    if (confirm('确定要删除这个对话吗？')) {
      onDeleteChat(chatId)
    }
  }

  const toggleTheme = () => {
    setIsDarkMode(!isDarkMode)
    // TODO: 实现主题切换逻辑
  }

  const groupChatsByDate = (chats: ChatHistory[]) => {
    const groups: { [key: string]: ChatHistory[] } = {}
    const today = new Date()
    const yesterday = new Date(today)
    yesterday.setDate(yesterday.getDate() - 1)
    const lastWeek = new Date(today)
    lastWeek.setDate(lastWeek.getDate() - 7)

    chats.forEach(chat => {
      const chatDate = new Date(chat.timestamp)
      let group = ''

      if (chatDate.toDateString() === today.toDateString()) {
        group = '今天'
      } else if (chatDate.toDateString() === yesterday.toDateString()) {
        group = '昨天'
      } else if (chatDate > lastWeek) {
        group = '最近一周'
      } else {
        group = '更早'
      }

      if (!groups[group]) groups[group] = []
      groups[group].push(chat)
    })

    return groups
  }

  const groupedChats = groupChatsByDate(filteredHistory)

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden smooth-transition" 
          onClick={onClose}
          aria-hidden="true"
        />
      )}
      
      {/* Sidebar */}
      <aside
        ref={sidebarRef}
        className={`fixed left-0 top-0 h-full w-80 bg-gray-50 border-r border-gray-200 transform transition-transform duration-300 ease-in-out z-50 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        } md:relative md:translate-x-0 md:z-0`}
        role="complementary"
        aria-label="聊天历史侧边栏"
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">聊天记录</h2>
            <div className="flex items-center space-x-2">
              <button
                onClick={onNewChat}
                className="p-2 rounded-lg hover:bg-gray-200 transition-colors touch-target focus-visible"
                title="新建对话"
                aria-label="创建新对话"
              >
                <Plus size={20} className="text-gray-600" />
              </button>
              <button
                onClick={onClose}
                className="p-2 rounded-lg hover:bg-gray-200 transition-colors md:hidden touch-target focus-visible"
                aria-label="关闭侧边栏"
              >
                <X size={20} className="text-gray-600" />
              </button>
            </div>
          </div>

          {/* Search */}
          <div className="p-4 border-b border-gray-200">
            <div className="relative">
              <Search size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="搜索对话..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-white border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-green-500 focus:border-transparent"
                aria-label="搜索聊天历史"
              />
            </div>
          </div>

          {/* Chat History */}
          <div className="flex-1 overflow-y-auto custom-scrollbar">
            {Object.keys(groupedChats).length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center text-gray-500 px-4">
                <MessageSquare size={48} className="mb-4 opacity-50" />
                <h3 className="font-medium mb-2">还没有对话记录</h3>
                <p className="text-sm">点击上方的 + 号开始新对话</p>
              </div>
            ) : (
              <div className="p-2">
                {Object.entries(groupedChats).map(([group, chats]) => (
                  <div key={group} className="mb-4">
                    <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider px-3 py-2">
                      {group}
                    </h3>
                    <div className="space-y-1">
                      {chats.map((chat) => (
                        <div
                          key={chat.id}
                          className={`group relative flex items-center p-3 rounded-lg cursor-pointer smooth-transition ${
                            chat.id === currentChatId
                              ? 'bg-gray-100 border border-gray-400'
                              : 'hover:bg-gray-100'
                          }`}
                          onClick={() => {
                            onLoadChat(chat.id)
                            onClose()
                          }}
                          role="button"
                          tabIndex={0}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault()
                              onLoadChat(chat.id)
                              onClose()
                            }
                          }}
                          aria-label={`选择对话: ${chat.title}`}
                        >
                          <MessageSquare size={16} className="mr-3 flex-shrink-0 text-gray-400" />
                          <div className="flex-1 min-w-0">
                            <p className="truncate text-sm font-medium text-gray-900">
                              {chat.title}
                            </p>
                            <p className="text-xs text-gray-500">
                              {new Date(chat.timestamp).toLocaleDateString('zh-CN')}
                            </p>
                          </div>
                          <button
                            onClick={(e) => handleDeleteChat(e, chat.id)}
                            className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-100 transition-all ml-2 touch-target focus-visible"
                            title="删除对话"
                            aria-label="删除此对话"
                          >
                            <Trash2 size={14} className="text-red-600" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-gray-200 space-y-2">
            <button
              onClick={toggleTheme}
              className="w-full flex items-center space-x-3 p-2 rounded-lg hover:bg-gray-200 transition-colors text-left touch-target focus-visible"
              aria-label={isDarkMode ? "切换到浅色主题" : "切换到深色主题"}
            >
              {isDarkMode ? <Sun size={16} /> : <Moon size={16} />}
              <span className="text-sm">{isDarkMode ? '浅色模式' : '深色模式'}</span>
            </button>
            
            <button
              className="w-full flex items-center space-x-3 p-2 rounded-lg hover:bg-gray-200 transition-colors text-left touch-target focus-visible"
              aria-label="设置"
            >
              <Settings size={16} />
              <span className="text-sm">设置</span>
            </button>
            
            <div className="text-xs text-gray-500 text-center pt-2">
              Project Yuzuriha v1.0
            </div>
          </div>
        </div>
      </aside>
    </>
  )
}