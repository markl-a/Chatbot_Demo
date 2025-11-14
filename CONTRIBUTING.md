# 貢獻指南

感謝您考慮為 Medical Chatbot 專案做出貢獻!

## 如何貢獻

### 回報問題

如果您發現了 bug 或有功能建議:

1. 先檢查 [Issues](https://github.com/markl-a/Chatbot_Demo/issues) 看是否已經有人提出
2. 如果沒有,請建立一個新的 issue
3. 請提供詳細的描述、重現步驟、預期行為等資訊

### 提交程式碼

1. Fork 這個專案
2. 建立您的功能分支 (`git checkout -b feature/AmazingFeature`)
3. 確保程式碼符合風格指南
4. 執行測試確保沒有問題
5. 提交您的變更 (`git commit -m 'Add some AmazingFeature'`)
6. 推送到分支 (`git push origin feature/AmazingFeature`)
7. 開啟一個 Pull Request

## 開發環境設置

```bash
# 克隆您的 fork
git clone https://github.com/YOUR_USERNAME/Chatbot_Demo.git
cd Chatbot_Demo

# 建立虛擬環境
python -m venv venv
source venv/bin/activate

# 安裝開發依賴
pip install -e ".[dev]"

# 安裝 pre-commit hooks
pre-commit install
```

## 程式碼風格

我們使用以下工具來確保程式碼品質:

- **Black**: 程式碼格式化
- **Ruff**: Linting
- **MyPy**: 型別檢查

執行檢查:

```bash
# 格式化程式碼
black src/

# Linting
ruff check src/

# 型別檢查
mypy src/
```

## 測試

請為新功能撰寫測試:

```bash
# 執行所有測試
pytest tests/

# 執行特定測試
pytest tests/test_config.py

# 產生覆蓋率報告
pytest tests/ --cov=src/medical_chatbot --cov-report=html
```

## 提交訊息規範

請使用清晰、描述性的提交訊息:

- `feat:` 新功能
- `fix:` Bug 修復
- `docs:` 文檔更新
- `style:` 程式碼格式調整
- `refactor:` 重構
- `test:` 測試相關
- `chore:` 其他雜項

範例:
```
feat: add support for multi-turn conversations
fix: resolve tokenizer padding issue
docs: update installation instructions
```

## Pull Request 檢查清單

在提交 PR 前,請確認:

- [ ] 程式碼已經過格式化 (black)
- [ ] 通過所有 linting 檢查 (ruff)
- [ ] 通過所有測試
- [ ] 新功能有相應的測試
- [ ] 文檔已更新 (如適用)
- [ ] 提交訊息清晰明瞭

## 授權

提交程式碼即表示您同意將您的貢獻以 MIT 授權釋出。
