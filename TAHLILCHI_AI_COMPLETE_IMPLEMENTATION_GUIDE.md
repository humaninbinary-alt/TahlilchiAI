# TahlilchiAI - Complete Technical Implementation Guide
## AI-Powered Legal Assistance Platform for Uzbekistan

---

## 🎯 EXECUTIVE SUMMARY

**Project Goal**: Build a sophisticated legal AI assistant that demonstrates technical excellence for hackathon judges while genuinely serving Uzbek citizens.

**Key Differentiators**:
1. **Advanced RAG Architecture** - Not just search, but intelligent legal reasoning
2. **Multi-Agent Orchestration** - Smart question refinement and clarification
3. **Zero-Hallucination Mode** - Every answer grounded in official legal sources
4. **Uzbek-First Design** - Native language support, not translation layer

**Timeline**: 4 weeks (MVP)  
**Team**: 5 people  
**Demo Focus**: Chat assistant with document analysis

---

## 📊 SYSTEM ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│                    (Web App - Streamlit/React)                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                    ORCHESTRATOR AGENT                           │
│  (Intent Classification, Conversation Management, Routing)      │
└─────────┬──────────────┬──────────────┬────────────────────────┘
          │              │              │
    ┌─────▼─────┐  ┌────▼────┐  ┌──────▼──────┐
    │ Clarifier │  │   RAG   │  │   Document  │
    │   Agent   │  │ System  │  │   Analyzer  │
    └───────────┘  └────┬────┘  └─────────────┘
                        │
         ┌──────────────┼──────────────┐
         │              │              │
    ┌────▼────┐  ┌──────▼──────┐  ┌───▼────┐
    │Retriever│  │  Re-Ranker  │  │  LLM   │
    │ Engine  │  │             │  │Generator│
    └─────────┘  └─────────────┘  └────────┘
                        │
         ┌──────────────┼──────────────┐
    ┌────▼────┐  ┌──────▼──────┐  ┌───▼─────┐
    │ Vector  │  │Legal Corpus │  │Citation │
    │   DB    │  │  PostgreSQL │  │ Engine  │
    └─────────┘  └─────────────┘  └─────────┘
```

---

## 🧠 LLM SELECTION & STRATEGY

### Recommended LLM Setup

Based on research for Uzbek/Russian language support:

**PRIMARY LLM (Orchestrator & Generation)**:
- **GPT-4o** or **Claude Sonnet 4.5**
  - Best multilingual support including Uzbek/Russian
  - Strong reasoning capabilities
  - Low hallucination rate
  - API-based (no infrastructure needed for MVP)

**EMBEDDING MODEL**:
- **multilingual-e5-large** (Free, open-source)
  - Supports 100+ languages including Uzbek/Russian
  - 1024 dimensions
  - Good for semantic search
  - Alternative: **LaBSE** (Language-agnostic BERT)

**FALLBACK/COST OPTIMIZATION**:
- **Llama 3.1 70B** via Groq API (cheap, fast)
- **Qwen 2.5** (strong multilingual, cost-effective)

### Why NOT Translation Layer?

✅ **Direct Uzbek/Russian LLM**:
- Preserves legal nuance
- No meaning loss
- Faster response
- Better cultural context

❌ **Translation Layer**:
- Loses legal terminology precision
- Double latency (translate → process → translate back)
- Potential legal misinterpretation

### Cost Estimates (Monthly - MVP)

```
Development/Testing Phase:
- GPT-4o API: ~$50-100/month (light usage)
- Claude API: ~$50-100/month
- Vector DB Hosting: $25/month (Pinecone free tier or Qdrant)
- Compute: $0 (local dev)
TOTAL: ~$100-200/month

Production (Post-Hackathon):
- LLM API: $500-2000/month (depends on users)
- Vector DB: $100-500/month
- Hosting: $100-300/month (AWS/GCP)
- Storage: $50-100/month
TOTAL: ~$750-3000/month for 1000-5000 users
```

---

## 🏗️ DETAILED RAG ARCHITECTURE

### 1. Document Ingestion Pipeline

```python
# PHASE 1: Document Collection & Preprocessing

Document Sources:
├── Constitution of Uzbekistan
├── Civil Code
├── Criminal Code  
├── Administrative Code
├── Labor Code
├── Tax Code
├── Police Procedure Regulations
└── Court Precedents (if available)

Preprocessing Steps:
1. PDF Extraction → Use PyMuPDF or Unstructured.io
2. OCR (if needed) → Tesseract for Uzbek/Russian
3. Structure Detection → Identify Articles, Sections, Clauses
4. Metadata Extraction → Law type, date, article numbers
5. Text Cleaning → Remove headers/footers, normalize spacing
```

### 2. Metadata Schema

```json
{
  "document_id": "uz_civil_code_art_123",
  "document_type": "law",
  "law_category": "civil",
  "title": "Гражданский кодекс Республики Узбекистан",
  "article_number": "123",
  "section": "Договор",
  "effective_date": "2024-01-01",
  "language": "russian",
  "content": "Full article text...",
  "keywords": ["contract", "agreement", "obligation"],
  "related_articles": ["124", "125", "456"],
  "jurisdiction": "uzbekistan",
  "last_updated": "2024-11-01"
}
```

### 3. Chunking Strategy

**Legal documents require special chunking**:

```python
# SMART CHUNKING RULES

