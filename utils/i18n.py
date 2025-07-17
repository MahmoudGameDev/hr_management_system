# c:\Users\mahmo\OneDrive\Documents\ai\HR\version\utils\i18n.py
import logging
import os
from typing import List, Dict
logger = logging.getLogger(__name__)
LOCALE_DIR = os.path.dirname(__file__) # Look for locale files in the current 'utils' directory
DEFAULT_LANG = "en"

class LanguageManager:
    def __init__(self):
        self.translations = {}
        self.current_lang = DEFAULT_LANG
        self.rtl_languages = ["ar"] # Add other RTL language codes if needed
        self._load_translations()

    def _load_translations(self):
        """Loads translation dictionaries from locale files."""
        self.translations = {}
        try:
            for filename in os.listdir(LOCALE_DIR):
                if filename.endswith(".py") and filename != "__init__.py":
                    lang_code = filename[:-3] # Remove .py extension
                    module_path = f"utils.{lang_code}" # Adjusted module path
                    try:
                        # Dynamically import the module
                        module = __import__(module_path, fromlist=['translations'])
                        if hasattr(module, 'translations') and isinstance(module.translations, dict):
                            self.translations[lang_code] = module.translations
                            logger.info(f"Loaded translations for language: {lang_code}")
                        else:
                            logger.warning(f"Locale file '{filename}' does not contain a 'translations' dictionary.")
                    except ImportError as e:
                        logger.error(f"Failed to import locale module '{module_path}': {e}")
                    except Exception as e: # pragma: no cover
                        logger.error(f"Error loading translations from '{filename}': {e}")

            if not self.translations:
                logger.error(f"No translation files found or loaded from {LOCALE_DIR}. Falling back to hardcoded defaults (if any).")
                # Optionally, add hardcoded minimal defaults here if no files are found at all
                self.translations[DEFAULT_LANG] = {"app_title": "HR Management System", "toggle_language_btn": "Toggle Language"} # Minimal fallback

        except FileNotFoundError:
             logger.error(f"Locale directory not found: {LOCALE_DIR}. Cannot load translations.")
             self.translations[DEFAULT_LANG] = {"app_title": "HR Management System", "toggle_language_btn": "Toggle Language"} # Minimal fallback
        except Exception as e:
             logger.error(f"An unexpected error occurred while loading translations: {e}")
             self.translations[DEFAULT_LANG] = {"app_title": "HR Management System", "toggle_language_btn": "Toggle Language"} # Minimal fallback

        # Ensure default language is available, if not, use the first loaded one or minimal fallback
        if DEFAULT_LANG not in self.translations and self.translations:
             self.current_lang = list(self.translations.keys())[0]
             logger.warning(f"Default language '{DEFAULT_LANG}' not found. Using '{self.current_lang}' instead.")
        elif DEFAULT_LANG in self.translations:
             self.current_lang = DEFAULT_LANG


    def get_string(self, key, **kwargs):
        lang_dict = self.translations.get(self.current_lang, {})
        base_string = lang_dict.get(key)

        if base_string is None: # Key not found in current language
            if self.current_lang != DEFAULT_LANG:
                logger.warning(f"Translation key '{key}' not found for current language '{self.current_lang}'. Trying default language '{DEFAULT_LANG}'.")
            default_lang_dict = self.translations.get(DEFAULT_LANG, {})
            base_string = default_lang_dict.get(key)
            if base_string is None: # Key not found in default language either
                logger.error(f"Translation key '{key}' not found in current ('{self.current_lang}') or default ('{DEFAULT_LANG}') language. Falling back to key itself.")
                base_string = key # Fallback to key itself
        
        return base_string.format(**kwargs) if kwargs else base_string

    def set_language(self, lang_code):
        if lang_code in self.translations:
            self.current_lang = lang_code
            logger.info(f"Language changed to: {lang_code}")
            # No need to reload translations here if all are loaded in __init__
            return True
        logger.warning(f"Language '{lang_code}' not supported.")
        return False
    def get_supported_languages(self) -> List[str]:
        """Returns a list of supported language codes."""
        return list(self.translations.keys())

    def is_rtl(self):
        return self.current_lang in self.rtl_languages

# Global instance of LanguageManager
LANG_MANAGER = LanguageManager()

# Helper function for convenience (similar to gettext's _)
def _(key, **kwargs):
    return LANG_MANAGER.get_string(key, **kwargs)