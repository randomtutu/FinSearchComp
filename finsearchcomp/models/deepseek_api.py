import requests
import json
import os
import sys
from tenacity import retry, stop_after_attempt, wait_exponential

# Add project root directory to Python path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from config.config_wrapper import get_config_wrapper

class DeepSeekChat:
    def __init__(self, model_name, api_key=None):
        self.model_name = model_name
        config = get_config_wrapper()
        
        # Prioritize the API key passed in, if not provided use the key from config file
        self.api_key = api_key or config.config['api']['deepseek']['api_key']
        if not self.api_key:
            raise ValueError("DeepSeek API key not found. Please set it in config.yaml or pass it as a parameter.")
        
        self.api_url = config.config['api']['deepseek']['api_url']
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def __call__(self, prompts, histories, **kwargs):
        responses = []
        for prompt, history in zip(prompts, histories):
            messages = []
            if history:
                messages.extend(history)
            messages.append({"role": "user", "content": prompt})
            
            try:
                data = {
                    "model": self.model_name,
                    "messages": messages,
                    **kwargs
                }
                
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json=data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    responses.append(result['choices'][0]['message']['content'])
                else:
                    error_msg = f"API request failed with status code {response.status_code}: {response.text}"
                    responses.append({"error": error_msg})
                    
            except Exception as e:
                responses.append({"error": str(e)})
        return responses

def load_model(model_name, **kwargs):
    return DeepSeekChat(model_name, **kwargs)