1. ARTICLE-LEVEL CHUNKING (Primary):
   - Each legal article = 1 chunk
   - Preserves complete legal context
   - Includes article number in metadata

2. HIERARCHICAL CHUNKING (For long articles):
   - Split by subsections
   - Maintain parent-child relationships
   - Cross-reference related sections

3. CONTEXT WINDOWS:
   - Include previous/next article numbers
   - Add section header for context
   - Max chunk size: 512 tokens
   - Overlap: 50 tokens

Example:
┌─────────────────────────────────────┐
│ Article 123: Contract Definition    │
│ (Parent Context: Section 5 - Civil) │
│                                     │
│ Full article text...                │
│                                     │
│ Related: Art. 124, 125              │
└─────────────────────────────────────┘
```

### 4. Embedding & Indexing

```python
# HYBRID SEARCH ARCHITECTURE

┌─────────────────────────────────────┐
│         USER QUERY                  │
│ "What are my rights if fired?"     │
└──────────┬──────────────────────────┘
           │
    ┌──────▼───────┐
    │ Query Parser │
    └──────┬───────┘
           │
    ┌──────▼─────────────────────────┐
    │  Parallel Search               │
    │  ┌─────────────┬─────────────┐ │
    │  │  Semantic   │   Keyword   │ │
    │  │  (Vector)   │   (BM25)    │ │
    │  └──────┬──────┴──────┬──────┘ │
    └─────────┼─────────────┼────────┘
              │             │
    ┌─────────▼─────────────▼────────┐
    │   FUSION RANKER                │
    │   (Reciprocal Rank Fusion)     │
    └────────────┬───────────────────┘
                 │
    ┌────────────▼───────────────────┐
    │   RE-RANKER (Cross-Encoder)    │
    │   - Score relevance            │
    │   - Legal context matching     │
    └────────────┬───────────────────┘
                 │
    ┌────────────▼───────────────────┐
    │   TOP K CHUNKS (K=5-10)        │
    └────────────────────────────────┘

# Vector DB Options:
1. Pinecone (managed, free tier)
2. Qdrant (open-source, can self-host)
3. Weaviate (good for legal due to filtering)

# Indexing Code Example:
from sentence_transformers import SentenceTransformer
import qdrant_client

model = SentenceTransformer('intfloat/multilingual-e5-large')
client = qdrant_client.QdrantClient(":memory:")

# Create collection
client.create_collection(
    collection_name="legal_corpus",
    vectors_config=qdrant_client.models.VectorParams(
        size=1024,  # e5-large dimension
        distance=qdrant_client.models.Distance.COSINE
    )
)

# Index documents
for doc in legal_documents:
    embedding = model.encode(doc['content'])
    client.upsert(
        collection_name="legal_corpus",
        points=[{
            "id": doc['document_id'],
            "vector": embedding,
            "payload": doc  # All metadata
        }]
    )
```

### 5. Re-Ranking System

```python
# CROSS-ENCODER RE-RANKER FOR LEGAL PRECISION

from sentence_transformers import CrossEncoder

# Use legal-tuned cross-encoder or general multilingual
reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-12-v2')

def rerank_results(query, retrieved_chunks):
    """
    Re-rank retrieved chunks using cross-encoder
    
    This is CRITICAL for legal accuracy - ensures we return
    the MOST relevant law, not just semantically similar text
    """
    pairs = [[query, chunk['content']] for chunk in retrieved_chunks]
    scores = reranker.predict(pairs)
    
    # Sort by score
    ranked = sorted(
        zip(retrieved_chunks, scores),
        key=lambda x: x[1],
        reverse=True
    )
    
    return [chunk for chunk, score in ranked]

# Re-ranking reduces hallucination by 60-80% in legal RAG
```

---

## 🤖 MULTI-AGENT ORCHESTRATION SYSTEM

This is **THE MOST IMPORTANT PART** for impressing judges. This is where you show intelligent reasoning, not just search.

### Agent Architecture

```python
"""
MULTI-AGENT SYSTEM FOR INTELLIGENT LEGAL REASONING

Agent Flow:
1. Orchestrator Agent (Router)
2. Clarifier Agent (Question Refinement)
3. Retrieval Agent (RAG System)
4. Verifier Agent (Hallucination Check)
5. Response Generator (Simple Language)
"""

