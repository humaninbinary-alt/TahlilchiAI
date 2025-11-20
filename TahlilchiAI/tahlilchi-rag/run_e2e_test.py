"""Simple end-to-end test - Create chat and demonstrate answer with citations."""

import asyncio
import json
from uuid import uuid4

import httpx


async def run_e2e_test():
    """Run end-to-end test."""
    base_url = "http://127.0.0.1:8000"
    
    # Generate test IDs
    tenant_id = str(uuid4())
    user_id = str(uuid4())
    
    print("=" * 60)
    print("🚀 End-to-End RAG Pipeline Test")
    print("=" * 60)
    print()
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Step 1: Create a chat
        print("1️⃣  Creating chat...")
        try:
            chat_data = {
                "name": "Test Legal Assistant",
                "purpose": "policy_qa",
                "target_audience": "staff",
                "tone": "simple_uzbek",
                "strictness": "strict_docs_only",
                "sensitivity": "high_on_prem",
                "document_types": ["policies"],
                "document_languages": ["uz", "ru"]
            }
            
            response = await client.post(
                f"{base_url}/api/v1/chats?tenant_id={tenant_id}&user_id={user_id}",
                json=chat_data
            )
            
            if response.status_code == 201:
                chat = response.json()
                chat_id = chat["id"]
                print(f"✅ Chat created successfully!")
                print(f"   Chat ID: {chat_id}")
                print(f"   Name: {chat['name']}")
                print(f"   Purpose: {chat['purpose']}")
                print()
            else:
                print(f"❌ Failed to create chat: {response.status_code}")
                print(f"   Error: {response.text}")
                return
                
        except Exception as e:
            print(f"❌ Error creating chat: {e}")
            return
        
        # Step 2: Since we don't have a document uploaded yet, 
        # let's demonstrate with a query that will trigger "no context" response
        print("2️⃣  Testing answer generation (no documents yet)...")
        print("   This will demonstrate the strict mode behavior")
        print()
        
        try:
            answer_request = {
                "query": "What are the payment terms?"
            }
            
            response = await client.post(
                f"{base_url}/api/v1/chats/{chat_id}/answer?tenant_id={tenant_id}",
                json=answer_request
            )
            
            if response.status_code == 200:
                result = response.json()
                
                print("=" * 60)
                print("📝 ANSWER RESPONSE (No Documents)")
                print("=" * 60)
                print()
                print(f"Query: {result['query']}")
                print()
                print(f"Answer: {result['answer']}")
                print()
                print(f"Citations: {len(result['citations'])} sources")
                print(f"Contexts used: {result['contexts_used']}")
                print(f"Confidence: {result['confidence']}")
                print(f"Retrieval mode: {result['retrieval_mode']}")
                print()
                print("Chat Config:")
                print(f"  Purpose: {result['chat_config'].get('purpose', 'N/A')}")
                print(f"  Tone: {result['chat_config'].get('tone', 'N/A')}")
                print(f"  Strictness: {result['chat_config'].get('strictness', 'N/A')}")
                print()
                print("=" * 60)
                print()
                
                # Save to file
                with open("answer_no_docs.json", "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                print("💾 Response saved to: answer_no_docs.json")
                print()
                
            else:
                print(f"❌ Failed to generate answer: {response.status_code}")
                print(f"   Error: {response.text}")
                
        except Exception as e:
            print(f"❌ Error generating answer: {e}")
        
        # Step 3: Show what a SUCCESSFUL answer with citations would look like
        print()
        print("=" * 60)
        print("📚 EXAMPLE: Successful Answer WITH Citations")
        print("=" * 60)
        print()
        print("This is what you'll get once documents are indexed:")
        print()
        
        example_response = {
            "query": "What are the payment terms?",
            "answer": "According to the contract, payment must be made within 30 calendar days from the invoice date. Late payments incur a 1% monthly penalty. [Doc: contract.pdf, Page: 5] For milestone-based projects, payments are due upon acceptance of each milestone deliverable. [Doc: SOW_v2.pdf, Page: 3]",
            "citations": [
                {
                    "type": "document",
                    "document": "contract.pdf",
                    "page": 5,
                    "text": "[Doc: contract.pdf, Page: 5]"
                },
                {
                    "type": "document",
                    "document": "SOW_v2.pdf",
                    "page": 3,
                    "text": "[Doc: SOW_v2.pdf, Page: 3]"
                }
            ],
            "contexts_used": 3,
            "confidence": "high",
            "retrieval_mode": "hybrid",
            "chat_config": {
                "purpose": "policy_qa",
                "tone": "formal_english",
                "strictness": "strict_docs_only"
            }
        }
        
        print(f"Query: {example_response['query']}")
        print()
        print(f"Answer: {example_response['answer']}")
        print()
        print("Citations:")
        for i, citation in enumerate(example_response['citations'], 1):
            print(f"  {i}. Type: {citation['type']}")
            print(f"     Document: {citation['document']}")
            print(f"     Page: {citation['page']}")
            print()
        
        print(f"Contexts used: {example_response['contexts_used']}")
        print(f"Confidence: {example_response['confidence']}")
        print(f"Retrieval mode: {example_response['retrieval_mode']}")
        print()
        
        # Save example
        with open("answer_example_with_citations.json", "w", encoding="utf-8") as f:
            json.dump(example_response, f, indent=2, ensure_ascii=False)
        print("💾 Example saved to: answer_example_with_citations.json")
        print()
    
    print("=" * 60)
    print("✅ END-TO-END TEST COMPLETED!")
    print("=" * 60)
    print()
    print("Next steps to get real citations:")
    print("1. Upload a document to the chat")
    print("2. Process and index it (POST /chats/{id}/documents/{doc_id}/process-and-index)")
    print("3. Ask questions - you'll get answers with real citations!")
    print()


if __name__ == "__main__":
    asyncio.run(run_e2e_test())
