# CLAUDE CODE BUILD PROMPT - TahlilchiAI MVP

## YOUR MISSION
Build a production-ready legal AI assistant for Uzbekistan in 4 weeks. Focus: intelligent chat with RAG, not just search.

## TECH STACK (FINAL DECISION)

### Backend
- **Framework**: FastAPI
- **Database**: PostgreSQL + Qdrant (vector DB)
- **LLM**: OpenAI GPT-4o (best Uzbek/Russian support)
- **Embeddings**: multilingual-e5-large

### Frontend  
- **Framework**: Streamlit (MVP speed) → React later
- **Styling**: Streamlit native + custom CSS

### Infrastructure
- Docker Compose for local dev
- Everything containerized

## PROJECT STRUCTURE

```
tahlilchi-ai/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── agents/
│   │   │   ├── orchestrator.py  # Intent routing
│   │   │   ├── clarifier.py     # Follow-up questions
│   │   │   ├── retrieval.py     # RAG pipeline
│   │   │   └── document.py      # Doc analysis
│   │   ├── core/
│   │   │   ├── rag.py           # RAG implementation
│   │   │   ├── embeddings.py    # Embedding logic
│   │   │   └── llm.py           # LLM wrapper
│   │   ├── database/
│   │   │   ├── models.py        # SQLAlchemy models
│   │   │   └── crud.py          # Database operations
│   │   └── utils/
│   │       ├── chunking.py      # Document chunking
│   │       └── indexing.py      # Vector DB indexing
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── app.py                   # Streamlit app
│   ├── components/
│   │   ├── chat.py
│   │   └── document_upload.py
│   ├── Dockerfile
│   └── requirements.txt
├── legal_corpus/                # Legal documents
│   ├── civil_code/
│   ├── criminal_code/
│   └── administrative_code/
├── docker-compose.yml
├── .env.example
└── README.md
```

## BUILD ORDER (FOLLOW EXACTLY)

### PHASE 1: Foundation (Days 1-3)

#### Step 1: Project Setup
```bash
# Create structure
mkdir -p tahlilchi-ai/{backend/app/{agents,core,database,utils},frontend/components,legal_corpus}
cd tahlilchi-ai

# Initialize git
git init
```

#### Step 2: Docker Compose
Create `docker-compose.yml`:
```yaml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: tahlilchi
      POSTGRES_PASSWORD: dev_password
      POSTGRES_DB: legal_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://tahlilchi:dev_password@postgres:5432/legal_db
      - QDRANT_URL=http://qdrant:6333
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - postgres
      - qdrant
    volumes:
      - ./backend:/app
      - ./legal_corpus:/app/legal_corpus

  frontend:
    build: ./frontend
    ports:
      - "8501:8501"
    environment:
      - BACKEND_URL=http://backend:8000
    depends_on:
      - backend
    volumes:
      - ./frontend:/app

volumes:
  postgres_data:
  qdrant_data:
```

#### Step 3: Backend Requirements
Create `backend/requirements.txt`:
```
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
qdrant-client==1.7.0
sentence-transformers==2.2.2
openai==1.3.7
python-multipart==0.0.6
pydantic==2.5.0
python-dotenv==1.0.0
langchain==0.1.0
pypdf==3.17.1
python-docx==1.1.0
```

#### Step 4: Database Models
Create `backend/app/database/models.py`:
```python
from sqlalchemy import Column, String, Text, ARRAY, DateTime, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class LegalDocument(Base):
    __tablename__ = "legal_documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(String, unique=True, nullable=False)
    document_type = Column(String(50), nullable=False)
    law_category = Column(String(50), nullable=False)
    title = Column(Text, nullable=False)
    article_number = Column(String(50))
    content = Column(Text, nullable=False)
    language = Column(String(10), nullable=False)
    keywords = Column(ARRAY(String))
    created_at = Column(DateTime, default=datetime.utcnow)

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_state = Column(JSON)
    intent_classification = Column(String(100))
    legal_domain = Column(String(50))
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True))
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    metadata_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### PHASE 2: RAG Core (Days 4-7)

#### Step 5: Embedding Service
Create `backend/app/core/embeddings.py`:
```python
from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np