class OrchestratorAgent:
    """
    Master agent that coordinates all other agents
    
    Responsibilities:
    - Classify user intent
    - Determine if clarification needed
    - Route to appropriate agent
    - Manage conversation state
    """
    
    def classify_intent(self, user_message):
        """
        Classify what the user wants
        
        Returns:
        - 'legal_query': Needs legal advice
        - 'document_analysis': Uploaded document
        - 'lawyer_needed': Complex case
        - 'general_chat': Greeting/casual
        """
        
        prompt = f"""
        Classify this user message into one category:
        
        Message: {user_message}
        
        Categories:
        - legal_query: User asking about laws, rights, procedures
        - document_analysis: User wants document reviewed
        - lawyer_needed: Case is too complex, needs real lawyer
        - general_chat: Greeting, thanks, casual conversation
        
        Also extract:
        - Legal domain: criminal, civil, administrative, tax, labor, etc.
        - Urgency: high, medium, low
        - Clarity: clear, needs_clarification
        
        Return JSON only:
        {{
          "intent": "legal_query",
          "domain": "administrative",
          "urgency": "medium",
          "clarity": "needs_clarification"
        }}
        """
        
        response = llm.generate(prompt)
        return json.loads(response)
    
    def route(self, intent_analysis, user_message, conversation_history):
        """
        Route to appropriate agent based on intent
        """
        if intent_analysis['intent'] == 'general_chat':
            return simple_response(user_message)
        
        if intent_analysis['clarity'] == 'needs_clarification':
            return ClarifierAgent().run(user_message, intent_analysis)
        
        if intent_analysis['intent'] == 'legal_query':
            return RetrievalAgent().run(user_message, intent_analysis)
        
        if intent_analysis['intent'] == 'document_analysis':
            return DocumentAnalyzerAgent().run(uploaded_doc)
        
        if intent_analysis['intent'] == 'lawyer_needed':
            return LawyerMatchingAgent().run(user_message, intent_analysis)


class ClarifierAgent:
    """
    THIS IS THE SECRET WEAPON FOR JUDGES
    
    Instead of answering immediately (and potentially hallucinating),
    this agent asks intelligent follow-up questions to get all details
    """
    
    def run(self, user_message, intent_analysis):
        """
        Generate targeted follow-up questions
        """
        
        domain = intent_analysis['domain']
        
        # Domain-specific question templates
        clarification_questions = {
            'administrative': [
                "Где вас остановила полиция? (Where did police stop you?)",
                "Вам выписали штраф или просто устное предупреждение? (Fine or warning?)",
                "У вас есть протокол или квитанция? (Do you have the protocol/receipt?)",
                "Когда это произошло? (When did this happen?)"
            ],
            'civil': [
                "Какой тип договора? (What type of contract?)",
                "Когда был подписан договор? (When was it signed?)",
                "Какая сумма указана? (What amount is specified?)",
                "Есть ли письменный договор? (Is there a written contract?)"
            ],
            'labor': [
                "Сколько времени вы работали в этой компании? (How long employed?)",
                "Есть ли у вас трудовой договор? (Do you have employment contract?)",
                "Какова причина увольнения? (What's the reason for termination?)",
                "Получили ли вы письменное уведомление? (Did you get written notice?)"
            ]
        }
        
        # Generate 2-3 most relevant questions using LLM
        prompt = f"""
        User said: {user_message}
        Legal domain: {domain}
        
        Based on this, what are the 2-3 MOST IMPORTANT questions we need answered
        to provide accurate legal guidance?
        
        Available question templates: {clarification_questions.get(domain, [])}
        
        Generate questions that are:
        - Specific and actionable
        - In simple Uzbek or Russian
        - Help us determine exact legal situation
        
        Return JSON:
        {{
          "questions": [
            "Question 1 in user's language",
            "Question 2 in user's language"
          ],
          "reasoning": "Why these questions matter"
        }}
        """
        
        response = llm.generate(prompt)
        return json.loads(response)


class RetrievalAgent:
    """
    RAG System with Verification Layer
    """
    
    def run(self, user_message, intent_analysis):
        """
        Execute RAG pipeline with verification
        """
        # 1. Expand query with legal terms
        expanded_query = self.query_expansion(user_message, intent_analysis['domain'])
        
        # 2. Hybrid retrieval
        retrieved_chunks = self.hybrid_search(expanded_query)
        
        # 3. Re-rank for legal relevance
        reranked = self.rerank(expanded_query, retrieved_chunks)
        
        # 4. Verify retrieved content is actually relevant
        verified_chunks = self.verify_relevance(expanded_query, reranked[:5])
        
        # 5. Generate response
        if len(verified_chunks) == 0:
            return self.handle_no_legal_basis()
        
        response = self.generate_grounded_response(
            user_message, 
            verified_chunks,
            intent_analysis['domain']
        )
        
        return response
    
    def query_expansion(self, query, domain):
        """
        Expand user query with legal terminology
        
        Example:
        "I was fired" → "увольнение, расторжение трудового договора, 
                         незаконное увольнение, Трудовой кодекс"
        """
        prompt = f"""
        User query: {query}
        Legal domain: {domain}
        
        Expand this query with:
        - Legal terms in Russian/Uzbek
        - Relevant code articles
        - Related legal concepts
        
        Return 3-5 search terms that will find the right laws.
        """
        return llm.generate(prompt)
    
    def verify_relevance(self, query, chunks):
        """
        CRITICAL VERIFICATION STEP
        
        Before using retrieved chunks, verify they actually answer the question
        This prevents hallucination
        """
        verified = []
        
        for chunk in chunks:
            prompt = f"""
            Question: {query}
            Legal Text: {chunk['content']}
            
            Does this legal text directly address the question?
            
            Answer ONLY 'yes' or 'no' and explain in ONE sentence.
            
            Format:
            {{
              "relevant": true/false,
              "reason": "one sentence"
            }}
            """
            
            result = llm.generate(prompt)
            verification = json.loads(result)
            
            if verification['relevant']:
                verified.append(chunk)
        
        return verified
    
    def generate_grounded_response(self, query, verified_chunks, domain):
        """
        Generate response that ONLY uses verified legal sources
        """
        
        # Combine all verified legal texts
        legal_context = "\n\n".join([
            f"[{chunk['article_number']}] {chunk['content']}"
            for chunk in verified_chunks
        ])
        
        prompt = f"""
        You are a legal assistant helping Uzbek citizens understand the law.
        
        User Question: {query}
        
        Relevant Laws:
        {legal_context}
        
        RULES:
        1. Answer ONLY based on the laws provided above
        2. Use simple Uzbek or Russian language
        3. Avoid legal jargon - explain like talking to a friend
        4. Include the article number when citing law
        5. If the law doesn't answer the question, say "I cannot find this in the law"
        
        Structure your answer:
        1. Direct answer to the question (2-3 sentences)
        2. Which law applies (mention article number)
        3. What the user should do next (practical steps)
        
        Generate answer in {'Uzbek' if 'uzb' in query else 'Russian'}:
        """
        
        answer = llm.generate(prompt)
        
        # Add citation metadata
        return {
            "answer": answer,
            "sources": [
                {
                    "article": chunk['article_number'],
                    "law": chunk['title'],
                    "text": chunk['content'][:200] + "..."
                }
                for chunk in verified_chunks
            ],
            "confidence": "high" if len(verified_chunks) >= 2 else "medium"
        }
    
    def handle_no_legal_basis(self):
        """
        What to do when we can't find relevant laws
        """
        return {
            "answer": "К сожалению, я не могу найти точный ответ в законодательстве Узбекистана. " +
                      "Рекомендую проконсультироваться с юристом для вашей конкретной ситуации.",
            "sources": [],
            "confidence": "none",
            "recommendation": "consult_lawyer"
        }


