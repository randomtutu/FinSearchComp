import json
import os
import sys
import argparse
import yaml
import random

from tqdm import tqdm

# Add project root directory to Python path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Import necessary modules
from config.config_wrapper import initialize_config
from logger import get_logger

# Initialize configuration
config_path = os.path.join(root_dir, 'config', 'config.yaml')
initialize_config(config_path)

# Import models
from models.deepseek_api import load_model as load_deepseek
from models.openai_api import load_model as load_openai
from models.gemini import load_gemini
# from models.claude_api import load_model as load_claude


def get_available_models():
    """
    Get available models from configuration file
    """
    config_path = os.path.join(root_dir, 'config', 'config.yaml')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        available_models = []
        api_config = config.get('api', {})
        
        # Check each API configuration
        if api_config.get('openai', {}).get('api_key'):
            available_models.append('gpt-3.5-turbo')
            available_models.append('gpt-4')
        
        if api_config.get('deepseek', {}).get('api_key'):
            available_models.append('deepseek-chat')
            available_models.append('deepseek-coder')
        
        if api_config.get('anthropic', {}).get('api_key'):
            available_models.append('claude-3-sonnet')
            available_models.append('claude-3-opus')
        
        return available_models
    except Exception as e:
        print(f"Error reading configuration file: {e}")
        return []


def load_model(model_name, api_key=None):
    """Load the appropriate model based on model name"""
    model_name_lower = model_name.lower()
    
    if 'deepseek' in model_name_lower:
        return load_deepseek(model_name, api_key=api_key)
    elif 'gpt' in model_name_lower:
        return load_openai(model_name, api_key=api_key)
    elif 'gemini' in model_name_lower:
        return load_gemini(model_name)
    else:
        raise ValueError(f"Unsupported model type: {model_name}")


def process_game(data, model, output_path):
    """Process single dialogue data"""

    prompt_id = [data['prompt_id']]
    prompt = data['prompt']

    # Initialize result
    result = dict([(k, v) for k,v in data.items()])
    result["dialogues"] =  []
    result['prompt_id'] = prompt_id

    # Process each question
    history = []
    msgs = [{'role':'user', 'content': prompt}]
    # Calculate user question index
    user_question_index = 0
    total_questions = 1

    # Iterate through all messages
    for message in msgs:
        if message['role'] == 'user':                
            question = message['content']
            
            # Get corresponding prompt_id
            if 'prompt_id' in data and user_question_index < len(data['prompt_id']):
                prompt_id = prompt_id[user_question_index]
                user_question_index += 1
            else:
                prompt_id = None

            # Call model to get answer
            responses = model([question], [history])
            response = responses[0]

            # Add question and answer to dialogue history
            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": response})
            
            # Save dialogue content
            result['dialogues'].append({
                "prompt_id": prompt_id,
                "question": question,
                "model_response": response
            })
            
            # Progress logging moved to main loop to reflect record-level progress
    
    return result


def main():
    parser = argparse.ArgumentParser(description='Dialogue processing program')
    parser.add_argument('--model_name', type=str, default='deepseek-chat', help='Model name')
    parser.add_argument('--api_key', type=str, help='API key (optional, overrides configuration file)')
    parser.add_argument('--input_file', type=str, required=True, help='Input file path')
    parser.add_argument('--output_path', type=str, default='result/chat-result/chat.json', help='Output file path')
    parser.add_argument('--limit', type=int, default=10, help='Number of records to process; 0 means all')
    args = parser.parse_args()

    # Build complete paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_path = os.path.normpath(os.path.join(base_dir, args.input_file))
    output_path = os.path.normpath(os.path.join(base_dir, args.output_path))
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Load model
    try:
        model = load_model(args.model_name, api_key=args.api_key)
    except Exception as e:
        print(f"Error loading model: {e}")
        return
    
    # Read and process all dialogue data
    results = []
    with open(input_path, 'r', encoding='utf-8') as f:
        records = json.load(f)
        random.shuffle(records)
        subset = records[:args.limit] if (args.limit and args.limit > 0) else records
        for idx, data in enumerate(subset, start=1):
            result = process_game(data, model, output_path)
            results.append(result)
            print(f"Processed record {idx}/{len(subset)}")

    # Save results
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Results saved to: {output_path}")

if __name__ == "__main__":
    main()

# python chat.py --input_file data/test.jsonl --output_path result/chat-result/chat-test.json
