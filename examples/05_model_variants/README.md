# 多模型和 RAG 系統使用範例 🚀

這個目錄包含了醫療聊天機器人的進階使用範例，展示如何使用不同模型、RAG 系統和生產級功能。

## 📚 範例列表

### 1. 不同模型使用範例 (`01_different_models.py`)

展示如何使用不同的中文和醫療領域模型。

**包含的模型：**
- 🇹🇼 **TAIDE-LX-8B-Chat** - 繁體中文，台灣在地化
- 🇹🇼 **Breeze-7B-Instruct** - MediaTek 開發，繁體中文
- 🇹🇼 **Taiwan-LLM-7B** - 台大開發，繁體中文訓練
- 🇨🇳 **Qwen-7B-Chat** - 阿里巴巴開發，醫療知識豐富
- 🇨🇳 **ChatGLM3-6B** - 清華開發，對話能力強

**功能亮點：**
- 7 個完整範例
- 模型比較和選擇建議
- 量化和記憶體優化技巧
- 自定義微調流程

**運行方式：**
```bash
python examples/05_model_variants/01_different_models.py
```

---

### 2. RAG 系統完整指南 (`02_rag_complete_guide.py`)

完整的檢索增強生成（RAG）系統使用指南。

**包含的主題：**
1. **基礎 RAG 系統** - 入門使用
2. **RAG + 生成器** - 整合語言模型
3. **知識庫管理** - 文檔添加和管理
4. **進階功能** - 多種索引類型（Flat/IVF/HNSW）
5. **RAG 評估** - 質量評估方法
6. **多語言支援** - 跨語言檢索
7. **最佳實踐** - 生產環境建議

**功能亮點：**
- 7 個詳細範例
- FAISS 索引優化
- 多種嵌入模型支援
- 性能調優建議

**運行方式：**
```bash
python examples/05_model_variants/02_rag_complete_guide.py
```

---

### 3. 組合功能範例 (`03_combined_features.py`)

展示如何組合使用多種功能構建生產級系統。

**組合功能：**
1. **RAG + 安全過濾** - 安全可靠的知識檢索
2. **RAG + 快取機制** - 提升性能和響應速度
3. **RAG + 錯誤處理** - 穩定的生產系統
4. **RAG + 性能監控** - 可觀測的系統運行
5. **多模型 RAG** - 靈活的模型選擇
6. **完整流水線** - 企業級解決方案

**功能亮點：**
- 6 個實用範例
- 快取實現（記憶體 + Redis）
- 性能監控和指標
- 完整的錯誤處理

**運行方式：**
```bash
python examples/05_model_variants/03_combined_features.py
```

---

### 4. 實際應用場景 (`04_real_world_scenarios.py`)

真實醫療場景的完整實現。

**應用場景：**

#### 場景 1：虛擬診所 24/7 線上諮詢助手
- 臨床指南載入
- 緊急情況檢測
- 諮詢歷史記錄
- 免責聲明管理

#### 場景 2：個人化健康教育平台
- 用戶興趣檔案
- 個人化內容推薦
- 學習歷史追蹤
- 多類別內容管理

#### 場景 3：智能用藥助手
- 藥物資料庫
- 用藥資訊查詢
- 安全警告提示
- 用法用量指南

#### 場景 4：AI 症狀檢查器
- 症狀資料庫
- 症狀匹配分析
- 嚴重程度評估
- 就醫建議

**功能亮點：**
- 4 個完整場景
- 真實業務邏輯
- 安全和合規考量
- 可直接用於生產

**運行方式：**
```bash
python examples/05_model_variants/04_real_world_scenarios.py
```

---

### 5. 生產環境部署 (`05_production_deployment.py`)

生產環境部署的最佳實踐和配置。

**部署方案：**
1. **Docker 容器化** - 完整 Dockerfile 和 docker-compose
2. **Kubernetes 部署** - 雲端原生部署
3. **負載平衡** - Nginx 配置和高可用性
4. **快取策略** - 多層快取架構
5. **監控告警** - Prometheus + Grafana
6. **安全實踐** - 認證、授權、加密

**功能亮點：**
- 6 個部署範例
- 完整配置文件
- 監控和告警規則
- 安全最佳實踐

**運行方式：**
```bash
python examples/05_model_variants/05_production_deployment.py
```

---

## 🎯 快速開始

### 環境準備

```bash
# 1. 安裝依賴
pip install -r requirements.txt

# 2. 設置環境變數（可選）
cp .env.example .env
# 編輯 .env 文件，設置 HuggingFace token 等

# 3. 下載模型（首次運行時自動下載）
```

### 運行所有範例

```bash
# 按順序運行所有範例
for script in examples/05_model_variants/*.py; do
    echo "Running $script..."
    python "$script"
    echo "---"
done
```

### 選擇性運行