class DocumentAnalyzerAgent:
    """
    Analyzes uploaded contracts/documents
    """
    
    def run(self, document):
        """
        Extract risks, obligations, and unfair clauses
        """
        
        # 1. Extract text from document
        document_text = extract_text(document)
        
        # 2. Identify document type
        doc_type = self.classify_document_type(document_text)
        
        # 3. Extract key clauses
        clauses = self.extract_clauses(document_text, doc_type)
        
        # 4. Analyze each clause against legal standards
        analysis = self.analyze_clauses(clauses)
        
        # 5. Generate simplified summary
        summary = self.generate_summary(analysis)
        
        return summary
    
    def analyze_clauses(self, clauses):
        """
        Check each clause for:
        - Fairness (is it balanced?)
        - Hidden fees or penalties
        - Unreasonable obligations
        - Legal compliance
        """
        
        analyzed = []
        
        for clause in clauses:
            prompt = f"""
            Analyze this contract clause:
            
            {clause}
            
            Evaluate:
            1. Is it fair to both parties?
            2. Are there hidden costs or penalties?
            3. Are there unreasonable obligations?
            4. Does it comply with Uzbek law?
            5. Risk level: low, medium, high
            
            Return JSON:
            {{
              "fair": true/false,
              "hidden_costs": "description or null",
              "risks": ["list of risks"],
              "risk_level": "low/medium/high",
              "recommendation": "accept/negotiate/reject",
              "simple_explanation": "In simple words..."
            }}
            """
            
            analysis = llm.generate(prompt)
            analyzed.append({
                "clause": clause,
                "analysis": json.loads(analysis)
            })
        
        return analyzed
```

---

## 💾 DATABASE SCHEMA

```sql
-- PostgreSQL Schema for TahlilchiAI

-- Legal Documents Table
CREATE TABLE legal_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id VARCHAR(255) UNIQUE NOT NULL,
    document_type VARCHAR(50) NOT NULL, -- 'law', 'regulation', 'code'
    law_category VARCHAR(50) NOT NULL, -- 'civil', 'criminal', 'administrative', etc.
    title TEXT NOT NULL,
    article_number VARCHAR(50),
    section VARCHAR(255),
    content TEXT NOT NULL,
    effective_date DATE,
    language VARCHAR(10) NOT NULL, -- 'uz', 'ru'
    keywords TEXT[], -- Array of keywords
    related_articles TEXT[], -- Array of related article IDs
    jurisdiction VARCHAR(50) DEFAULT 'uzbekistan',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for fast retrieval
CREATE INDEX idx_law_category ON legal_documents(law_category);
CREATE INDEX idx_article_number ON legal_documents(article_number);
CREATE INDEX idx_keywords ON legal_documents USING GIN(keywords);

-- Conversations Table
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    started_at TIMESTAMP DEFAULT NOW(),
    last_message_at TIMESTAMP DEFAULT NOW(),
    conversation_state JSONB, -- Store conversation history
    intent_classification VARCHAR(100),
    legal_domain VARCHAR(50),
    resolved BOOLEAN DEFAULT FALSE
);

-- Messages Table
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id),
    role VARCHAR(20) NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    message_type VARCHAR(50), -- 'query', 'clarification', 'answer'
    metadata JSONB, -- Store sources, confidence, etc.
    created_at TIMESTAMP DEFAULT NOW()
);

