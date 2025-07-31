'use client'

import ChatInterfaceD1 from '@/components/ChatInterfaceD1'
import ErrorBoundary from '@/components/ErrorBoundary'

export default function HomePage() {
  return (
    <ErrorBoundary>
      <ChatInterfaceD1 />
    </ErrorBoundary>
  )
}