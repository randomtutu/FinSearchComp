import re
import json
import logging
import os
import sys
import argparse
import time
from typing import Any, Dict
import time, re, datetime as dt

import akshare as ak

# Add project root directory to Python path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from config.config_wrapper import initialize_config, get_config_wrapper
from models.deepseek_api import load_model as load_deepseek
from models.openai_api import load_model as load_openai
from models.gemini import load_gemini
from logger import get_logger

# Setup logging
logger = get_logger(__name__)

# Default error score
DEFAULT_ERROR_SCORE = -100000

_CACHE = {}  # {universe: {"ts": epoch_seconds, "df": DataFrame}}

UNIVERSE = {
    "CN_STOCK":  lambda: ak.stock_zh_a_spot_em(),                   # A-share full snapshot
    "US_STOCK":  lambda: ak.stock_us_spot_em(),                     # US stock full snapshot
    "HK_STOCK":  lambda: ak.stock_hk_spot_em(),                     # HK stock full snapshot
    "CN_INDEX":  lambda: ak.stock_zh_index_spot_em("沪深重要指数"),   # Index full snapshot
    "H_INDEX":   lambda: ak.stock_hk_index_spot_em(),               # hk index full snapshot
    "GLOBAL_IDX":lambda: ak.index_global_spot_em(),                 # Global index full snapshot
    "FX":        lambda: ak.forex_spot_em(),                        # Forex full snapshot
}


def select_model(model_name: str, api_key: str | None = None):
    """Select and load model implementation based on model_name.
    Supports DeepSeek, OpenAI (Azure OpenAI-compatible), and Gemini wrappers.
    """
    name = (model_name or '').lower()
    if 'deepseek' in name:
        return load_deepseek(model_name, api_key=api_key)
    if 'gpt' in name:
        return load_openai(model_name, api_key=api_key)
    if 'gemini' in name:
        return load_gemini(model_name)
    raise ValueError(f"Unsupported model type: {model_name}")


def _get_df(universe: str, ttl_sec: int):
    now = time.time()
    ent = _CACHE.get(universe)
    if not ent or now - ent["ts"] > ttl_sec:
        df = UNIVERSE[universe]()
        _CACHE[universe] = {"ts": now, "df": df}
    return _CACHE[universe]["df"]


def _norm_cn(code: str) -> str:
    c = code.strip().upper()
    return c.split(".")[0] if c.endswith((".SH",".SZ",".BJ")) else c


def _norm_os(code: str):
    raw = code.strip().upper()
    if raw.endswith(".USA"): return "US_STOCK", raw[:-4]
    if raw.endswith(".US"):  return "US_STOCK", raw[:-3]
    if raw.endswith(".HK"):  return "HK_STOCK", raw[:-3].zfill(5)
    if re.fullmatch(r"\d{1,5}", raw): return "HK", raw.zfill(5)
    return "US", raw  # Compatible with 105.AAPL or AAPL


def _pick_row(df, code, name_hint=None):
    cols = set(df.columns.astype(str))
    if "代码" in cols:
        s = df["代码"].astype(str).str.upper()
        hit = df[s == code.upper()]
        if hit.empty and "." in code:
            hit = df[s.str.endswith("." + code.split(".")[-1].upper())]
        if not hit.empty: return hit.iloc[0]
    if "名称" in cols:
        key = (name_hint or code).upper()
        hit = df[df["名称"].astype(str).str.upper().str.contains(key, na=False)]
        if not hit.empty: return hit.iloc[0]
    if "代码" in cols:
        hit = df[df["代码"].astype(str).str.upper().str.contains(code.upper(), na=False)]
        if not hit.empty: return hit.iloc[0]
    return None


