# Project Yuzuriha 🧠

An AI chat assistant with persistent memory capabilities, built with modern web technologies and AI services.

## Architecture

```
🌐 Frontend (Next.js PWA) → 🚀 Backend (FastAPI) → 📦 Cloudflare D1 + 🔍 Zilliz Milvus → 🧠 OpenAI GPT-4o
```

## Features

- **PWA Support**: Works offline and can be installed as an app
- **Persistent Memory**: Remembers conversations using Cloudflare D1 and Milvus
- **Dual Storage**: Structured chat history (D1) + semantic search (Milvus)
- **Cloud Sync**: Chat history synchronized across devices
- **Modern UI**: ChatGPT-like interface with responsive design
- **Real-time Chat**: Fast, responsive conversations
- **Chat History**: Save and resume conversations
- **File Upload**: Support for images, documents, and audio
- **Voice Input**: Speech-to-text transcription

## Tech Stack

- **Frontend**: Next.js 14, TypeScript, Tailwind CSS, PWA
- **Backend**: FastAPI, Python 3.11
- **AI Model**: OpenAI GPT-4o
- **Chat Storage**: Cloudflare D1 (SQLite-compatible)
- **Vector Database**: Zilliz Cloud Milvus
- **Embeddings**: OpenAI text-embedding-3-small
- **File Storage**: Local uploads with cloud sync

## Quick Start

### Prerequisites

1. OpenAI API key
2. Zilliz Cloud account and cluster
3. Cloudflare account with D1 database (optional, for cloud sync)
4. Node.js 18+ and Python 3.11+

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd project-yuzuriha
```

2. **Backend Setup**
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
python main.py
```

3. **Frontend Setup**
```bash
cd frontend
npm install
npm run dev
```

4. **Using Docker (Recommended)**
```bash
# Copy environment variables
cp backend/.env.example .env
# Edit .env with your API keys
docker-compose up --build
```

### Environment Variables

Create a `.env` file in the backend directory:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_CHAT_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Milvus Configuration
MILVUS_URI=https://in03-xxx.api.gcp-us-west1.zillizcloud.com
MILVUS_TOKEN=your_zilliz_token_here
MILVUS_COLLECTION_NAME=yuzuriha_memories

# Cloudflare D1 Configuration (Optional)
CLOUDFLARE_ACCOUNT_ID=your_account_id
CLOUDFLARE_D1_DATABASE_ID=your_database_id
CLOUDFLARE_API_TOKEN=your_api_token
CLOUDFLARE_D1_DATABASE_NAME=yuzuriha_chat_db

# API Authentication
API_SECRET_KEY=your_secret_api_key_here
```

For D1 setup instructions, see [docs/cloudflare-d1-setup.md](docs/cloudflare-d1-setup.md).

## API Endpoints

### Chat API
- `POST /api/chat` - Send a message and get AI response (with dual-write to D1 and Milvus)
- `POST /chat` - Legacy chat endpoint

### D1 Chat History API
- `GET /api/chat/sessions` - Get all chat sessions
- `POST /api/chat/sessions` - Create new chat session
- `GET /api/chat/sessions/{id}` - Get specific chat session
- `PUT /api/chat/sessions/{id}` - Update chat session
- `DELETE /api/chat/sessions/{id}` - Delete chat session
- `GET /api/chat/sessions/{id}/messages` - Get messages in session
- `POST /api/chat/sessions/{id}/messages` - Add message to session
- `GET /api/chat/search` - Search chat messages
- `GET /api/chat/stats` - Get D1 database statistics

### File and Voice API
- `POST /api/upload` - Upload files (images, documents, audio)
- `POST /api/transcribe` - Convert audio to text

### System API
- `GET /health` - Health check for all services
- `GET /api/stats` - Get memory and system statistics

## PWA Features

- **Offline Support**: Core functionality works without internet
- **App Installation**: Can be installed as a native app
- **Full Screen**: Immersive chat experience
- **Responsive Design**: Works on all devices

## Storage System

The app uses a sophisticated dual-storage system:

### 1. Cloudflare D1 (Structured Storage)
- **Purpose**: Chat sessions and message history
- **Benefits**: Fast queries, relational data, cloud sync
- **Tables**: `chat_sessions`, `chat_messages`
- **Features**: Full CRUD operations, search, statistics

### 2. Zilliz Milvus (Vector Storage)
- **Purpose**: Semantic memory and context retrieval
- **Benefits**: AI-powered similarity search, contextual responses
- **Data**: Message embeddings, emotional context, interaction types
- **Features**: Vector similarity search, memory weight scoring

### Storage Modes
- **Cloud + Local**: D1 for structured data, localStorage for offline support
- **Local Only**: localStorage fallback when D1 is unavailable
- **Dual Write**: All messages stored in both systems simultaneously

This enables the AI to:
- Remember complete conversation history
- Find semantically related past discussions
- Provide contextually aware responses
- Sync chat history across devices
- Work offline with local storage fallback

## Development

### Frontend Development
```bash
cd frontend
npm run dev
```

### Backend Development
```bash
cd backend
uvicorn main:app --reload
```

### Building for Production
```bash
# Frontend
cd frontend
npm run build

# Backend
cd backend
pip install -r requirements.txt
```

## Deployment

### Using Docker
```bash
docker-compose up -d
```

### Manual Deployment
1. Deploy backend to a Python hosting service
2. Deploy frontend to Vercel, Netlify, or similar
3. Update API URLs in environment variables

## Configuration

### Zilliz Cloud Setup
1. Create a cluster on Zilliz Cloud
2. Get your endpoint URI and token
3. Add to environment variables

### Cloudflare D1 Setup
1. Create a Cloudflare account
2. Set up a D1 database
3. Configure API token and database IDs
4. See detailed instructions: [docs/cloudflare-d1-setup.md](docs/cloudflare-d1-setup.md)

### Authentication
The API uses Bearer token authentication. Set `API_SECRET_KEY` in your environment variables.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
1. Check the GitHub issues
2. Create a new issue with details
3. Include logs and error messages

---

Built with ❤️ for the future of AI-powered conversations