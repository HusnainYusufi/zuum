import json
import os
from typing import List, Dict, Any

# Form type constants
FORM_TYPE_DEFAULT = "default"
FORM_TYPE_AT_PICKUP = "at_pickup"
FORM_TYPE_PICKUP_COMPLETE = "pickup_complete"
FORM_TYPE_IN_TRANSIT = "in_transit"
FORM_TYPE_AT_DROP = "at_drop"
FORM_TYPE_DELIVERED = "delivered"
FORM_TYPE_REQUEST_POD = "request_pod"


class PromptConfig:
    def __init__(self):
        """Initialize PromptConfig with form type mapping"""
        self.base_dir = os.path.dirname(__file__)

        # Form type to number mapping (used by retell API)
        self.FORM_TYPE_MAPPING = {
            FORM_TYPE_DEFAULT: 0,
            FORM_TYPE_AT_PICKUP: 1,
            FORM_TYPE_PICKUP_COMPLETE: 2,
            FORM_TYPE_IN_TRANSIT: 3,
            FORM_TYPE_AT_DROP: 4,
            FORM_TYPE_DELIVERED: 5,
            FORM_TYPE_REQUEST_POD: 6
        }

    def _load_scenario_file(self, form_type: str) -> Dict[str, Any]:
        """Load a specific scenario file"""
        scenario_path = os.path.join(self.base_dir, f"scenario_{form_type}.json")

        if not os.path.exists(scenario_path):
            raise FileNotFoundError(f"Scenario file not found: scenario_{form_type}.json")

        with open(scenario_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_scenario_file(self, form_type: str, config: Dict[str, Any]) -> None:
        """Save a specific scenario file"""
        scenario_path = os.path.join(self.base_dir, f"scenario_{form_type}.json")

        with open(scenario_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def get_form_config(self, form_type: str) -> Dict[str, Any]:
        """Get configuration for a specific form type (loads only what's needed)"""
        return self._load_scenario_file(form_type)

    def update_form_config(self, form_type: str, config: Dict[str, Any]) -> None:
        """Update configuration for a specific form type"""
        self._save_scenario_file(form_type, config)

    def get_all_form_types(self) -> List[str]:
        """Get list of all available form types from mapping"""
        return list(self.FORM_TYPE_MAPPING.keys())

    def update_voice_questions(self, form_type: str, questions: List[str]) -> None:
        """Update voice questions for a specific form type"""
        config = self.get_form_config(form_type)
        config["voice_questions"] = questions
        self.update_form_config(form_type, config)

    def update_output_schema(self, form_type: str, output_schema: Dict[str, Any]) -> None:
        """Update output schema for a specific form type"""
        config = self.get_form_config(form_type)
        config["output_schema"] = output_schema
        self.update_form_config(form_type, config)


# Create a singleton instance
prompt_config = PromptConfig()