-- Document Analysis Results
CREATE TABLE document_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    document_name VARCHAR(255),
    document_type VARCHAR(100),
    analysis_result JSONB, -- Store full analysis
    risk_level VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Lawyer Profiles (For Phase 2)
CREATE TABLE lawyers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    specialization TEXT[],
    experience_years INTEGER,
    rating DECIMAL(3,2),
    available_for_booking BOOLEAN DEFAULT TRUE,
    profile_data JSONB
);

-- User Feedback (For improvement)
CREATE TABLE feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id),
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    helpful BOOLEAN,
    feedback_text TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 🚀 MVP IMPLEMENTATION PLAN (4 WEEKS)

### Week 1: Foundation & Data Pipeline

**Full-Stack Lead & Backend Dev:**
- [ ] Setup project repository (GitHub)
- [ ] Initialize FastAPI backend
- [ ] Setup PostgreSQL database
- [ ] Implement document ingestion pipeline
- [ ] Create database schema
- [ ] Setup environment (Docker containers)

**NLP/ML Engineer:**
- [ ] Research and select embedding model
- [ ] Setup vector database (Qdrant/Pinecone)
- [ ] Implement chunking logic for legal documents
- [ ] Create embedding generation pipeline
- [ ] Index sample legal documents (5-10 laws)

**Frontend Dev:**
- [ ] Setup React/Streamlit project
- [ ] Design mockups for chat interface
- [ ] Implement basic UI components
- [ ] Setup routing and state management

**Product Manager:**
- [ ] Finalize demo script
- [ ] Prepare sample legal documents
- [ ] Create test queries for each legal domain
- [ ] Draft pitch presentation outline

**Deliverables:**
- ✅ Working database with 5-10 laws indexed
- ✅ Basic API endpoints for document retrieval
- ✅ UI mockups approved

---

### Week 2: RAG System Core

**NLP/ML Engineer (PRIORITY):**
- [ ] Implement hybrid search (vector + BM25)
- [ ] Build re-ranking system
- [ ] Create query expansion logic
- [ ] Test retrieval accuracy on 50 queries
- [ ] Implement relevance verification

**Backend Dev:**
- [ ] Build RAG API endpoints
- [ ] Implement caching layer
- [ ] Create conversation state management
- [ ] Add error handling and logging

**Full-Stack Lead:**
- [ ] Integrate LLM API (GPT-4o/Claude)
- [ ] Build orchestrator agent logic
- [ ] Implement intent classification
- [ ] Create response generation pipeline

**Frontend Dev:**
- [ ] Build chat interface
- [ ] Implement message streaming
- [ ] Add loading states
- [ ] Create source citation display

**Deliverables:**
- ✅ Working RAG retrieval with >70% accuracy
- ✅ Functional chat interface
- ✅ Intent classification working

---

### Week 3: Multi-Agent Intelligence

**Full-Stack Lead & NLP Engineer (PAIR PROGRAMMING):**
- [ ] Implement Clarifier Agent
- [ ] Build follow-up question generation
- [ ] Create domain-specific question templates
- [ ] Implement conversation memory
- [ ] Add context tracking

**Backend Dev:**
- [ ] Build document upload & analysis API
- [ ] Implement document parsing (PDF, DOCX)
- [ ] Create clause extraction logic
- [ ] Add risk analysis workflow

**Frontend Dev:**
- [ ] Design document upload interface
- [ ] Build analysis results display
- [ ] Add interactive clarification flow
- [ ] Implement source highlighting

**Product Manager & QA:**
- [ ] Test 100+ queries across all domains
- [ ] Document bugs and edge cases
- [ ] Prepare demo scenarios
- [ ] Create judge presentation slides

**Deliverables:**
- ✅ Clarifier Agent fully functional
- ✅ Document analyzer working
- ✅ Demo-ready system

---

### Week 4: Polish, Testing & Presentation

**Everyone:**
- [ ] Bug fixing sprint
- [ ] Performance optimization
- [ ] Add Uzbek language support
- [ ] Test on slow connections
- [ ] Prepare fallback responses

**Frontend Dev:**
- [ ] UI polish and animations
- [ ] Mobile responsiveness
- [ ] Add feedback mechanism
- [ ] Error state improvements

**Product Manager:**
- [ ] Finalize pitch deck
- [ ] Rehearse demo (3x minimum)
- [ ] Prepare technical Q&A answers
- [ ] Create backup demo video

**NLP Engineer:**
- [ ] Tune retrieval thresholds
- [ ] Add more legal documents
- [ ] Optimize response time
- [ ] Document technical approach

**Deliverables:**
- ✅ Polished demo-ready product
- ✅ Pitch presentation ready
- ✅ Technical documentation
- ✅ Backup demo video

---

## 🎨 FRONTEND IMPLEMENTATION

### Technology Stack

**Recommended: Streamlit (MVP Speed) or React (Production Quality)**

