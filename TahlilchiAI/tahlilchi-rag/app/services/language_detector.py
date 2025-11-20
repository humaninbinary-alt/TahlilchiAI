"""Language detection service for documents."""

import logging

from langdetect import LangDetectException, detect

from app.core.exceptions import LanguageDetectionError

logger = logging.getLogger(__name__)


class LanguageDetector:
    """
    Service for detecting document language.

    Uses langdetect library to identify language from text samples.
    Supports Uzbek, Russian, English, and mixed language documents.
    """

    # Map langdetect codes to our standard codes
    LANG_MAP = {
        "uz": "uz",  # Uzbek
        "ru": "ru",  # Russian
        "en": "en",  # English
    }

    def detect_language(self, text: str) -> str:
        """
        Detect language from text.

        Samples from beginning, middle, and end of text to detect mixed languages.

        Args:
            text: Text to analyze

        Returns:
            Language code: 'uz', 'ru', 'en', or 'mixed'

        Raises:
            LanguageDetectionError: If detection fails
        """
        try:
            if len(text.strip()) < 50:
                logger.warning(
                    "Text too short for reliable language detection, defaulting to 'uz'"
                )
                return "uz"

            # Sample from beginning, middle, end to detect mixed languages
            samples = [
                text[:500],
                text[len(text) // 2 : len(text) // 2 + 500],
                text[-500:],
            ]

            detected_langs: set[str] = set()

            for sample in samples:
                if len(sample.strip()) < 50:
                    continue

                try:
                    lang = detect(sample)
                    mapped = self.LANG_MAP.get(lang, "other")
                    if mapped != "other":
                        detected_langs.add(mapped)
                except LangDetectException as e:
                    logger.debug(f"Language detection failed for sample: {e}")
                    continue

            # Determine final language
            if len(detected_langs) == 0:
                logger.warning("Could not detect language, defaulting to 'uz'")
                return "uz"
            elif len(detected_langs) == 1:
                detected_lang = detected_langs.pop()
                logger.info(f"Detected language: {detected_lang}")
                return detected_lang
            else:
                logger.info(f"Detected mixed languages: {detected_langs}")
                return "mixed"

        except Exception as e:
            logger.error(f"Language detection error: {e}")
            raise LanguageDetectionError(f"Failed to detect language: {e}")
