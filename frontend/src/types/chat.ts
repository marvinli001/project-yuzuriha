export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface ChatHistory {
  id: string;
  title: string;
  messages: Message[];
  timestamp: string;
}

export interface ChatResponse {
  response: string;
  memory_stored: boolean;
}