```python
# STREAMLIT VERSION (Fastest to build)

import streamlit as st
import requests

st.set_page_config(
    page_title="TahlilchiAI",
    page_icon="⚖️",
    layout="wide"
)

# Session state for conversation
if 'messages' not in st.session_state:
    st.session_state.messages = []

# UI
st.title("⚖️ TahlilchiAI - Ваш юридический помощник")

# Chat interface
for msg in st.session_state.messages:
    with st.chat_message(msg['role']):
        st.write(msg['content'])
        
        # Show sources if available
        if 'sources' in msg and msg['sources']:
            with st.expander("📚 Правовая основа"):
                for source in msg['sources']:
                    st.caption(f"**{source['article']}** - {source['law']}")
                    st.text(source['text'])

# User input
if prompt := st.chat_input("Опишите вашу ситуацию..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Call API
    with st.spinner("Анализирую законодательство..."):
        response = requests.post(
            "http://localhost:8000/api/chat",
            json={
                "message": prompt,
                "conversation_history": st.session_state.messages
            }
        )
        
        result = response.json()
    
    # Add assistant response
    st.session_state.messages.append({
        "role": "assistant",
        "content": result['answer'],
        "sources": result.get('sources', [])
    })
    
    st.rerun()

# Sidebar - Document Upload
with st.sidebar:
    st.header("📄 Анализ документа")
    uploaded_file = st.file_uploader("Загрузите договор", type=['pdf', 'docx'])
    
    if uploaded_file:
        if st.button("Проанализировать"):
            with st.spinner("Анализирую документ..."):
                files = {"file": uploaded_file}
                response = requests.post(
                    "http://localhost:8000/api/analyze-document",
                    files=files
                )
                
                analysis = response.json()
                st.json(analysis)
```

---

## 🔧 BACKEND API IMPLEMENTATION

```python
# FastAPI Backend Structure

from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
import uuid

app = FastAPI(title="TahlilchiAI API")

# Models
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    conversation_history: List[Message]
    language: str = "ru"

class ChatResponse(BaseModel):
    answer: str
    sources: List[dict]
    confidence: str
    next_action: Optional[str] = None

class ClarificationResponse(BaseModel):
    questions: List[str]
    reasoning: str

# Main Chat Endpoint
@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint - routes to orchestrator
    """
    
    # 1. Initialize orchestrator
    orchestrator = OrchestratorAgent()
    
    # 2. Classify intent
    intent = orchestrator.classify_intent(request.message)
    
    # 3. Route to appropriate agent
    if intent['clarity'] == 'needs_clarification':
        # Return clarification questions
        clarifier = ClarifierAgent()
        questions = clarifier.run(request.message, intent)
        
        return ChatResponse(
            answer="Чтобы помочь вам лучше, мне нужна дополнительная информация:",
            sources=[],
            confidence="pending",
            next_action="clarification",
            clarification_questions=questions['questions']
        )
    
    elif intent['intent'] == 'legal_query':
        # Execute RAG pipeline
        retrieval = RetrievalAgent()
        result = retrieval.run(request.message, intent)
        
        return ChatResponse(
            answer=result['answer'],
            sources=result['sources'],
            confidence=result['confidence']
        )
    
    elif intent['intent'] == 'lawyer_needed':
        return ChatResponse(
            answer="Ваша ситуация требует консультации специалиста. " + 
                   "Я могу помочь найти подходящего юриста.",
            sources=[],
            confidence="high",
            next_action="lawyer_matching"
        )

# Document Analysis Endpoint
@app.post("/api/analyze-document")
async def analyze_document(file: UploadFile = File(...)):
    """
    Analyze uploaded legal document
    """
    
    # 1. Save file temporarily
    file_path = f"/tmp/{uuid.uuid4()}_{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())
    
    # 2. Analyze
    analyzer = DocumentAnalyzerAgent()
    analysis = analyzer.run(file_path)
    
    # 3. Clean up
    os.remove(file_path)
    
    return analysis

# Retrieval Test Endpoint (for demo)
@app.post("/api/search")
async def search_legal_corpus(query: str):
    """
    Test RAG retrieval
    """
    retrieval = RetrievalAgent()
    results = retrieval.hybrid_search(query)
    
    return {"results": results}

# Health check
@app.get("/health")
async def health():
    return {"status": "healthy"}
```

---

## 📊 EVALUATION & METRICS

### Key Metrics to Track

```python
# RETRIEVAL QUALITY METRICS

1. Retrieval Accuracy:
   - MRR (Mean Reciprocal Rank): >0.7
   - Precision@5: >0.8
   - Recall@10: >0.6

2. Response Quality:
   - Answer Relevance: >0.85
   - Faithfulness (grounded in sources): >0.9
   - Hallucination Rate: <5%

3. User Experience:
   - Response Time: <3 seconds
   - Clarification Rate: 20-30% (shows intelligent questioning)
   - User Satisfaction: >4/5

# EVALUATION SCRIPT
def evaluate_rag_system(test_queries, ground_truth):
    """
    Test RAG system against ground truth
    """
    
    results = {
        'correct_law_retrieved': 0,
        'answer_accurate': 0,
        'no_hallucinations': 0,
        'total': len(test_queries)
    }
    
    for query, expected in zip(test_queries, ground_truth):
        # Get response
        response = retrieval_agent.run(query, {})
        
        # Check if correct law retrieved
        retrieved_articles = [s['article'] for s in response['sources']]
        if expected['article'] in retrieved_articles:
            results['correct_law_retrieved'] += 1
        
        # Check answer accuracy (manual or LLM judge)
        if is_accurate(response['answer'], expected['answer']):
            results['answer_accurate'] += 1
        
        # Check for hallucinations
        if no_hallucinations(response['answer'], response['sources']):
            results['no_hallucinations'] += 1
    
    # Calculate metrics
    precision = results['correct_law_retrieved'] / results['total']
    accuracy = results['answer_accurate'] / results['total']
    faithfulness = results['no_hallucinations'] / results['total']
    
    return {
        'precision': precision,
        'accuracy': accuracy,
        'faithfulness': faithfulness
    }
```