```bash
# 只運行 RAG 範例
python examples/05_model_variants/02_rag_complete_guide.py

# 只運行真實場景
python examples/05_model_variants/04_real_world_scenarios.py
```

---

## 📖 詳細文檔

### 模型選擇指南

| 模型 | 語言 | 大小 | 特點 | 適用場景 |
|------|------|------|------|----------|
| TAIDE-LX-8B | 繁體中文 | 8B | 台灣在地化 | 台灣醫療諮詢 |
| Breeze-7B | 繁體中文 | 7B | MediaTek 開發 | 一般醫療對話 |
| Taiwan-LLM-7B | 繁體中文 | 7B | 台大開發 | 學術醫療 |
| Qwen-7B | 簡體中文 | 7B | 醫療知識豐富 | 中文醫療知識 |
| ChatGLM3-6B | 中文 | 6B | 對話能力強 | 多輪對話 |

### RAG 配置建議

#### 嵌入模型選擇
- **多語言**：`paraphrase-multilingual-MiniLM-L12-v2`
- **中文優化**：`BAAI/bge-large-zh-v1.5`
- **輕量級**：`sentence-transformers/all-MiniLM-L6-v2`

#### 索引類型選擇
- **小型知識庫（< 10K 文檔）**：Flat 索引
- **中型知識庫（10K-1M）**：IVF 索引
- **大型知識庫（> 1M）**：HNSW 索引

#### 參數調優
```python
# 推薦配置
MedicalRetriever(
    top_k=3,              # 返回 top 3 文檔
    score_threshold=0.6,  # 最低相似度 0.6
)

# 文檔分塊
chunk_size=512,  # 512 tokens
overlap=50,      # 10% 重疊
```

---

## 🔧 常見問題

### Q1: 模型下載很慢怎麼辦？

A: 可以使用鏡像站點或手動下載：
```bash
# 使用 HuggingFace 鏡像（中國大陸）
export HF_ENDPOINT=https://hf-mirror.com

# 或手動下載後指定本地路徑
python -c "from transformers import AutoModel; AutoModel.from_pretrained('./local_model')"
```

### Q2: 記憶體不足怎麼辦？

A: 使用量化技術：
```python
# 8-bit 量化
config.model.load_in_8bit = True

# 4-bit 量化（更省記憶體）
config.model.load_in_4bit = True
```

### Q3: RAG 檢索效果不好？

A: 嘗試以下優化：
1. 調整 `score_threshold`（降低門檻）
2. 增加 `top_k`（返回更多結果）
3. 優化文檔分塊策略
4. 使用更好的嵌入模型
5. 添加更多相關知識

### Q4: 如何提升響應速度？

A: 多層優化：
1. 使用快取（記憶體 + Redis）
2. 批次處理
3. 模型量化
4. GPU 加速
5. 負載平衡

---

## 📊 性能基準

### 硬體需求

| 配置 | CPU | 記憶體 | GPU | 適用場景 |
|------|-----|--------|-----|----------|
| 最低 | 4 核 | 8GB | - | 測試開發 |
| 推薦 | 8 核 | 16GB | RTX 3060 12GB | 小規模部署 |
| 生產 | 16 核 | 32GB+ | A100 40GB | 大規模部署 |

### 性能指標

| 指標 | 8-bit 量化 | 完整精度 |
|------|-----------|---------|
| 載入時間 | ~30s | ~60s |
| 記憶體使用 | ~8GB | ~16GB |
| 推理速度 | ~50 tokens/s | ~30 tokens/s |
| GPU 記憶體 | ~6GB | ~12GB |

---

## 🤝 貢獻

歡迎提交問題和改進建議！

1. Fork 這個專案
2. 創建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 開啟 Pull Request

---

## 📄 授權

MIT License - 詳見 [LICENSE](../../LICENSE) 文件

---

## 🔗 相關資源

### 官方文檔
- [專案主 README](../../README.md)
- [改進文檔](../../docs/PROJECT_ENHANCEMENTS_2025.md)
- [貢獻指南](../../CONTRIBUTING.md)

### 模型資源
- [TAIDE 官網](https://taide.tw/)
- [Breeze GitHub](https://github.com/MediaTek-Research/Breeze-7B)
- [Taiwan-LLM](https://github.com/MiuLab/Taiwan-LLM)
- [Qwen](https://github.com/QwenLM/Qwen)
- [ChatGLM](https://github.com/THUDM/ChatGLM3)

### 技術文檔
- [FAISS Documentation](https://github.com/facebookresearch/faiss/wiki)
- [Sentence Transformers](https://www.sbert.net/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

## 📞 聯繫方式

如有問題或建議，請：
- 開啟 [GitHub Issue](https://github.com/markl-a/Chatbot_Demo/issues)
- 查看 [FAQ](../../docs/FAQ.md)

---

**最後更新**: 2025-11-18
**範例版本**: v1.0.0
**專案版本**: v0.3.0
