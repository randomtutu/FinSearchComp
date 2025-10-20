import os
import sys
import openai
from tenacity import retry, stop_after_attempt, wait_exponential

# Add project root directory to Python path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from config.config_wrapper import get_config_wrapper
from logger import get_logger

logger = get_logger(__name__)

class GeminiChat:
    def __init__(
            self, 
            model_name,
            api_version = "2024-03-01-preview",
            extra_headers = {"X-TT-LOGID": "", "caller": "liniuniu",},
            extra_body = {"tools": [{"type": "google_search"}]},
            ):
        config = get_config_wrapper()
        base_url = config.config['api']['gemini']['api_url']
        api_key = config.config['api']['gemini']['api_key']
        self.max_tokens = config.config['chat_defaults']['max_tokens']
        self.model_name = model_name
        self.extra_headers = extra_headers
        self.extra_body = extra_body
        self.client = openai.AzureOpenAI(
            azure_endpoint=base_url,
            api_version=api_version,
            api_key=api_key,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def __call__(self, prompts, histories, **kwargs):

        responses = []
        for prompt, history in zip(prompts, histories):
            messages = []
            if history:
                messages.extend(history)
            messages.append({"role": "user", "content": prompt})

            logger.debug("Sending request to Gemini model %s with %d messages", self.model_name, len(messages))

            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    extra_headers=self.extra_headers,
                    extra_body=self.extra_body,
                    **kwargs
                    )

                responses.append(response.choices[0].message.content)
            except Exception as e:
                logger.error("Gemini chat request failed: %s", e)
                responses.append({"error": str(e)})
        return responses

def load_gemini(model_name, **kwargs):
    return GeminiChat(model_name, **kwargs) 


if __name__ == "__main__":
    gemini = load_gemini(
        model_name = "gemini-2.5-flash",
        base_url = "",
        api_version = "2024-03-01-preview",
        api_key = "",
        max_tokens = 1000
    )
    response = gemini(['你好'], [[]])
    print(response)
