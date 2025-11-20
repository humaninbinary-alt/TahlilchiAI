"""Multilingual tokenizer for Uzbek, Russian, and English text."""

import logging
import re
from typing import List

import nltk
from nltk.corpus import stopwords

logger = logging.getLogger(__name__)


class MultilingualTokenizer:
    """
    Tokenizer for Uzbek, Russian, and English text.

    Features:
    - Lowercasing
    - Punctuation removal
    - Stopword removal (optional)
    - Number preservation (important for article numbers, IDs)
    """

    def __init__(self, remove_stopwords: bool = True):
        """
        Initialize tokenizer.

        Args:
            remove_stopwords: Whether to remove stopwords
        """
        self.remove_stopwords = remove_stopwords
        self.logger = logger

        # Load stopwords for supported languages
        try:
            self.stopwords = set()
            if remove_stopwords:
                # English and Russian stopwords available in NLTK
                self.stopwords.update(stopwords.words("english"))
                self.stopwords.update(stopwords.words("russian"))
                # Uzbek stopwords (basic list)
                self.stopwords.update(self._get_uzbek_stopwords())
        except LookupError:
            self.logger.warning("NLTK stopwords not found, downloading...")
            nltk.download("stopwords", quiet=True)
            self.stopwords = set(stopwords.words("english"))
            self.stopwords.update(stopwords.words("russian"))
            self.stopwords.update(self._get_uzbek_stopwords())

    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into list of tokens.

        Args:
            text: Input text

        Returns:
            List of tokens (lowercased, cleaned)
        """
        if not text or not text.strip():
            return []

        # Lowercase
        text = text.lower()

        # Basic tokenization (split on whitespace and punctuation)
        # But preserve numbers and hyphens (for article numbers like "article-27")
        tokens = re.findall(r"\b[\w-]+\b", text)

        # Remove stopwords if enabled
        if self.remove_stopwords:
            tokens = [t for t in tokens if t not in self.stopwords]

        # Remove very short tokens (< 2 chars) unless they're numbers
        tokens = [t for t in tokens if len(t) >= 2 or t.isdigit()]

        return tokens

    def _get_uzbek_stopwords(self) -> List[str]:
        """
        Basic Uzbek stopwords list.

        Note: This is a minimal list. Can be expanded.

        Returns:
            List of Uzbek stopwords
        """
        return [
            "va",
            "yoki",
            "lekin",
            "uchun",
            "bilan",
            "dan",
            "ga",
            "ni",
            "bu",
            "shu",
            "o",
            "u",
            "ham",
            "yoxud",
            "yo",
            "esa",
            "edi",
            "ekan",
            "kerak",
            "mumkin",
            "sifatida",
            "haqida",
            "agar",
        ]
