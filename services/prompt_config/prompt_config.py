import json
import os
from typing import List, Dict, Any

class PromptConfig:
    def __init__(self):
        self.config_data = self.load_config()
        self.FORM_CONFIG = self.config_data['FORM_CONFIG']
        self.FORM_TYPE_MAPPING = self.config_data['FORM_TYPE_MAPPING']

    def load_config(self):
        """Load configuration from JSON file"""
        config_path = os.path.join(os.path.dirname(__file__), 'prompt_config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_form_config(self, form_type: str) -> Dict[str, Any]:
        """Get configuration for a specific form type"""
        # Always load fresh config from file
        config_data = self.load_config()
        return config_data['FORM_CONFIG'].get(form_type, config_data['FORM_CONFIG']["default"])

    def get_all_form_types(self) -> List[str]:
        """Get list of all available form types"""
        # Always load fresh config from file
        config_data = self.load_config()
        return list(config_data['FORM_CONFIG'].keys())

    def get_voice_questions(self, form_type: str) -> List[str]:
        """Get voice agent questions for a specific form type"""
        config = self.get_form_config(form_type)
        return config.get("voice_questions", [])

    def get_form_fields(self, form_type: str) -> Dict[str, Dict[str, Any]]:
        """Get form fields configuration for a specific form type"""
        config = self.get_form_config(form_type)
        return config.get("fields", {})

# Create a singleton instance
prompt_config = PromptConfig()
