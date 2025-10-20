import argparse
import datetime as dt
import json
import logging
import os
import re
import subprocess
import sys
import time
from typing import Any, Dict

import akshare as ak

# Add project root directory to Python path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from config.config_wrapper import initialize_config
from models.openai_api import load_model
from logger import get_logger
from finsearchcomp.data import fetch_single, get_snapshot_directory

# Setup logging
logger = get_logger(__name__)

# Default error score
DEFAULT_ERROR_SCORE = -100000
_SNAPSHOT_FRESHNESS_CHECKED = False


def _latest_snapshot_date(snapshot_dir: str) -> dt.date | None:
    """Return the most recent snapshot date parsed from filenames in the directory."""
    pattern = re.compile(r"_(\d{8})T\d+Z\.(csv|json)$", re.IGNORECASE)
    latest: dt.date | None = None

    try:
        entries = [
            entry for entry in os.listdir(snapshot_dir)
            if os.path.isfile(os.path.join(snapshot_dir, entry))
        ]
    except FileNotFoundError:
        logger.info("Snapshot directory %s does not exist yet.", snapshot_dir)
        return None

    for entry in entries:
        match = pattern.search(entry)
        if not match:
            continue
        candidate = dt.datetime.strptime(match.group(1), "%Y%m%d").date()
        if not latest or candidate > latest:
            latest = candidate
    return latest


def _refresh_snapshots() -> bool:
    """Invoke the snapshot fetch script to refresh on-disk market data."""
    script_path = os.path.join(root_dir, "scripts", "fetch_market_data.py")
    if not os.path.exists(script_path):
        logger.error("Snapshot refresh script not found at %s", script_path)
        return False

    logger.info("Refreshing market snapshots via %s", script_path)
    try:
        subprocess.run([sys.executable, script_path], check=True)
    except subprocess.CalledProcessError as exc:
        logger.error("Snapshot refresh failed with exit code %s", exc.returncode)
        return False
    except OSError as exc:
        logger.error("Failed to execute snapshot refresh script: %s", exc)
        return False

    return True


def ensure_snapshots_current() -> None:
    """Ensure on-disk market snapshots are from the current calendar day."""
    global _SNAPSHOT_FRESHNESS_CHECKED
    if _SNAPSHOT_FRESHNESS_CHECKED:
        return

    snapshot_dir = get_snapshot_directory()
    today = dt.datetime.now().date()
    latest_date = _latest_snapshot_date(snapshot_dir)

    if latest_date != today:
        logger.info(
            "Cached snapshot date %s does not match today's date %s; refreshing.",
            latest_date,
            today,
        )
        if _refresh_snapshots():
            latest_date = _latest_snapshot_date(snapshot_dir)
        else:
            logger.warning("Snapshot refresh attempt failed; proceeding with existing data.")

    if latest_date != today:
        logger.warning(
            "Latest snapshot date %s still differs from today %s after refresh.",
            latest_date,
            today,
        )
    else:
        logger.info("Snapshot data confirmed for %s.", today)

    _SNAPSHOT_FRESHNESS_CHECKED = True


def parse_judge_output(judge_output: str) -> float:
    """Parse numerical score from judge's output"""
    if not isinstance(judge_output, str):
        logger.warning(f"Input passed to parse_judge_output is not a string: {type(judge_output)}")
        return DEFAULT_ERROR_SCORE
    try:
        # Extract JSON part
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", judge_output, re.DOTALL)
        if not json_match:
            logger.warning(f"Unable to find JSON block from judge output: {judge_output}")
            return DEFAULT_ERROR_SCORE

        judge_json = json.loads(json_match.group(1))
        # Extract score, assuming it's nested as [[score]]
        score = judge_json.get("answer_score", [[DEFAULT_ERROR_SCORE]])[0][0]
        return float(score)
    except (json.JSONDecodeError, IndexError, TypeError, ValueError) as e:
        logger.warning(f"Error parsing judge output JSON or score: {e}\nOutput: {judge_output}")
        return DEFAULT_ERROR_SCORE


def evaluate_response(
        judge_user_input,
        judge_model, 
        judge_system_prompt) -> Dict[str, Any]:
    """Evaluate model response"""

    # Call judge model
    history = [{"role": "system", "content": judge_system_prompt}]
    judge_response = judge_model([judge_user_input], [history])[0]
    
    # Parse score
    score = parse_judge_output(judge_response)
    
    # Return evaluation result
    return {
        "judge_response": judge_response,
        "score": score
    }


def get_judge_user_input(data, response):
    prompt = data['prompt']
    prompt_id = data['prompt_id'][0]
    prompt_template = data['judge_prompt_template']
    response_reference = data['response_reference']
    if 'T1' in prompt_id:
        akshare_ticker = data['akshare_ticker']
        tag = data['tags']
        method = data.get('method', None)
        ensure_snapshots_current()
        ground_truth = fetch_single(akshare_ticker, tag, method)

        judge_user_input = prompt_template.format(
            prompt = prompt,
            response_reference = response_reference,
            ground_truth = ground_truth,
            response = response,
        )
    else:
        judge_user_input = prompt_template.format(
            prompt = prompt,
            response_reference = response_reference,
            response = response,
        )
    return judge_user_input


