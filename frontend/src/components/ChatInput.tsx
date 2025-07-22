'use client'
import React, { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Paperclip, Mic, MicOff, X, Image, FileText } from 'lucide-react'
import { uploadFiles, UploadedFile, formatFileSize } from '../utils/fileUtils'
import { useVoiceRecording } from '../hooks/useVoiceRecording'

interface ChatInputProps {
  onSendMessage: (message: string, files?: UploadedFile[]) => void
  disabled?: boolean
  hasMessages?: boolean
}

export default function ChatInput({ onSendMessage, disabled = false, hasMessages = false }: ChatInputProps) {
  const [message, setMessage] = useState('')
  const [isComposing, setIsComposing] = useState(false)
  const [attachedFiles, setAttachedFiles] = useState<UploadedFile[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  const {
    isRecording,
    isTranscribing,
    startRecording,
    stopRecording,
    cancelRecording,
  } = useVoiceRecording()

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
    if ((message.trim() || attachedFiles.length > 0) && !disabled && !isComposing) {
      onSendMessage(message.trim(), attachedFiles)
      setMessage('')
      setAttachedFiles([])
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

  // 文件上传处理
  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    setIsUploading(true)
    try {
      const uploadedFiles = await uploadFiles(files)
      setAttachedFiles(prev => [...prev, ...uploadedFiles])
    } catch (error) {
      console.error('File upload failed:', error)
      // 可以添加错误提示
    } finally {
      setIsUploading(false)
      // 重置文件输入
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  // 移除附件
  const removeFile = (fileId: string) => {
    setAttachedFiles(prev => prev.filter(file => file.id !== fileId))
  }

  // 语音录制处理
  const handleVoiceToggle = async () => {
    if (isRecording) {
      try {
        const transcribedText = await stopRecording()
        setMessage(prev => prev + (prev ? ' ' : '') + transcribedText)
      } catch (error) {
        console.error('Voice recording failed:', error)
        // 可以添加错误提示
      }
    } else {
      try {
        await startRecording()
      } catch (error) {
        console.error('Failed to start recording:', error)
        // 可以添加错误提示
      }
    }
  }

  // 取消录音
  const handleCancelRecording = () => {
    cancelRecording()
  }

  // 文件图标
  const getFileIcon = (type: string) => {
    switch (type) {
      case 'image':
        return <Image size={14} />
      case 'document':
        return <FileText size={14} />
      default:
        return <Paperclip size={14} />
    }
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
        {/* 附件预览 */}
        {attachedFiles.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-2">
            {attachedFiles.map(file => (
              <div key={file.id} className="flex items-center gap-2 bg-gray-100 rounded-lg px-3 py-2 text-sm">
                {getFileIcon(file.type)}
                <span className="truncate max-w-32">{file.filename}</span>
                <span className="text-gray-500">({formatFileSize(file.size)})</span>
                <button
                  type="button"
                  onClick={() => removeFile(file.id)}
                  className="text-gray-400 hover:text-red-500 transition-colors"
                >
                  <X size={14} />
                </button>
              </div>
            ))}
          </div>
        )}

        <div className={homePageStyle.inputContainerClass}>
          {/* 附件按钮 */}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept="image/*,.pdf,.txt,.doc,.docx,audio/*"
            onChange={handleFileSelect}
            className="hidden"
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled || isUploading}
            className="flex-shrink-0 p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors touch-target focus-visible disabled:opacity-50"
            title="上传附件"
            aria-label="上传附件"
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

          {/* 录音状态指示器 */}
          {isRecording && (
            <div className="flex items-center gap-2 text-red-600">
              <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
              <span className="text-xs">录音中...</span>
              <button
                type="button"
                onClick={handleCancelRecording}
                className="p-1 hover:bg-red-100 rounded"
                title="取消录音"
              >
                <X size={12} />
              </button>
            </div>
          )}

          {/* 发送/语音按钮 */}
          <div className="flex-shrink-0 flex items-center gap-2">
            {message.trim() || attachedFiles.length > 0 ? (
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
                onClick={handleVoiceToggle}
                disabled={disabled || isTranscribing}
                className={`p-2 rounded-lg transition-colors ${
                  isRecording 
                    ? 'bg-red-100 text-red-600 hover:bg-red-200' 
                    : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'
                }`}
                title={isRecording ? "停止录音" : isTranscribing ? "转换中..." : "开始录音"}
              >
                {isTranscribing ? (
                  <div className="animate-spin w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full" />
                ) : isRecording ? (
                  <MicOff size={18} />
                ) : (
                  <Mic size={18} />
                )}
              </button>
            )}
          </div>
        </div>
        
        {/* 上传状态 */}
        {isUploading && (
          <div className="text-xs text-gray-500 mt-1 text-center">
            正在上传文件...
          </div>
        )}
      </form>
    </div>
  )
}