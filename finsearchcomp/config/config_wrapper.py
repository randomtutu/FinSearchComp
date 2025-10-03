import yaml

class ConfigWrapper:
    def __init__(self, config):
        self.config = config
        self.model_config = config.get('model', {})
        self.api_config = config.get('api', {})
        self.chat_config = config.get('chat', {})
        self.evaluation_config = config.get('evaluation', {})
        
        # Model keys
        self.response_key = self.model_config.get('response_key', 'response')
        self.error_key = self.model_config.get('error_key', 'error')
        self.prompt_key = self.model_config.get('prompt_key', 'prompt')
        self.history_key = self.model_config.get('history_key', 'history')
        self.id_key = self.model_config.get('id_key', 'id')
        
        # API configuration
        self.azure_endpoint = self.api_config.get('azure_endpoint')
        self.api_version = self.api_config.get('api_version')
        self.api_key = self.api_config.get('api_key')
        self.caller = self.api_config.get('caller', 'default_caller')
        
        # Chat parameters
        self.max_tokens = self.chat_config.get('max_tokens', 2000)
        self.temperature = self.chat_config.get('temperature', 0.7)
        self.top_p = self.chat_config.get('top_p', 1.0)
        self.frequency_penalty = self.chat_config.get('frequency_penalty', 0.0)
        self.presence_penalty = self.chat_config.get('presence_penalty', 0.0)
        
        # Retry parameters
        self.max_retries = self.chat_config.get('max_retries', 3)
        self.retry_delay = self.chat_config.get('retry_delay', 4)
        self.max_retry_delay = self.chat_config.get('max_retry_delay', 10)
        
        # Evaluation metrics
        self.metrics = self.evaluation_config.get('metrics', ['accuracy'])

        # Extra headers
        self.extra_headers = config.get('extra_headers')

        # Extra body
        self.extra_body = config.get('extra_body')


    def get_chat_params(self):
        return {
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'top_p': self.top_p,
            'frequency_penalty': self.frequency_penalty,
            'presence_penalty': self.presence_penalty
        }

    def get_api_params(self):
        return {
            'azure_endpoint': self.azure_endpoint,
            'api_version': self.api_version,
            'api_key': self.api_key,
            'caller': self.caller
        }

_config_wrapper = None

def initialize_config(config_path):
    global _config_wrapper
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    _config_wrapper = ConfigWrapper(config)


def get_config_wrapper():
    if _config_wrapper is None:
        raise ValueError("Config not initialized. Call initialize_config first.")
    return _config_wrapper