def _as_quote(row, orig_ticker):
    g = row.get
    def f(primary, alt=None):
        v = g(primary, g(alt, None))
        return float(v) if (v not in (None, "")) else None
    fetch_dt_utc = dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)
    return {
        "ticker": orig_ticker,
        "name": g("名称", None),
        "price": f("最新价", "当前价"),
        "change": f("涨跌额"),
        "pct_change": f("涨跌幅"),
        "open": f("今开", "开盘价"),
        "high": f("最高", "最高价"),
        "low":  f("最低", "最低价"),
        "prev_close": f("昨收", "昨收价"),
        "volume": f("成交量"),
        "amount": f("成交额"),
        "quote_time": g("最新行情时间", g("时间", None)),
        "fetch_time_utc": fetch_dt_utc.isoformat(),
        "fetch_time_epoch": int(fetch_dt_utc.timestamp()),
    }


def fetch_single(ticker: str, tags: str, method: str, ttl_sec: int = 60, max_retries: int = 3, retry_delay: float = 2.0):
    """
    tags in {"汇率","指数","股票","Index","Stock"}
    ttl_sec: 同一市场快照的缓存时长（秒）
    max_retries: 最大重试次数
    retry_delay: 重试间隔（秒）
    """
    tag = tags.strip()
    # 路由到市场
    if tag == "汇率": 
        uni, code, name_hint = "FX", ticker.strip().upper(), None
    elif tag == "指数" and method == "akshare_HK_index":
        uni, code, name_hint = "H_INDEX", ticker, None
    elif tag == "指数" and method == "akshare_沪深重要指数_index":
        uni, code, name_hint = "CN_INDEX", _norm_cn(ticker), None
    elif tag == "Index": 
        uni, name = "GLOBAL_IDX", ticker.strip().upper()
        code, name_hint = name, name
    elif tag == "股票": 
        uni, code, name_hint = "CN_STOCK", _norm_cn(ticker), None
    elif tag == "Stock":
        mkt, code = _norm_os(ticker)
        uni, name_hint = mkt, None
    else:
        raise ValueError(f"未知 tags: {tags}")

    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            # Only capture the full amount once when the market is first opened or the TTL expires; otherwise, use the cache directly.
            df = _get_df(uni, ttl_sec=ttl_sec)
            if df is None or df.empty: 
                return None

            row = _pick_row(df, code, name_hint)
            return _as_quote(row, ticker) if row is not None else None
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                logger.warning(f"Attempt {attempt + 1} failed for {ticker}: {e}. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error(f"All {max_retries + 1} attempts failed for {ticker}: {e}")
                raise last_exception


def parse_judge_output(judge_output: str) -> float:
    """Parse numerical score from judge's output"""
    if not isinstance(judge_output, str):
        logger.warning(f"Input passed to parse_judge_output is not a string: {type(judge_output)}")
        return DEFAULT_ERROR_SCORE
    try:
        # Extract JSON part: allow fenced blocks with or without language tag
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", judge_output, re.DOTALL)
        raw_json = None
        if json_match:
            raw_json = json_match.group(1)
        else:
            # Fallback: first JSON object found in text
            brace_match = re.search(r"\{[\s\S]*\}", judge_output)
            if brace_match:
                raw_json = brace_match.group(0)
        if not raw_json:
            logger.warning(f"Unable to find JSON block from judge output: {judge_output}")
            return DEFAULT_ERROR_SCORE

        judge_json = json.loads(raw_json)
        # Extract score robustly: support scalar, [score], or [[score]]
        val = judge_json.get("answer_score", DEFAULT_ERROR_SCORE)
        if isinstance(val, list):
            # flatten nested lists to find first numeric
            def first_number(x):
                if isinstance(x, (int, float)):
                    return float(x)
                if isinstance(x, str):
                    try:
                        return float(x)
                    except ValueError:
                        return None
                if isinstance(x, list) and x:
                    return first_number(x[0])
                return None
            score = first_number(val)
            if score is None:
                return DEFAULT_ERROR_SCORE
            return float(score)
        elif isinstance(val, (int, float)):
            return float(val)
        elif isinstance(val, str):
            return float(val)
        else:
            return DEFAULT_ERROR_SCORE
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
    # Be tolerant of different dataset schemas
    response_reference = data.get('response_reference', data.get('response_reference_translate', ''))
    if 'T1' in prompt_id:
        akshare_ticker = data.get('akshare_ticker', '')
        # Fallback tag inference when missing
        tag = data.get('tags')
        if not tag:
            if data.get('akshare_ticker') or data.get('yfinance_ticker') or data.get('wind_ticker'):
                tag = 'Stock'
            else:
                tag = 'Index'
        method = data.get('method', None)
        
        # Add error handling for data fetching
        try:
            ground_truth = fetch_single(akshare_ticker, tag, method)
        except Exception as e:
            logger.warning(f"Failed to fetch ground truth data for {akshare_ticker}: {e}")
            # Use fallback ground truth if available in data
            ground_truth = data.get('ground_truth', 'Data unavailable due to network error')

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
    try:
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
        logger.info(f"response_reference: {data.get('response_reference', data.get('response_reference_translate', 'N/A'))}")
        logger.info(f"model_response: {data.get('dialogues', [])[0].get('model_response', 'N/A')}")
    
        for dialogue in data.get("dialogues", []):
            prompt_id = dialogue.get("prompt_id", "")
            
            # If this prompt_id is in eval_id list, then evaluation is needed
            prompt = data["prompt"]
            model_response = dialogue["model_response"]
            judge_system_prompt = data["judge_system_prompt"]
            
            try:
                judge_user_input = get_judge_user_input(data, model_response)
            except Exception as e:
                logger.error(f"Failed to prepare judge input for {prompt_id}: {e}")
                continue

            # If necessary information is missing, skip this evaluation
            if not model_response:
                logger.warning(f"Dialog {prompt_id} lacks necessary evaluation information, skipping")
                continue
            
            # Evaluate response with error handling
            try:
                evaluation = evaluate_response(judge_user_input, model, judge_system_prompt)
            except Exception as e:
                logger.error(f"Evaluation failed for {prompt_id}: {e}")
                evaluation = {"judge_response": f"Error: {str(e)}", "score": DEFAULT_ERROR_SCORE}
            
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
            
            # Update non-TS scores (exclude error scores and T1 time-sensitive tasks)
            if evaluation["score"] != DEFAULT_ERROR_SCORE and not prompt_id.startswith("(T1)"):
                non_ts_total_score += evaluation["score"]
                non_ts_valid_evals += 1
        
        logger.info(f"Evaluation completed {prompt_id}: score {evaluation['score']}")
    
        # Calculate total accuracy
        if valid_evals > 0:
            # Save the total accuracy of all evaluations (including TS) as the original accuracy
            results["original_accuracy"] = total_score / valid_evals
            
            # Use the accuracy of non-TS evaluations as the main accuracy
            if non_ts_valid_evals > 0:
                results["accuracy"] = non_ts_total_score / non_ts_valid_evals
            else:
                # If no valid non-TS evaluations, return None to indicate no valid data
                results["accuracy"] = None
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
    
    except Exception as e:
        logger.error(f"Critical error in process_file: {e}")
        # Return minimal result structure with error
        return {
            "prompt_id": data.get('prompt_id', ['unknown']),
            "evaluations": [],
            "accuracy": 0.0,
            "error": str(e)
        }


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
    model = select_model(args.model_name, api_key=args.api_key)

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
                
                logger.info(f"Processed record {i+1}/{len(data)}, accuracy: {result.get('accuracy', 'N/A')}")
                
            # Calculate overall accuracy
            overall_accuracy = 0.0
            total_valid_scores = 0
            total_score_sum = 0.0
            
            for result in all_results:
                accuracy = result.get("accuracy")
                # Only include records with valid accuracy (not None and >= 0)
                if accuracy is not None and accuracy >= 0:
                    total_score_sum += accuracy
                    total_valid_scores += 1
                    
            overall_accuracy = total_score_sum / total_valid_scores if total_valid_scores > 0 else 0.0
            
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

