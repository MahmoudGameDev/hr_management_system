# hr_dashboard_project/utils/localization.py
import json
import os
import logging
# from . import en  # Comment out or remove if using JSON files
# from . import ar  # Comment out or remove if using JSON files

logger = logging.getLogger(__name__)

class LanguageManager:
    def __init__(self, default_lang="en"):
        self.languages = {} # Will be populated from JSON files
        self.current_lang = default_lang
        self.default_lang = default_lang
        self.locales_dir = os.path.dirname(__file__) # Directory where en.json, ar.json are located

        self._load_all_languages() # This call is correct

        if default_lang not in self.languages:
            logger.warning(f"Default language '{default_lang}' not found. Falling back to 'en'.")
            self.current_lang = "en"
            self.default_lang = "en"
            if "en" not in self.languages: # Ensure 'en' is loaded if it's the ultimate fallback
                self._load_language("en")

    def _load_language(self, lang_code: str):
        """Loads a single language from its JSON file."""
        expected_path = os.path.join(self.locales_dir, f"{lang_code}.json")
        try:
            with open(expected_path, "r", encoding="utf-8") as f:
                self.languages[lang_code] = json.load(f)
            logger.info(f"Successfully loaded translations for '{lang_code}' from {expected_path}")
        except FileNotFoundError:
            logger.error(f"Language file not found for '{lang_code}' at {expected_path}")
            self.languages[lang_code] = {} # Empty dict if file not found
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON for '{lang_code}' from {expected_path}: {e}")
            self.languages[lang_code] = {}

    def _load_all_languages(self): # Moved inside the class
        """Loads all available .json language files from the locales directory."""
        for filename in os.listdir(self.locales_dir):
            if filename.endswith(".json"):
                lang_code = filename[:-5] # Remove .json
                self._load_language(lang_code)

    def set_language(self, lang_code: str) -> bool:
        if lang_code in self.languages:
            self.current_lang = lang_code
            logger.info(f"Language changed to: {lang_code}")
            return True
        else:
            # Attempt to load the language if not already loaded
            self._load_language(lang_code)
            if lang_code in self.languages and self.languages[lang_code]: # Check if loading was successful
                self.current_lang = lang_code
                logger.info(f"Language changed to: {lang_code} (loaded on demand)")
                return True
            logger.warning(f"Language '{lang_code}' not supported. Language remains '{self.current_lang}'.")
            return False

    def get_translation(self, key: str, **kwargs) -> str:
        # Try current language
        translation = self.languages.get(self.current_lang, {}).get(key)

        # Fallback to default language if not found in current
        if translation is None and self.current_lang != self.default_lang:
            translation = self.languages.get(self.default_lang, {}).get(key)
            if translation:
                logger.debug(f"Translation key '{key}' not found in '{self.current_lang}', used default '{self.default_lang}'.")

        # Fallback to the key itself if not found in default either
        if translation is None:
            logger.error(f"Translation key '{key}' not found in current ('{self.current_lang}') or default ('{self.default_lang}') language. Falling back to key itself.")
            return key # Return the key itself as a fallback

        try:
            return translation.format(**kwargs) if kwargs else translation
        except KeyError as e_format: # pragma: no cover
            logger.error(f"Formatting error for key '{key}' with args {kwargs}. Missing placeholder: {e_format}. Translation: '{translation}'")
            return translation # Return unformatted string on error

# Global instance of LanguageManager
LANG_MANAGER = LanguageManager()

def _(key: str, **kwargs) -> str:
    """Global translation function."""
    return LANG_MANAGER.get_translation(key, **kwargs)

def init_translation(default_lang_code: str = "en"):
    """Initializes the language manager with a default language."""
    LANG_MANAGER.set_language(default_lang_code)
    logger.info(f"Translation system initialized. Current language: {LANG_MANAGER.current_lang}")

