# Changelog

本文檔記錄專案的所有重要變更。

格式基於 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/)，
版本號遵循 [Semantic Versioning](https://semver.org/lang/zh-TW/)。

## [0.2.0] - 2025-01-XX

### Added
- 完整重構專案架構，採用模組化設計
- 新增 FastAPI REST API 服務
- 新增 Gradio 網頁介面
- 新增命令列介面 (CLI) 工具
- 新增 Docker 和 docker-compose 支援
- 新增完整的配置管理系統 (YAML + 環境變數)
- 新增日誌系統 (loguru)
- 新增資料處理 Pipeline
- 新增模型管理系統
- 新增 LoRA 訓練模組
- 新增推理生成器
- 新增單元測試
- 新增 CI/CD workflow (GitHub Actions)
- 新增完整的專案文檔

### Changed
- 將 Jupyter Notebook 代碼模組化為 Python 套件
- 改善錯誤處理和異常管理
- 更新依賴套件到最新穩定版本
- 重寫 README 提供詳細使用說明

### Fixed
- 修復 API token 硬編碼的安全問題
- 修復文本清理和後處理問題

## [0.1.0] - 2024-08-13

### Added
- 初始版本
- 基於 TAIDE-LX-7B-Chat 的醫療聊天機器人
- Breeze-7B-Instruct 替代模型支援
- Jupyter Notebook 訓練和推理範例
- 基本的 Gradio 介面
- 模型量化和 GGUF 轉換
- LLaMA Factory 微調範例
