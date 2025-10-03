<div align="center">
<h1 style="font-family: 'Century Gothic', Arial, sans-serif; font-size: 2.2em; font-weight: bold; color: #2c3e50; margin: 20px 0;">
FinSearchComp: Towards a Realistic, Expert-Level Evaluation of Financial Search and Reasoning
</h1>
<p align="center">
  <a href="https://github.com/randomtutu/FinSearchComp/stargazers">
    <img src="https://img.shields.io/github/stars/randomtutu/FinSearchComp?style=social"></a>
  <a href="https://randomtutu.github.io/FinSearchComp/">
    <img src="https://img.shields.io/badge/FinSearchComp-Project%20Page-green"></a>
  <a href="https://arxiv.org/abs/2509.13160">
    <img src="https://img.shields.io/badge/FinSearchComp-Arxiv-yellow"></a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-Apache--2.0-blue"></a>
</p>
</div>

<div align="center" style="margin: 15px 0;">
<p style="font-family: 'Century Gothic', Arial, sans-serif; font-size: 1.1em; font-weight: bold; color: #34495e; margin: 0;">
<span style="color: #2c3e50;">ByteDance Seed</span>&nbsp;&nbsp;&nbsp;&nbsp;•&nbsp;&nbsp;&nbsp;&nbsp;<span style="color: #2c3e50;">Columbia Business School</span>
</p>
</div>

---

## 🔔 Introduction

<p align="center">
  <img src="/docx/assets/performance.png" alt="FinSearchComp Performance" style="width: 800px;"> 
</p>

Realistic decision-making tasks require three core skills: finding the right signals, checking and reconciling sources, and turning them into grounded judgments under time pressure. We provide a foundational, end-to-end evaluation infrastructure—an open finance benchmark with tasks for time-sensitive fetching, historical lookup, and multi-source investigation—that measures these skills directly.

---

## ⚙️ Installation

To install the required packages:

```bash
# we prefer to run the code in a conda environment
git clone git@github.com:randomtutu/FinSearchComp.git
cd FinSearchComp
conda create -n finsearchcomp python=3.10
conda activate finsearchcomp
pip install -r finsearchcomp/requirements.txt
```

---

## 🚀 Quick Start

You can quick start like this:

1️⃣ Configure the `finsearchcomp/config/config.yaml` with your API keys (e.g., Gemini).

2️⃣ Process a specific data file:

```bash
python finsearchcomp/chat/chat.py \
  --model_name gemini-2.5-flash \
  --input_file ../data/finsearchcomp_data.json \
  --output_path result/chat-result/chat.json \
  --limit 1
```
> limit=0 means process all questions in the data file.

3️⃣ Conduct evaluation:

```bash
python finsearchcomp/eval/eval.py \
  --model_name gemini-2.5-flash \
  --input finsearchcomp/result/chat-result/chat.json \
  --output finsearchcomp/result/eval-result/eval.json
```

---

## 🛠️ Project Structure

### eval

* `eval.py`: Main evaluation script, calculates metrics.

### chat

* `chat.py`: Processes full dataset for FinSearchComp.  

### data

* `*.json`: JSON files with FinSearchComp data.

### config

* `config.yaml`: API keys and model settings.
* `config_wrapper.py`: Helper for loading configurations.

### result

* `chat-result/`: Dialogue outputs (e.g., `demo.json`).
* `eval-result/`: Evaluation results.

### models

* `deepseek.py`: Implement of dpsk models.
* `openai_api.py`: Implement of openai models.
* `gemini.py`: Implement of gemini models.

### logger
* `config.py`: logger config.
---

## 📄 Citation

```bibtex
@misc{hu2025finsearchcomprealisticexpertlevelevaluation,
      title={FinSearchComp: Towards a Realistic, Expert-Level Evaluation of Financial Search and Reasoning}, 
      author={Liang Hu and Jianpeng Jiao and Jiashuo Liu and Yanle Ren and Zhoufutu Wen and Kaiyuan Zhang and Xuanliang Zhang and Xiang Gao and Tianci He and Fei Hu and Yali Liao and Zaiyuan Wang and Chenghao Yang and Qianyu Yang and Mingren Yin and Zhiyuan Zeng and Ge Zhang and Xinyi Zhang and Xiying Zhao and Zhenwei Zhu and Hongseok Namkoong and Wenhao Huang and Yuwen Tang},
      year={2025},
      eprint={2509.13160},
      archivePrefix={arXiv},
      primaryClass={cs.LG},
      url={https://arxiv.org/abs/2509.13160}, 
}
```