---

## 🎤 HACKATHON PRESENTATION STRATEGY

### Demo Script (7-10 minutes)

**Act 1: The Problem (1 min)**
- Show confusing legal document
- "Ordinary citizens don't understand their rights"
- "No one to ask, lawyers are expensive"

**Act 2: The Solution - Chat Assistant (4 min)**

**Scenario 1: Simple Query**
```
User: "Я получил штраф за парковку. Это законно?"
(I got a parking fine. Is this legal?)

[Show orchestrator classifying intent → administrative law]

TahlilchiAI: "Да, штрафы за нарушение правил парковки предусмотрены 
Административным кодексом. Согласно статье 128..."

[Show source citation appearing]
```

**Scenario 2: Intelligent Clarification (THE WOW MOMENT)**
```
User: "Меня уволили с работы"
(I was fired from my job)

[Show clarifier agent activating]

TahlilchiAI: "Чтобы помочь вам, мне нужна информация:
1. Сколько вы работали в компании?
2. Какова причина увольнения?
3. Есть ли у вас трудовой договор?"

[Show judge's reaction - "This is not a simple chatbot!"]

User: "2 года, сказали сокращение штата, договор есть"

TahlilchiAI: "По Трудовому кодексу, при сокращении работодатель 
обязан уведомить вас за 2 месяца и выплатить выходное пособие..."

[Show RAG retrieving exact articles]
```

**Act 3: Document Analysis (2 min)**
```
[Upload sample contract]

TahlilchiAI: 
"⚠️ Обнаружены риски:
1. Высокий штраф за досрочное расторжение (15% - превышает норму)
2. Скрытая комиссия за обслуживание
3. Неограниченное право изменения условий банком

Рекомендация: Попросите пересмотреть пункты 7.2 и 9.4"

[Show risk highlighting in document]
```

**Act 4: Technical Depth (2 min)**
```
[Show architecture diagram]

"Behind the scenes:
- Advanced RAG with hybrid retrieval
- Multi-agent orchestration
- Cross-encoder re-ranking
- Zero-hallucination verification
- All answers grounded in official legal sources"

[Show metrics: 85% retrieval accuracy, <2% hallucination rate]
```

**Closing:**
"TahlilchiAI - первый шаг к справедливому доступу к правовой информации в Узбекистане"

---

## 🛠️ DEPLOYMENT (Post-Hackathon)

### Cloud Infrastructure

```yaml
# Docker Compose Setup

version: '3.8'

services:
  # FastAPI Backend
  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/tahlilchi
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - QDRANT_URL=http://qdrant:6333
    depends_on:
      - db
      - qdrant

  # PostgreSQL
  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=tahlilchi

  # Qdrant Vector DB
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

  # Streamlit Frontend
  frontend:
    build: ./frontend
    ports:
      - "8501:8501"
    depends_on:
      - api

volumes:
  postgres_data:
  qdrant_data:
```

### Cost Optimization

```python
# PRODUCTION COST REDUCTION STRATEGIES

1. Caching Layer:
   - Cache common queries (Redis)
   - Save 60-70% on LLM costs
   
2. Smaller Model for Classification:
   - Use GPT-3.5 for intent classification
   - Use GPT-4o only for final answers
   - Saves 90% on classification costs

3. Batch Processing:
   - Process document ingestion overnight
   - Reduce API rate limit costs

4. Open-Source LLM Option:
   - Deploy Llama 3.1 70B on GPU server
   - $500/month GPU vs $2000/month API calls
   - Break-even at ~100k queries/month
```

---

## 📚 TECHNICAL DOCUMENTATION FOR JUDGES

### Architecture Highlights

**1. Advanced RAG Pipeline**
- Hybrid search (semantic + keyword)
- Cross-encoder re-ranking
- Multi-source verification
- Prevents hallucinations through forced grounding

**2. Multi-Agent Intelligence**
- Orchestrator for routing
- Clarifier for intelligent questioning
- Verifier for accuracy checking
- Not a simple chatbot - true reasoning system

**3. Legal-Grade Accuracy**
- Every answer cites official sources
- Relevance verification before responding
- Confidence scoring
- Fallback to lawyer recommendation when uncertain

**4. Scalable Architecture**
- Microservices design
- Horizontal scaling ready
- Caching layer for performance
- Database optimized for legal queries

---

## 🔒 SECURITY & PRIVACY

### Data Protection

```python
# SECURITY MEASURES

1. User Data:
   - Conversations not stored permanently (optional)
   - Document analysis temporary (deleted after 24h)
   - No PII collected without consent

2. API Security:
   - Rate limiting
   - API key authentication
   - HTTPS only
   - Input sanitization

3. Legal Corpus:
   - Version control for laws
   - Audit trail for changes
   - Source verification
   
4. Compliance:
   - GDPR-compliant (if needed)
   - Local data storage option
   - Transparent data usage
```

