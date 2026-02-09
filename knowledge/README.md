# CPET 临床知识库

本目录存放 CPET 相关的专业知识文档，用于 RAG 检索增强生成。

## 支持的文件格式

- `.md` - Markdown 文档
- `.txt` - 纯文本文档
- `.pdf` - PDF 文档（需安装 pypdf）
- `.json` - JSON 知识库

## 目录结构

```
knowledge/
├── guidelines/      # 临床指南
├── indicators/      # 指标解读
├── protocols/       # 运动方案
└── references/      # 参考文献
```

## 索引知识库

```bash
# 使用 CLI 工具索引
python -m backend.rag.cli index knowledge/

# 或在 Python 中
from backend.rag import KnowledgeIndexer
indexer = KnowledgeIndexer("./data/vector_db")
indexer.index_directory("knowledge/")
```

## 查询知识库

```python
from backend.rag import KnowledgeRetriever
retriever = KnowledgeRetriever("./data/vector_db")
results = retriever.retrieve("VO2peak 正常值是多少")
```
