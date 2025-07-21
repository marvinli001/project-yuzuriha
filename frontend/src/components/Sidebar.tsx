'use client'

import { useEffect, useRef } from 'react'
import { ChatHistory } from '@/types/chat'
import { X, Plus, MessageSquare, Trash2 } from 'lucide-react'

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

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden" />
      )}
      
      {/* Sidebar */}
      <div
        ref={sidebarRef}
        className={`fixed left-0 top-0 h-full w-80 bg-chat-sidebar border-r border-gray-700 transform transition-transform duration-300 ease-in-out z-50 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        } md:relative md:translate-x-0 md:z-0`}
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-700">
            <h2 className="text-lg font-semibold text-white">Chats</h2>
            <div className="flex items-center space-x-2">
              <button
                onClick={onNewChat}
                className="p-2 rounded-lg hover:bg-gray-700 transition-colors"
                title="New Chat"
              >
                <Plus size={20} className="text-gray-400" />
              </button>
              <button
                onClick={onClose}
                className="p-2 rounded-lg hover:bg-gray-700 transition-colors md:hidden"
              >
                <X size={20} className="text-gray-400" />
              </button>
            </div>
          </div>

          {/* Chat History */}
          <div className="flex-1 overflow-y-auto p-2">
            {chatHistory.length === 0 ? (
              <div className="text-center text-gray-500 mt-8">
                <MessageSquare size={48} className="mx-auto mb-2 opacity-50" />
                <p>No conversations yet</p>
              </div>
            ) : (
              <div className="space-y-1">
                {chatHistory.map((chat) => (
                  <div
                    key={chat.id}
                    className={`group relative flex items-center p-3 rounded-lg cursor-pointer transition-colors ${
                      chat.id === currentChatId
                        ? 'bg-gray-700 text-white'
                        : 'hover:bg-gray-700 text-gray-300'
                    }`}
                    onClick={() => onLoadChat(chat.id)}
                  >
                    <MessageSquare size={16} className="mr-3 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="truncate text-sm font-medium">
                        {chat.title}
                      </p>
                      <p className="text-xs text-gray-500">
                        {new Date(chat.timestamp).toLocaleDateString()}
                      </p>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        onDeleteChat(chat.id)
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-600 transition-all ml-2"
                      title="Delete chat"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-gray-700 text-xs text-gray-500">
            Project Yuzuriha v1.0
          </div>
        </div>
      </div>
    </>
  )
}