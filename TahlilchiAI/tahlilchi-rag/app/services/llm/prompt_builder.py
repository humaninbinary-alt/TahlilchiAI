"""Prompt templates and builders for LLM."""

import logging
from typing import Any, Dict, List

from app.schemas.retrieval import RetrievedContext

logger = logging.getLogger(__name__)


class PromptBuilder:
    """
    Builds prompts for LLM based on chat configuration.

    Handles:
    - System prompt generation
    - Context formatting with citations
    - Tone/language adaptation
    - Strictness enforcement
    """

    def __init__(self) -> None:
        """Initialize the prompt builder."""
        self.logger = logger

    def build_system_prompt(self, chat_config: Dict[str, Any]) -> str:
        """
        Build system prompt based on chat configuration.

        Args:
            chat_config: Chat configuration dict

        Returns:
            System prompt text
        """
        purpose = chat_config.get("purpose", "general")
        tone = chat_config.get("tone", "simple_uzbek")
        strictness = chat_config.get("strictness", "strict_docs_only")

        # Base instruction
        system_prompt = "You are a helpful AI assistant that answers questions based on provided documents.\n\n"

        # Add purpose-specific instructions
        purpose_instructions = {
            "hr_assistant": "You specialize in HR policies and employee questions.",
            "policy_qa": "You help users understand policies and regulations.",
            "sop_helper": "You assist with standard operating procedures.",
            "product_docs": "You help users understand product documentation.",
        }

        if purpose in purpose_instructions:
            system_prompt += purpose_instructions[purpose] + "\n\n"

        # Add tone/language instructions
        tone_instructions = {
            "simple_uzbek": (
                "CRITICAL: You MUST respond in simple, clear Uzbek language (O'zbek tili). "
                "Use everyday words that regular people can understand. "
                "Avoid complex legal or technical jargon unless necessary.\n\n"
            ),
            "technical_russian": (
                "Respond in technical Russian. Use precise terminology. "
                "You may use technical terms when appropriate.\n\n"
            ),
            "formal_english": (
                "Respond in formal, professional English. "
                "Use proper grammar and business language.\n\n"
            ),
        }

        system_prompt += tone_instructions.get(
            tone, "Respond clearly and professionally.\n\n"
        )

        # Add strictness instructions
        if strictness == "strict_docs_only":
            system_prompt += (
                "IMPORTANT RULES:\n"
                "1. Answer ONLY based on the provided context documents.\n"
                "2. If the answer is not in the documents, say: "
                "\"Kechirasiz, bu ma'lumot hujjatlarda yo'q\" (Sorry, this information is not in the documents).\n"
                "3. Do NOT use your general knowledge.\n"
                "4. Do NOT make assumptions or guesses.\n"
                "5. ALWAYS cite your sources using [Doc: filename, Page: X] format.\n\n"
            )
        else:  # allow_reasoning
            system_prompt += (
                "RULES:\n"
                "1. Primarily answer based on the provided documents.\n"
                "2. You may use general knowledge if documents are incomplete.\n"
                "3. Clearly distinguish between document-based and general knowledge.\n"
                "4. Always cite document sources when using them.\n\n"
            )

        return system_prompt

    def build_user_prompt(self, query: str, contexts: List[RetrievedContext]) -> str:
        """
        Build user prompt with query and retrieved contexts.

        Args:
            query: User's question
            contexts: Retrieved context chunks

        Returns:
            Formatted user prompt
        """
        prompt = "CONTEXT DOCUMENTS:\n\n"

        # Format each context with citation info
        for i, ctx in enumerate(contexts, start=1):
            # Extract document name from metadata or use ID
            doc_name = ctx.metadata.get(
                "document_name", f"Document {ctx.document_id[:8]}"
            )
            page_info = f", Page {ctx.page_number}" if ctx.page_number else ""
            section_info = (
                f", Section: {ctx.section_title}" if ctx.section_title else ""
            )

            prompt += f"[Context {i}]\n"
            prompt += f"Source: {doc_name}{page_info}{section_info}\n"
            prompt += f"Content: {ctx.text}\n"
            prompt += "---\n\n"

        # Add the actual question
        prompt += f"QUESTION: {query}\n\n"
        prompt += "ANSWER (with citations):"

        return prompt

    def truncate_contexts(
        self, contexts: List[RetrievedContext], max_tokens: int = 4000
    ) -> List[RetrievedContext]:
        """
        Truncate contexts to fit within token limit.

        Simple heuristic: ~4 chars per token

        Args:
            contexts: List of contexts
            max_tokens: Maximum tokens allowed

        Returns:
            Truncated list of contexts
        """
        max_chars = max_tokens * 4
        total_chars = 0
        truncated = []

        for ctx in contexts:
            ctx_length = len(ctx.text)
            if total_chars + ctx_length <= max_chars:
                truncated.append(ctx)
                total_chars += ctx_length
            else:
                # Stop adding more contexts
                break

        if len(truncated) < len(contexts):
            self.logger.warning(
                f"Truncated contexts from {len(contexts)} to {len(truncated)} "
                f"to fit {max_tokens} token limit"
            )

        return truncated