class EmbeddingService:
    def __init__(self):
        self.model = SentenceTransformer('intfloat/multilingual-e5-large')
        
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for single text"""
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()
    
    def embed_query(self, query: str) -> List[float]:
        """Embed user query with instruction prefix"""
        # E5 models work better with instruction
        prefixed = f"query: {query}"
        return self.embed_text(prefixed)

# Singleton instance
embedding_service = EmbeddingService()
```

#### Step 6: RAG Implementation
Create `backend/app/core/rag.py`:
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from typing import List, Dict
import openai
import os

class RAGSystem:
    def __init__(self):
        self.qdrant = QdrantClient(url=os.getenv("QDRANT_URL"))
        self.collection_name = "legal_corpus"
        self.embedding_service = embedding_service
        openai.api_key = os.getenv("OPENAI_API_KEY")
        
    def create_collection(self):
        """Create Qdrant collection if not exists"""
        try:
            self.qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=1024,  # multilingual-e5-large dimension
                    distance=Distance.COSINE
                )
            )
        except Exception as e:
            print(f"Collection exists or error: {e}")
    
    def index_document(self, doc_id: str, content: str, metadata: Dict):
        """Index a single document"""
        embedding = self.embedding_service.embed_text(content)
        
        point = PointStruct(
            id=doc_id,
            vector=embedding,
            payload={
                "content": content,
                **metadata
            }
        )
        
        self.qdrant.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
    
    def search(self, query: str, limit: int = 5) -> List[Dict]:
        """Semantic search"""
        query_embedding = self.embedding_service.embed_query(query)
        
        results = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=limit
        )
        
        return [
            {
                "content": hit.payload["content"],
                "article": hit.payload.get("article_number"),
                "law": hit.payload.get("title"),
                "score": hit.score
            }
            for hit in results
        ]
    
    def generate_answer(self, query: str, context_chunks: List[Dict]) -> Dict:
        """Generate answer using GPT-4o"""
        
        # Combine context
        context = "\n\n".join([
            f"[{chunk['article']}] {chunk['content']}"
            for chunk in context_chunks
        ])
        
        system_prompt = """You are a legal assistant helping Uzbek citizens understand the law.

Rules:
1. Answer ONLY based on the laws provided
2. Use simple Russian or Uzbek language
3. Include article numbers when citing law
4. If law doesn't answer question, say so
5. Never make up information

Structure:
1. Direct answer (2-3 sentences)
2. Which law applies (mention article)
3. What to do next (practical steps)"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Laws:\n{context}\n\nQuestion: {query}"}
        ]
        
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.3
        )
        
        return {
            "answer": response.choices[0].message.content,
            "sources": context_chunks,
            "model": "gpt-4o"
        }

# Singleton
rag_system = RAGSystem()
```

### PHASE 3: Agents (Days 8-14)

#### Step 7: Orchestrator Agent
Create `backend/app/agents/orchestrator.py`:
```python
import openai
import json
from typing import Dict

class OrchestratorAgent:
    """Routes queries to appropriate agents"""
    
    def classify_intent(self, message: str) -> Dict:
        """Classify user intent and legal domain"""
        
        prompt = f"""Classify this message:

Message: {message}

Return JSON:
{{
  "intent": "legal_query" | "document_analysis" | "lawyer_needed" | "general_chat",
  "domain": "civil" | "criminal" | "administrative" | "labor" | "tax" | "other",
  "clarity": "clear" | "needs_clarification",
  "urgency": "high" | "medium" | "low"
}}"""

        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        
        return json.loads(response.choices[0].message.content)

orchestrator = OrchestratorAgent()
```

#### Step 8: Clarifier Agent
Create `backend/app/agents/clarifier.py`:
```python
import openai
import json
from typing import Dict, List

class ClarifierAgent:
    """Generates follow-up questions"""
    
    DOMAIN_QUESTIONS = {
        "administrative": [
            "Где произошло событие?",
            "Когда это случилось?",
            "Есть ли у вас документы (протокол, квитанция)?",
            "Что именно вам сказали?"
        ],
        "labor": [
            "Сколько времени вы работали?",
            "Есть ли трудовой договор?",
            "Какова причина увольнения?",
            "Получили ли письменное уведомление?"
        ],
        "civil": [
            "Какой тип договора?",
            "Когда был подписан?",
            "Какая сумма?",
            "Есть письменный договор?"
        ]
    }
    
    def generate_questions(self, message: str, domain: str) -> List[str]:
        """Generate targeted clarification questions"""
        
        template_questions = self.DOMAIN_QUESTIONS.get(domain, [])
        
        prompt = f"""User message: {message}
Legal domain: {domain}

Template questions: {template_questions}

Generate 2-3 MOST IMPORTANT questions needed to provide accurate legal advice.
Questions should be:
- Specific and actionable
- In simple Russian
- Help determine exact legal situation

Return JSON:
{{
  "questions": ["Question 1", "Question 2"],
  "reasoning": "Why these matter"
}}"""

        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        )
        
        result = json.loads(response.choices[0].message.content)
        return result["questions"]

