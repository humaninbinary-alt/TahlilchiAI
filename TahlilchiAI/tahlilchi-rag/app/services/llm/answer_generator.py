"""Main answer generation service."""

import logging
import re
from typing import Any, AsyncGenerator, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import LLMError, NoRelevantContextError
from app.models.chat import Chat
from app.schemas.retrieval import RetrievedContext
from app.services.llm.ollama_client import OllamaClient
from app.services.llm.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


class AnswerGenerator:
    """
    Main service for generating grounded answers.

    Pipeline:
    1. Load chat configuration
    2. Build system and user prompts
    3. Call LLM
    4. Extract and format citations
    5. Return structured answer
    """

    def __init__(
        self,
        db: AsyncSession,
        llm_client: OllamaClient,
        prompt_builder: PromptBuilder,
    ) -> None:
        """
        Initialize answer generator.

        Args:
            db: Database session
            llm_client: LLM client instance
            prompt_builder: Prompt builder instance
        """
        self.db = db
        self.llm_client = llm_client
        self.prompt_builder = prompt_builder
        self.logger = logger

    async def generate_answer(
        self,
        query: str,
        contexts: List[RetrievedContext],
        chat_id: UUID,
        tenant_id: UUID,
    ) -> Dict[str, Any]:
        """
        Generate grounded answer from contexts.

        Args:
            query: User's question
            contexts: Retrieved context chunks
            chat_id: Chat UUID
            tenant_id: Tenant UUID

        Returns:
            Dict with:
            - answer: str (generated answer)
            - citations: List[dict] (sources used)
            - contexts_used: int (number of contexts used)
            - confidence: str (high/medium/low)

        Raises:
            NoRelevantContextError: If no contexts and strict mode
            LLMError: If generation fails
        """
        try:
            self.logger.info(f"Generating answer for query: '{query}'")

            # 1. Load chat configuration
            chat_config = await self._load_chat_config(chat_id, tenant_id)

            # 2. Check if we have contexts (for strict mode)
            if not contexts:
                if chat_config["strictness"] == "strict_docs_only":
                    raise NoRelevantContextError(
                        "No relevant information found in documents"
                    )
                else:
                    self.logger.warning("No contexts found, using general knowledge")

            # 3. Truncate contexts if needed
            contexts = self.prompt_builder.truncate_contexts(contexts)

            # 4. Build prompts
            system_prompt = self.prompt_builder.build_system_prompt(chat_config)
            user_prompt = self.prompt_builder.build_user_prompt(query, contexts)

            self.logger.info(
                f"Generated prompts: system={len(system_prompt)} chars, "
                f"user={len(user_prompt)} chars"
            )

            # 5. Generate answer
            answer_text = await self.llm_client.generate(
                prompt=user_prompt, system_prompt=system_prompt
            )

            # 6. Extract citations from answer
            citations = self._extract_citations(answer_text, contexts)

            # 7. Determine confidence
            confidence = self._determine_confidence(contexts, answer_text)

            result = {
                "answer": answer_text,
                "citations": citations,
                "contexts_used": len(contexts),
                "confidence": confidence,
                "chat_config": {
                    "purpose": chat_config["purpose"],
                    "tone": chat_config["tone"],
                    "strictness": chat_config["strictness"],
                },
            }

            self.logger.info(
                f"Answer generated: {len(answer_text)} chars, "
                f"{len(citations)} citations, "
                f"confidence: {confidence}"
            )

            return result

        except NoRelevantContextError:
            raise
        except Exception as e:
            self.logger.error(f"Answer generation failed: {e}")
            raise LLMError(f"Failed to generate answer: {e}")

    async def generate_answer_with_context(
        self,
        query: str,
        contexts: List[RetrievedContext],
        chat_id: UUID,
        tenant_id: UUID,
        conversation_context: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate answer with conversation context for multi-turn chat.

        Args:
            query: Current user question
            contexts: Retrieved document contexts
            chat_id: Chat UUID
            tenant_id: Tenant UUID
            conversation_context: Previous messages [{"role": "user", "content": "..."}, ...]

        Returns:
            Same as generate_answer()

        Raises:
            NoRelevantContextError: If no contexts and strict mode
            LLMError: If generation fails
        """
        try:
            self.logger.info("Generating answer with conversation context")

            # Load chat configuration
            chat_config = await self._load_chat_config(chat_id, tenant_id)

            # Check contexts
            if not contexts:
                if chat_config["strictness"] == "strict_docs_only":
                    raise NoRelevantContextError(
                        "No relevant information found in documents"
                    )

            # Truncate contexts
            contexts = self.prompt_builder.truncate_contexts(contexts)

            # Build system prompt
            system_prompt = self.prompt_builder.build_system_prompt(chat_config)

            # Build user prompt with conversation context
            user_prompt = self._build_contextual_prompt(
                query=query,
                contexts=contexts,
                conversation_context=conversation_context,
            )

            # Generate answer
            answer_text = await self.llm_client.generate(
                prompt=user_prompt, system_prompt=system_prompt
            )

            # Extract citations
            citations = self._extract_citations(answer_text, contexts)

            # Determine confidence
            confidence = self._determine_confidence(contexts, answer_text)

            return {
                "answer": answer_text,
                "citations": citations,
                "contexts_used": len(contexts),
                "confidence": confidence,
                "chat_config": {
                    "purpose": chat_config["purpose"],
                    "tone": chat_config["tone"],
                    "strictness": chat_config["strictness"],
                },
            }

        except NoRelevantContextError:
            raise
        except Exception as e:
            self.logger.error(f"Answer generation with context failed: {e}")
            raise LLMError(f"Failed to generate answer: {e}")

    def _build_contextual_prompt(
        self,
        query: str,
        contexts: List[RetrievedContext],
        conversation_context: Optional[List[Dict[str, str]]],
    ) -> str:
        """
        Build prompt with conversation history.

        Args:
            query: Current user question
            contexts: Retrieved document contexts
            conversation_context: Previous messages

        Returns:
            Formatted prompt string
        """
        prompt = ""

        # Add conversation history if provided
        if conversation_context:
            prompt += "CONVERSATION HISTORY:\n\n"
            for msg in conversation_context[-4:]:  # Last 2 exchanges
                role_label = "User" if msg["role"] == "user" else "Assistant"
                prompt += f"{role_label}: {msg['content']}\n\n"
            prompt += "---\n\n"

        # Add document contexts
        prompt += "CONTEXT DOCUMENTS:\n\n"
        for i, ctx in enumerate(contexts, start=1):
            doc_name = f"Document {ctx.document_id[:8]}"
            page_info = f", Page {ctx.page_number}" if ctx.page_number else ""
            prompt += f"[Context {i}]\n"
            prompt += f"Source: {doc_name}{page_info}\n"
            prompt += f"Content: {ctx.text}\n"
            prompt += "---\n\n"

        # Add current question
        prompt += f"CURRENT QUESTION: {query}\n\n"
        prompt += "ANSWER (with citations):"

        return prompt

    async def generate_answer_stream(
        self,
        query: str,
        contexts: List[RetrievedContext],
        chat_id: UUID,
        tenant_id: UUID,
        conversation_context: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate answer with streaming for real-time token delivery.

        Yields:
            1. Metadata event with retrieval info
            2. Token events with generated text
            3. Done event with citations and confidence

        Args:
            query: Current user question
            contexts: Retrieved document contexts
            chat_id: Chat UUID
            tenant_id: Tenant UUID
            conversation_context: Previous messages for multi-turn

        Yields:
            Dict events in SSE format

        Raises:
            NoRelevantContextError: If no contexts and strict mode
            LLMError: If generation fails
        """
        try:
            self.logger.info("Starting streaming answer generation")

            # Load chat configuration
            chat_config = await self._load_chat_config(chat_id, tenant_id)

            # Check contexts
            if not contexts:
                if chat_config["strictness"] == "strict_docs_only":
                    raise NoRelevantContextError(
                        "No relevant information found in documents"
                    )

            # Truncate contexts
            contexts = self.prompt_builder.truncate_contexts(contexts)

            # Yield metadata first
            yield {
                "type": "metadata",
                "retrieval_mode": "hybrid",  # Will be passed from caller
                "contexts_used": len(contexts),
                "chat_config": {
                    "purpose": chat_config["purpose"],
                    "tone": chat_config["tone"],
                    "strictness": chat_config["strictness"],
                },
            }

            # Build prompts
            system_prompt = self.prompt_builder.build_system_prompt(chat_config)

            if conversation_context:
                user_prompt = self._build_contextual_prompt(
                    query=query,
                    contexts=contexts,
                    conversation_context=conversation_context,
                )
            else:
                user_prompt = self.prompt_builder.build_user_prompt(query, contexts)

            # Stream tokens from LLM
            full_answer = ""
            async for token in self.llm_client.generate_stream(
                prompt=user_prompt, system_prompt=system_prompt
            ):
                full_answer += token
                yield {"type": "token", "content": token}

            # Extract citations from complete answer
            citations = self._extract_citations(full_answer, contexts)

            # Determine confidence
            confidence = self._determine_confidence(contexts, full_answer)

            # Yield done event with final metadata
            yield {
                "type": "done",
                "citations": citations,
                "confidence": confidence,
                "total_tokens": len(full_answer.split()),
            }

            self.logger.info("Streaming completed successfully")

        except NoRelevantContextError:
            raise
        except Exception as e:
            self.logger.error(f"Streaming generation failed: {e}")
            raise LLMError(f"Failed to generate streaming answer: {e}")

    async def _load_chat_config(self, chat_id: UUID, tenant_id: UUID) -> Dict[str, Any]:
        """Load chat configuration from database."""
        try:
            query = select(Chat).where(Chat.id == chat_id, Chat.tenant_id == tenant_id)
            result = await self.db.execute(query)
            chat = result.scalar_one_or_none()

            if not chat:
                raise ValueError(f"Chat {chat_id} not found")
        except Exception as e:
            # If the transaction is in a bad state, rollback and retry
            if "InFailedSqlTransaction" in str(e):
                await self.db.rollback()
                # Retry the query after rollback
                query = select(Chat).where(
                    Chat.id == chat_id, Chat.tenant_id == tenant_id
                )
                result = await self.db.execute(query)
                chat = result.scalar_one_or_none()

                if not chat:
                    raise ValueError(f"Chat {chat_id} not found")
            else:
                raise

        return {
            "purpose": chat.purpose,
            "tone": chat.tone,
            "strictness": chat.strictness,
            "document_types": chat.document_types,
            "document_languages": chat.document_languages,
        }

    def _extract_citations(
        self, answer: str, contexts: List[RetrievedContext]
    ) -> List[Dict[str, Any]]:
        """
        Extract citation references from answer.

        Looks for patterns like:
        - [Doc: filename, Page: 5]
        - [Context 1]
        - [Source: filename]
        """
        citations = []
        seen_docs = set()

        # Pattern 1: [Doc: ..., Page: ...]
        doc_pattern = r"\[Doc:\s*([^,]+),\s*Page:\s*(\d+)\]"
        matches = re.finditer(doc_pattern, answer)

        for match in matches:
            doc_name = match.group(1).strip()
            page = int(match.group(2))

            key = f"{doc_name}:{page}"
            if key not in seen_docs:
                citations.append(
                    {
                        "type": "document",
                        "document": doc_name,
                        "page": page,
                        "text": match.group(0),
                    }
                )
                seen_docs.add(key)

        # Pattern 2: [Context N]
        context_pattern = r"\[Context\s+(\d+)\]"
        matches = re.finditer(context_pattern, answer)

        for match in matches:
            ctx_num = int(match.group(1))
            if 1 <= ctx_num <= len(contexts):
                ctx = contexts[ctx_num - 1]

                key = f"{ctx.document_id}:{ctx.sequence}"
                if key not in seen_docs:
                    citations.append(
                        {
                            "type": "context",
                            "context_number": ctx_num,
                            "document_id": ctx.document_id,
                            "page": ctx.page_number,
                            "section": ctx.section_title,
                        }
                    )
                    seen_docs.add(key)

        return citations

    def _determine_confidence(
        self, contexts: List[RetrievedContext], answer: str
    ) -> str:
        """
        Determine confidence level based on contexts and answer.

        Returns: "high", "medium", or "low"
        """
        if not contexts:
            return "low"

        # High confidence: multiple high-scoring contexts
        high_score_contexts = [c for c in contexts if c.score > 0.7]
        if len(high_score_contexts) >= 3:
            return "high"

        # Medium confidence: some relevant contexts
        medium_score_contexts = [c for c in contexts if c.score > 0.4]
        if len(medium_score_contexts) >= 2:
            return "medium"

        # Low confidence: weak contexts
        return "low"
