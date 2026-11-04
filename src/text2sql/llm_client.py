"""Optional LLM client stub — disabled by default, never called offline.

The engine works fully offline with the rule/template generator in
generator.py. This stub exists so a future LLM provider can be plugged
in without changing the evaluator: set enabled=True and provide an
api_key, and generate() will still refuse unless a real provider
implementation is added (it currently raises NotImplementedError
rather than inventing an API call or a cost). No API key is required,
stored, or sent anywhere by this project.
"""


class LLMClient:
    def __init__(self, enabled=False, api_key=None, model=None):
        self.enabled = enabled
        self.api_key = api_key
        self.model = model

    def generate(self, prompt):
        """Generate SQL via LLM. Disabled by default."""
        if not self.enabled:
            return None
        if not self.api_key:
            raise ValueError("LLM is enabled but no api_key was provided")
        raise NotImplementedError(
            "No LLM provider is implemented in this project. "
            "Plug in a real provider here; do not use this stub to "
            "claim LLM-generated results or costs."
        )