---

## 🎯 SUCCESS CRITERIA

### MVP Success Metrics

**Technical:**
- ✅ Retrieval accuracy >70%
- ✅ Response time <3 seconds
- ✅ Hallucination rate <5%
- ✅ System uptime >95% during demo

**User Experience:**
- ✅ 10 successful demo scenarios prepared
- ✅ Clarification works for ambiguous queries
- ✅ Simple language verified by non-lawyers
- ✅ Mobile-responsive design

**Hackathon Goals:**
- ✅ Judges say "This is technically impressive"
- ✅ Users say "I actually understand this"
- ✅ Winning pitch presentation
- ✅ Working product, not just slides

---

## 📝 NOVELTY POINTS FOR JUDGES

### What Makes This Special

1. **Not Just RAG - It's Intelligent**
   - Most legal chatbots just do search
   - Ours asks clarifying questions like a real lawyer
   
2. **Zero-Hallucination Architecture**
   - Forced grounding in official sources
   - Verification layer prevents made-up answers
   - Shows citations for transparency

3. **Uzbek-First Design**
   - Built for local language and laws
   - Not a translated foreign product
   - Addresses real local needs

4. **Multi-Agent System**
   - Orchestrator, clarifier, retriever, verifier
   - Shows sophisticated AI reasoning
   - Not a monolithic prompt

5. **Production-Ready Architecture**
   - Scalable microservices
   - Database optimized for legal data
   - Can handle real users post-hackathon

---

## 🚨 RISK MITIGATION

### Common Pitfalls & Solutions

**Problem: LLM Hallucinations**
- ✅ Solution: Verification layer + forced grounding

**Problem: Slow Retrieval**
- ✅ Solution: Caching + optimized indexing

**Problem: Poor Uzbek Support**
- ✅ Solution: Use multilingual LLMs (GPT-4o/Claude)

**Problem: Demo Fails During Presentation**
- ✅ Solution: Backup video + offline mode

**Problem: Can't Find Relevant Law**
- ✅ Solution: Graceful fallback to lawyer recommendation

---

## 🎓 LEARNING RESOURCES

### For Team Members

**RAG Systems:**
- LangChain RAG Tutorial
- Pinecone RAG Guide
- "Building RAG from Scratch" (YouTube)

**Legal NLP:**
- Legal-BERT paper
- Harvey AI case studies
- TrueLaw blog

**Multi-Agent Systems:**
- LangGraph documentation
- CrewAI examples
- AutoGen framework

**Vector Databases:**
- Qdrant quickstart
- Pinecone Academy
- Weaviate tutorials

---

## 📞 NEXT STEPS

### Immediate Actions (Day 1)

1. **Tech Lead:**
   - [ ] Create GitHub repo
   - [ ] Setup development environment
   - [ ] Choose LLM provider (GPT-4o recommended)

2. **NLP Engineer:**
   - [ ] Download 5-10 Uzbek legal documents
   - [ ] Test embedding models
   - [ ] Setup vector DB

3. **Frontend:**
   - [ ] Design chat UI mockup
   - [ ] Choose framework (Streamlit vs React)

4. **Everyone:**
   - [ ] Read this document fully
   - [ ] Schedule daily standups
   - [ ] Commit to timeline

---

## 💡 FINAL THOUGHTS

### Keys to Success

1. **Focus on Chat Intelligence**
   - This is your differentiator
   - Make it work REALLY well
   - Show off the multi-agent magic

2. **Keep It Simple**
   - MVP = Core chat + basic document analysis
   - Don't build features judges won't see
   - Polish what you demo

3. **Test Relentlessly**
   - 100+ queries minimum
   - Find edge cases
   - Fix before demo day

4. **Tell a Story**
   - Not just features
   - Show how it helps real people
   - Make judges care

**You have everything you need to win. Now go build it! 🚀**

---

## APPENDIX A: Sample Legal Documents Structure

```
legal_corpus/
├── civil_code/
│   ├── section_1_general_provisions.txt
│   ├── section_2_contracts.txt
│   └── section_3_obligations.txt
├── criminal_code/
│   ├── general_part.txt
│   └── special_part.txt
├── administrative_code/
│   ├── traffic_violations.txt
│   └── fines_procedures.txt
└── labor_code/
    ├── employment_contracts.txt
    └── termination.txt
```

## APPENDIX B: Test Queries Database

```python
TEST_QUERIES = [
    {
        "query": "Меня оштрафовали за парковку. Законно ли это?",
        "domain": "administrative",
        "expected_article": "128",
        "difficulty": "easy"
    },
    {
        "query": "Работодатель уволил меня без причины",
        "domain": "labor",
        "expected_article": "101",
        "needs_clarification": True,
        "difficulty": "medium"
    },
    {
        "query": "Банк изменил процентную ставку без моего согласия",
        "domain": "civil",
        "expected_article": "365",
        "difficulty": "hard"
    }
    # Add 100+ more...
]
```

---

**VERSION: 1.0**  
**LAST UPDATED: November 14, 2025**  
**AUTHOR: TahlilchiAI Development Team**

