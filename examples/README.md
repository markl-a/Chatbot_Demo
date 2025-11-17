# 實際案例集合

本目錄包含了醫療聊天機器人的多個實際應用案例，涵蓋從基礎使用到進階應用的完整場景。

## 📁 目錄結構

```
examples/
├── 01_basic_usage/              # 基礎使用案例（3個）
├── 02_advanced_applications/    # 進階應用案例（3個）
├── 03_domain_specific/          # 專業領域案例（3個）
└── 04_integration_deployment/   # 整合部署案例（3個）
```

## 📋 案例清單

### 1. 基礎使用案例 (01_basic_usage/)

| 編號 | 檔案名 | 說明 | 難度 |
|------|--------|------|------|
| 1.1 | `simple_chat.py` | 簡單的命令行對話示例 | ⭐ |
| 1.2 | `api_call.py` | REST API 調用示例 | ⭐ |
| 1.3 | `config_usage.py` | 自定義配置參數使用 | ⭐ |

### 2. 進階應用案例 (02_advanced_applications/)

| 編號 | 檔案名 | 說明 | 難度 |
|------|--------|------|------|
| 2.1 | `batch_processing.py` | 批量問題處理 | ⭐⭐ |
| 2.2 | `multi_turn_conversation.py` | 多輪對話管理 | ⭐⭐ |
| 2.3 | `performance_optimization.py` | 推理性能優化 | ⭐⭐⭐ |

### 3. 專業領域案例 (03_domain_specific/)

| 編號 | 檔案名 | 說明 | 難度 |
|------|--------|------|------|
| 3.1 | `cardiovascular_consultation.py` | 心血管疾病諮詢 | ⭐⭐ |
| 3.2 | `respiratory_system.py` | 呼吸系統疾病處理 | ⭐⭐ |
| 3.3 | `emergency_detection.py` | 緊急狀況檢測與處理 | ⭐⭐⭐ |

### 4. 整合部署案例 (04_integration_deployment/)

| 編號 | 檔案名 | 說明 | 難度 |
|------|--------|------|------|
| 4.1 | `docker_deployment.py` | Docker 容器化部署腳本 | ⭐⭐ |
| 4.2 | `monitoring_logging.py` | 監控與日誌記錄 | ⭐⭐ |
| 4.3 | `security_best_practices.py` | 安全最佳實踐示例 | ⭐⭐⭐ |

## 🚀 快速開始

### 前置需求

確保已安裝專案依賴：

```bash
pip install -e .
```

### 運行案例

每個案例都可以獨立運行：

```bash
# 基礎案例
python examples/01_basic_usage/simple_chat.py

# 進階案例
python examples/02_advanced_applications/batch_processing.py

# 領域案例
python examples/03_domain_specific/cardiovascular_consultation.py

# 部署案例
python examples/04_integration_deployment/monitoring_logging.py
```

## 📚 學習路徑

### 初學者路徑
1. 從 `01_basic_usage/simple_chat.py` 開始
2. 學習 `01_basic_usage/api_call.py` 了解 API 使用
3. 嘗試 `02_advanced_applications/multi_turn_conversation.py`

### 進階開發者路徑
1. 研究 `02_advanced_applications/performance_optimization.py`
2. 探索 `03_domain_specific/` 中的領域應用
3. 學習 `04_integration_deployment/` 中的部署方案

### 生產環境路徑
1. 掌握 `04_integration_deployment/docker_deployment.py`
2. 實施 `04_integration_deployment/monitoring_logging.py`
3. 應用 `04_integration_deployment/security_best_practices.py`

## 💡 使用建議

- **閱讀代碼註釋**：每個案例都包含詳細的中文註釋
- **修改參數**：嘗試調整溫度、最大長度等參數觀察效果
- **組合使用**：可以將多個案例的技巧組合到實際專案中
- **參考文檔**：配合主 README.md 閱讀以獲得完整理解

## 🔗 相關資源

- [主 README](../README.md)
- [API 文檔](../docs/API.md)
- [配置指南](../configs/config.yaml)
- [Jupyter Notebooks](../notebooks/)

## 🤝 貢獻

歡迎提交新的實際案例！請確保：
- 代碼清晰且有詳細註釋
- 包含完整的使用說明
- 測試過可以正常運行
- 遵循專案的代碼風格

## 📝 授權

所有案例遵循專案的 MIT 授權條款。