clarifier = ClarifierAgent()
```

### PHASE 4: API Endpoints (Days 15-17)

#### Step 9: Main FastAPI App
Create `backend/app/main.py`:
```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from agents.orchestrator import orchestrator
from agents.clarifier import clarifier
from core.rag import rag_system

app = FastAPI(title="TahlilchiAI API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    conversation_history: List[Message] = []

class ChatResponse(BaseModel):
    answer: str
    sources: List[dict] = []
    confidence: str = "high"
    clarification_needed: bool = False
    clarification_questions: List[str] = []

# Endpoints
@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint"""
    
    try:
        # 1. Classify intent
        intent = orchestrator.classify_intent(request.message)
        
        # 2. Handle clarification
        if intent["clarity"] == "needs_clarification":
            questions = clarifier.generate_questions(
                request.message,
                intent["domain"]
            )
            
            return ChatResponse(
                answer="Чтобы помочь вам лучше, мне нужна дополнительная информация:",
                clarification_needed=True,
                clarification_questions=questions
            )
        
        # 3. Handle legal query
        if intent["intent"] == "legal_query":
            # Search legal corpus
            chunks = rag_system.search(request.message, limit=5)
            
            if not chunks:
                return ChatResponse(
                    answer="Извините, я не могу найти точную информацию в законодательстве.",
                    confidence="none"
                )
            
            # Generate answer
            result = rag_system.generate_answer(request.message, chunks)
            
            return ChatResponse(
                answer=result["answer"],
                sources=result["sources"]
            )
        
        # 4. Handle general chat
        return ChatResponse(
            answer="Здравствуйте! Я юридический помощник. Опишите вашу ситуацию.",
            confidence="high"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### PHASE 5: Frontend (Days 18-21)

#### Step 10: Streamlit App
Create `frontend/app.py`:
```python
import streamlit as st
import requests
import json

st.set_page_config(
    page_title="TahlilchiAI",
    page_icon="⚖️",
    layout="wide"
)

# Backend URL
BACKEND_URL = "http://backend:8000"

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'awaiting_clarification' not in st.session_state:
    st.session_state.awaiting_clarification = False

# Title
st.title("⚖️ TahlilchiAI")
st.caption("Ваш юридический помощник")

# Chat container
chat_container = st.container()

with chat_container:
    # Display messages
    for msg in st.session_state.messages:
        with st.chat_message(msg['role']):
            st.write(msg['content'])
            
            # Show clarification questions
            if msg.get('clarification_questions'):
                st.info("Пожалуйста, ответьте на следующие вопросы:")
                for q in msg['clarification_questions']:
                    st.write(f"• {q}")
            
            # Show sources
            if msg.get('sources'):
                with st.expander("📚 Правовая основа"):
                    for source in msg['sources']:
                        st.caption(f"**Статья {source['article']}** - {source['law']}")
                        st.text(source['content'][:300] + "...")

# User input
if prompt := st.chat_input("Опишите вашу ситуацию..."):
    # Add user message
    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })
    
    # Call API
    with st.spinner("Анализирую..."):
        try:
            response = requests.post(
                f"{BACKEND_URL}/api/chat",
                json={
                    "message": prompt,
                    "conversation_history": [
                        {"role": m['role'], "content": m['content']}
                        for m in st.session_state.messages
                    ]
                },
                timeout=30
            )
            
            result = response.json()
            
            # Add assistant response
            st.session_state.messages.append({
                "role": "assistant",
                "content": result['answer'],
                "sources": result.get('sources', []),
                "clarification_questions": result.get('clarification_questions', [])
            })
            
        except Exception as e:
            st.error(f"Ошибка: {str(e)}")
    
    st.rerun()

# Sidebar
with st.sidebar:
    st.header("📊 Статистика")
    st.metric("Всего запросов", len(st.session_state.messages))
    
    st.divider()
    
    st.header("ℹ️ О проекте")
    st.write("""
    TahlilchiAI - AI-ассистент для понимания 
    законодательства Узбекистана.
    
    **Возможности:**
    - Ответы на правовые вопросы
    - Анализ договоров
    - Поиск подходящих юристов
    """)
    
    if st.button("Очистить чат"):
        st.session_state.messages = []
        st.rerun()
```

### PHASE 6: Document Ingestion (Days 22-24)

#### Step 11: Ingestion Script
Create `backend/scripts/ingest_legal_docs.py`:
```python
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.core.rag import rag_system
from app.database.models import LegalDocument, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pypdf
import re

def chunk_legal_document(text: str, article_pattern: str) -> list:
    """Split document by articles"""
    articles = re.split(article_pattern, text)
    chunks = []
    
    for i in range(1, len(articles), 2):  # Every odd element is article number
        if i + 1 < len(articles):
            article_num = articles[i].strip()
            content = articles[i + 1].strip()
            
            if len(content) > 50:  # Skip empty
                chunks.append({
                    "article_number": article_num,
                    "content": content
                })
    
    return chunks

def ingest_pdf(filepath: str, law_type: str, law_category: str):
    """Ingest a legal PDF document"""
    
    # Extract text from PDF
    reader = pypdf.PdfReader(filepath)
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text()
    
    # Chunk by articles (adjust pattern for Uzbek laws)
    article_pattern = r"(Статья\s+\d+)"
    chunks = chunk_legal_document(full_text, article_pattern)
    
    print(f"Found {len(chunks)} articles in {filepath}")
    
    # Index each chunk
    for chunk in chunks:
        doc_id = f"{law_category}_{chunk['article_number']}"
        
        metadata = {
            "document_type": law_type,
            "law_category": law_category,
            "title": os.path.basename(filepath),
            "article_number": chunk['article_number'],
            "language": "ru"
        }
        
        # Index in Qdrant
        rag_system.index_document(doc_id, chunk['content'], metadata)
        
        print(f"Indexed: {doc_id}")

if __name__ == "__main__":
    # Create collection
    rag_system.create_collection()
    
    # Ingest all PDFs in legal_corpus/
    corpus_dir = "/app/legal_corpus"
    
    for subdir in os.listdir(corpus_dir):
        subdir_path = os.path.join(corpus_dir, subdir)
        if os.path.isdir(subdir_path):
            for filename in os.listdir(subdir_path):
                if filename.endswith('.pdf'):
                    filepath = os.path.join(subdir_path, filename)
                    print(f"\nProcessing: {filepath}")
                    
                    # Determine category from directory name
                    category = subdir.replace('_', ' ').title()
                    
                    ingest_pdf(filepath, "law", category)
    
    print("\n✅ Ingestion complete!")
```

## CRITICAL SUCCESS FACTORS

### 1. **FOCUS ON CHAT INTELLIGENCE** ⭐
- Clarifier agent is your secret weapon
- Show it asking follow-up questions in demo
- This impresses judges more than fancy UI

### 2. **PREVENT HALLUCINATIONS** ⭐⭐⭐
- ALWAYS verify retrieved chunks are relevant
- Force grounding in legal sources
- Show confidence scores

### 3. **SIMPLE LANGUAGE** ⭐⭐
- All responses in easy Russian/Uzbek
- No legal jargon
- Explain like talking to friend

### 4. **FAST ITERATION** ⭐
- Test early and often
- 100+ queries minimum
- Fix what breaks

## TESTING CHECKLIST

Before demo day:

- [ ] 10 successful chat scenarios prepared
- [ ] Clarification works for vague queries
- [ ] Retrieval accuracy >70% on test set
- [ ] Response time <3 seconds
- [ ] Works on mobile
- [ ] Backup demo video ready
- [ ] Pitch presentation polished

## DEMO SCRIPT

**Scenario 1: Simple Query**
```
User: "Я получил штраф за парковку"
AI: [Shows intent classification → administrative]
AI: [Retrieves Article 128 from Admin Code]
AI: "Да, штрафы за парковку законны согласно статье 128..."
```

**Scenario 2: Intelligent Clarification (WOW MOMENT)**
```
User: "Меня уволили"
AI: [Clarifier activates]
AI: "Чтобы помочь вам:
     1. Сколько времени работали?
     2. Какова причина?
     3. Есть договор?"
     
[Judges see: "This is not simple search!"]
```

## GO BUILD IT! 🚀

Start with Phase 1 today. You have everything you need to win.

**Questions? Debug issues? Just ask me and I'll guide you through.**

Remember: 
- Judges want to see INTELLIGENCE, not features
- Users want CLARITY, not complexity  
- You want to WIN, not just participate

Now go make it happen! 💪
