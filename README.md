# Project Yuzuriha 🧠

An AI chat assistant with persistent memory capabilities, built with modern web technologies and AI services.

## Architecture

```
🌐 Frontend (Next.js PWA) → 🚀 Backend (FastAPI) → 📦 SuperMemory MCP + 🔍 Zilliz Milvus → 🧠 OpenAI GPT-4o
```

## Features

- **PWA Support**: Works offline and can be installed as an app
- **Persistent Memory**: Remembers conversations using SuperMemory MCP
- **Semantic Search**: Vector-based memory retrieval with Zilliz Cloud Milvus
- **Modern UI**: ChatGPT-like interface with responsive design
- **Real-time Chat**: Fast, responsive conversations
- **Chat History**: Save and resume conversations

## Tech Stack

- **Frontend**: Next.js 14, TypeScript, Tailwind CSS, PWA
- **Backend**: FastAPI, Python 3.11
- **AI Model**: OpenAI GPT-4o
- **Memory System**: SuperMemory MCP
- **Vector Database**: Zilliz Cloud Milvus
- **Embeddings**: OpenAI text-embedding-3-small

## Quick Start

### Prerequisites

1. OpenAI API key
2. Zilliz Cloud account and cluster
3. SuperMemory MCP instance
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
OPENAI_API_KEY=your_openai_api_key_here
MILVUS_URI=https://in03-xxx.api.gcp-us-west1.zillizcloud.com
MILVUS_TOKEN=your_zilliz_token_here
SUPERMEMORY_API_URL=https://your-supermemory-instance.com
SUPERMEMORY_API_KEY=your_supermemory_api_key_here
```

## API Endpoints

- `POST /api/chat` - Send a message and get AI response
- `GET /api/memories` - Retrieve stored memories
- `DELETE /api/memories` - Clear all memories
- `GET /health` - Health check for all services

## PWA Features

- **Offline Support**: Core functionality works without internet
- **App Installation**: Can be installed as a native app
- **Full Screen**: Immersive chat experience
- **Responsive Design**: Works on all devices

## Memory System

The app uses a dual-layer memory system:

1. **SuperMemory MCP**: Long-term structured memory storage
2. **Zilliz Milvus**: Vector embeddings for semantic search

This enables the AI to:
- Remember past conversations
- Find relevant context automatically
- Provide personalized responses
- Learn from interactions

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

### SuperMemory Setup
1. Deploy SuperMemory MCP instance
2. Get API endpoint and key
3. Configure in environment variables

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