# Load input file and complete model evaluation
def process_file(data: Dict, model, output_file: str = None):
    """Process input file, evaluate model response"""
    prompt_id = data['prompt_id']
    
    # Initialize result
    results = dict([(k, v) for k,v in data.items()])
    results['evaluations'] = []
    results['accuracy'] = 0.0

    # Process each dialogue to be evaluated
    total_score = 0.0
    valid_evals = 0
    
    # Calculate the score of non-TS tasks
    non_ts_total_score = 0.0
    non_ts_valid_evals = 0
    
    logger.info(f"Data keys: {list(data.keys())}")
    logger.info(f"prompt_ids: {prompt_id}")
    logger.info(f"response_reference: {len(data.get('response_reference', []))}")
    logger.info(f"dialogues: {len(data.get('dialogues', []))}")
    
    for dialogue in data.get("dialogues", []):
        prompt_id = dialogue.get("prompt_id", "")
        
        # If this prompt_id is in eval_id list, then evaluation is needed
        prompt = data["prompt"]
        model_response = dialogue["model_response"]
        judge_system_prompt = data["judge_system_prompt"]
        judge_user_input = get_judge_user_input(data, model_response)


        # If necessary information is missing, skip this evaluation
        if not model_response:
            logger.warning(f"Dialog {prompt_id} lacks necessary evaluation information, skipping")
            continue
        
        # Evaluate response
        evaluation = evaluate_response(judge_user_input, model, judge_system_prompt)
        
        # Record evaluation result
        eval_result = {
            "id": prompt_id,
            "question": prompt,
            "model_response": model_response,
            "judge_user_input": judge_user_input,
            "judge_response": evaluation["judge_response"],
            "score": evaluation["score"]
        }
        
        results["evaluations"].append(eval_result)
        total_score += evaluation["score"]
        valid_evals += 1
        
        logger.info(f"Evaluation completed {prompt_id}: score {evaluation['score']}")
    
    # Calculate total accuracy
    if valid_evals > 0:
        # Save the total accuracy of all evaluations (including TS) as the original accuracy
        results["original_accuracy"] = total_score / valid_evals
        
        # Use the accuracy of non-TS evaluations as the main accuracy
        if non_ts_valid_evals > 0:
            results["accuracy"] = non_ts_total_score / non_ts_valid_evals
        else:
            results["accuracy"] = 0.0
    

    # Save result
    if output_file:
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Evaluation results saved to {output_file}")
        logger.info(f"Total accuracy: {results['accuracy']:.4f}")
    
    return results


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Evaluate model response')
    parser.add_argument('--model_name', type=str, default='deepseek-chat', help='Model name')
    parser.add_argument('--api_key', type=str, help='API key (optional, will override config file)')
    parser.add_argument('--input', type=str, required=True, help='Input file path')
    parser.add_argument('--output', type=str, default='result/eval.json', help='Output file path')
    parser.add_argument('--config', type=str, default='config/config.yaml', help='Config file path')
    args = parser.parse_args()
    
    # Build full path
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_path = os.path.abspath(args.input)
    output_path = os.path.abspath(args.output)
    config_path = os.path.join(base_dir, args.config)
    
    # Initialize config
    try:
        initialize_config(config_path)
        logger.info(f"Config loaded from {config_path}")
    except Exception as e:
        logger.error(f"Error initializing config: {e}")
        return
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    logger.info(f"Input file: {input_path}")
    logger.info(f"Output file: {output_path}")
    
    # Load model
    model = load_model(args.model_name)

    # Read entire JSON file instead of reading line by line
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
        # Check if data is a list
        if isinstance(data, list):
            logger.info(f"Processing a list of {len(data)} dialogue objects")
            all_results = []
            total_accuracy_sum = 0.0
            valid_results = 0
            
            # Process each item in the list
            for i, item in enumerate(data):
                # Use a temporary output file for individual results if needed
                temp_output = None
                
                # Process each dialogue object
                result = process_file(item, model, temp_output)
                all_results.append(result)
                
                # Calculate overall accuracy
                if "accuracy" in result and result["accuracy"] > 0:
                    total_accuracy_sum += result["accuracy"]
                    valid_results += 1
                    
                logger.info(f"Processed item {i+1}/{len(data)}, accuracy: {result.get('accuracy', 0):.4f}")
        # Calculate overall accuracy across all items
            overall_accuracy = total_accuracy_sum / valid_results if valid_results > 0 else 0.0
            
            # Save all results to the output file
            if output_path:
                with open(output_path, 'w', encoding='utf-8') as out_f:
                    json.dump(all_results, out_f, ensure_ascii=False, indent=2)
                    
                logger.info(f"All results saved to {output_path}")
                logger.info(f"Overall accuracy across all items: {overall_accuracy:.4f}")
        else:
            # Process single JSON object
            result = process_file(data, model, output_path)
            logger.info(f"Evaluation completed, total accuracy: {result['accuracy']:.4f}")


if __name__ == "__main__":
    main()
