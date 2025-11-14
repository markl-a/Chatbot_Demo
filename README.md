# Medical Chatbot 醫療聊天機器人 🏥

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

基於 TAIDE/Breeze 模型的中文醫療問答系統，使用 LoRA 微調技術訓練，提供專業的醫療諮詢服務。

![Demo Screenshot](./img/cover.png)

## ✨ 特色功能

- 🤖 **專業醫療模型**: 基於 TAIDE-LX-7B-Chat 和 Breeze-7B-Instruct 微調
- 🎯 **LoRA 微調**: 高效的參數高效微調技術
- 🚀 **多種部署方式**: FastAPI、Gradio、Docker、CLI
- 📦 **完整開發環境**: 包含訓練、推理、評估的完整流程
- 🔧 **靈活配置**: YAML 配置文件和環境變數支援
- 🐳 **容器化部署**: Docker 和 docker-compose 支援
- 📊 **日誌監控**: 完整的日誌和錯誤追蹤系統
- 🎨 **現代化 UI**: 美觀的 Gradio 網頁介面

## 📋 目錄

- [安裝](#安裝)
- [快速開始](#快速開始)
- [使用方式](#使用方式)
- [模型訓練](#模型訓練)
- [API 服務](#api-服務)
- [Docker 部署](#docker-部署)
- [專案結構](#專案結構)
- [配置說明](#配置說明)
- [開發指南](#開發指南)
- [授權條款](#授權條款)

## 🚀 安裝

### 環境需求

- Python 3.9+
- CUDA 11.8+ (如需 GPU 加速)
- 16GB+ RAM
- 20GB+ 磁碟空間

### 1. 克隆專案

```bash
git clone https://github.com/markl-a/Chatbot_Demo.git
cd Chatbot_Demo
```

### 2. 建立虛擬環境

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

### 3. 安裝依賴

```bash
# 基本安裝
pip install -r requirements.txt

# 或使用 pip editable 模式安裝
pip install -e .

# 安裝所有可選依賴
pip install -e ".[all]"
```

### 4. 配置環境變數

```bash
cp .env.example .env
# 編輯 .env 文件，填入您的 HuggingFace token
```

## ⚡ 快速開始

### 1. 互動式對話 (CLI)

```bash
python -m medical_chatbot.cli chat
```

### 2. 啟動 Gradio 網頁介面

```bash
python -m medical_chatbot.cli gradio
```

訪問 `http://localhost:7860` 使用網頁介面。

### 3. 啟動 FastAPI 服務

```bash
python -m medical_chatbot.cli serve
```

API 文檔: `http://localhost:8000/docs`

## 📖 使用方式

### CLI 命令

```bash
# 查看所有命令
python -m medical_chatbot.cli --help

# 訓練模型
python -m medical_chatbot.cli train --config configs/config.yaml

# 啟動 FastAPI 服務
python -m medical_chatbot.cli serve --host 0.0.0.0 --port 8000

# 啟動 Gradio 介面
python -m medical_chatbot.cli gradio --share

# 互動式對話
python -m medical_chatbot.cli chat

# 發送單一訊息
python -m medical_chatbot.cli chat --message "頭痛該怎麼辦？"
```

### Python API

```python
from medical_chatbot.utils.config import load_config
from medical_chatbot.models.model_manager import ModelManager
from medical_chatbot.inference.generator import MedicalChatGenerator

# 載入配置
config = load_config("configs/config.yaml")

# 載入模型
model_manager = ModelManager(
    model_name=config.model.base_model,
    peft_name=config.model.fine_tuned_model,
    token=config.hf_token,
)
tokenizer, model = model_manager.load()

# 建立生成器
generator = MedicalChatGenerator(
    model=model,
    tokenizer=tokenizer,
    system_prompt=config.prompts.system,
)

# 生成回應
response = generator.generate("每天肚子痛是什麼狀況？")
print(response)
```

### API 呼叫範例

```python
import requests

# 單輪對話
response = requests.post(
    "http://localhost:8000/chat",
    json={
        "message": "頭痛該怎麼辦？",
        "temperature": 0.15,
    }
)
print(response.json())

# 多輪對話
response = requests.post(
    "http://localhost:8000/conversation",
    json={
        "messages": [
            {"role": "system", "content": "你是一位專業的醫療人員。"},
            {"role": "user", "content": "我有高血壓"},
            {"role": "assistant", "content": "請問您目前有在服用藥物嗎？"},
            {"role": "user", "content": "有，但還是偶爾會頭暈"},
        ]
    }
)
print(response.json())
```

## 🎓 模型訓練

### 1. 準備資料集

資料集會自動下載，或手動下載到 `data/raw/MedText_zhtw.json`

### 2. 配置訓練參數

編輯 `configs/config.yaml` 調整訓練參數：

```yaml
training:
  num_train_epochs: 40
  per_device_train_batch_size: 64
  learning_rate: 0.00005
  # ... 其他參數
```

### 3. 開始訓練

```bash
python -m medical_chatbot.cli train --config configs/config.yaml
```

訓練完成後，模型會保存到 `models/checkpoints/` 目錄。

### 4. 評估模型

```python
from medical_chatbot.models.model_manager import ModelManager
from medical_chatbot.inference.generator import MedicalChatGenerator

# 載入訓練好的模型
model_manager = ModelManager(
    model_name="taide/TAIDE-LX-7B-Chat",
    peft_name="models/checkpoints/final",
)
tokenizer, model = model_manager.load()

# 測試生成
generator = MedicalChatGenerator(model, tokenizer)
response = generator.generate("測試問題")
```

## 🌐 API 服務

### FastAPI 端點

- `GET /`: 服務資訊
- `GET /health`: 健康檢查
- `POST /chat`: 單輪對話
- `POST /conversation`: 多輪對話

### API 文檔

啟動服務後訪問:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🐳 Docker 部署

### 使用 Docker Compose (推薦)

```bash
# 啟動 FastAPI 服務
docker-compose up medical-chatbot-api

# 啟動 Gradio 介面
docker-compose up medical-chatbot-gradio

# 同時啟動兩個服務
docker-compose up
```

### 使用 Docker

```bash
# 建立映像
docker build -t medical-chatbot .

# 運行容器
docker run -d \
  --name medical-chatbot \
  --gpus all \
  -p 8000:8000 \
  -e HF_TOKEN=your_token_here \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/models:/app/models \
  medical-chatbot
```

## 📁 專案結構

```
Chatbot_Demo/
├── configs/                 # 配置文件
│   └── config.yaml
├── data/                    # 資料目錄
│   ├── raw/                # 原始資料
│   └── processed/          # 處理後資料
├── docs/                    # 文檔
├── models/                  # 模型目錄
│   ├── checkpoints/        # 訓練檢查點
│   └── quantized/          # 量化模型
├── logs/                    # 日誌文件
├── notebooks/              # Jupyter Notebooks
├── scripts/                # 輔助腳本
├── src/                    # 原始碼
│   └── medical_chatbot/
│       ├── api/            # API 服務
│       │   ├── server.py   # FastAPI 服務器
│       │   └── gradio_app.py # Gradio 介面
│       ├── data/           # 資料處理
│       │   ├── dataset.py
│       │   └── preprocessor.py
│       ├── models/         # 模型管理
│       │   ├── model_manager.py
│       │   └── lora_trainer.py
│       ├── inference/      # 推理
│       │   └── generator.py
│       ├── utils/          # 工具
│       │   ├── config.py
│       │   └── logger.py
│       └── cli.py          # CLI 介面
├── tests/                  # 測試
├── .env.example           # 環境變數範例
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
└── README.md
```

## ⚙️ 配置說明

### 環境變數 (.env)

```bash
# HuggingFace Token
HF_TOKEN=your_token_here
HF_READ_TOKEN=your_read_token_here
HF_WRITE_TOKEN=your_write_token_here

# 模型配置
BASE_MODEL_NAME=taide/TAIDE-LX-7B-Chat
FINE_TUNED_MODEL_NAME=mark1098/TAIDE-LX-7B-Chat-Medical-Fintune

# 訓練配置
BATCH_SIZE=64
LEARNING_RATE=5e-5
NUM_EPOCHS=40

# API 配置
API_HOST=0.0.0.0
API_PORT=8000
```

### YAML 配置 (configs/config.yaml)

查看 `configs/config.yaml` 了解完整配置選項。

## 🛠️ 開發指南

### 安裝開發依賴

```bash
pip install -e ".[dev]"
```

### 程式碼格式化

```bash
# 使用 black 格式化
black src/

# 使用 ruff 檢查
ruff check src/
```

### 執行測試

```bash
pytest tests/
```

### 型別檢查

```bash
mypy src/
```

## 📊 使用的技術棧

- **深度學習框架**: PyTorch, Transformers, PEFT
- **API 框架**: FastAPI, Gradio
- **配置管理**: Pydantic, PyYAML, python-dotenv
- **日誌**: Loguru
- **CLI**: Typer, Rich
- **容器化**: Docker, docker-compose
- **程式碼品質**: Black, Ruff, MyPy, Pytest

## 🤝 參考資料

本專案使用以下開源資源:

- [TAIDE-LX-7B-Chat](https://huggingface.co/taide/TAIDE-LX-7B-Chat) - 基礎模型
- [Breeze-7B-Instruct](https://huggingface.co/MediaTek-Research/Breeze-7B-Instruct-v1_0) - 替代模型
- [MedText_zhtw](https://huggingface.co/datasets/ChenWeiLi/Medtext_zhtw) - 醫療資料集

## ⚠️ 免責聲明

本系統提供的資訊僅供參考，不構成專業醫療建議。如有任何健康疑慮，請務必諮詢合格的醫療專業人員。

## 📄 授權條款

本專案採用 [MIT License](LICENSE) 授權。

## 🙏 致謝

感謝 TAIDE、MediaTek Research 和所有開源社群的貢獻者。

## 📮 聯絡方式

- GitHub: [@markl-a](https://github.com/markl-a)
- Issues: [GitHub Issues](https://github.com/markl-a/Chatbot_Demo/issues)

---

Made with ❤️ by Mark L
