# Heartwise - 心衡智问

临床运动评估与健康平台

## 功能模块

| Agent | 功能 | 描述 |
|-------|------|------|
| `report` | CPET 报告分析 | 解读心肺运动试验报告、关键指标分析 |
| `analysis` | 运动数据分析 | CPET/手表数据分析与趋势摘要 |
| `prescription` | 运动处方生成 | 个体化运动处方（FITT 原则） |
| `health` | 运动风险评估 | 风险分层与安全建议 |
| `diet` | 营养与食疗 | 营养方向与食疗建议 |
| `clinical` | 临床综合 | 综合问答与决策辅助 |

## 项目结构

```
heartwise/
├── .opencode/
│   ├── agents/           # OpenCode Agent 定义
│   │   ├── report.md     # CPET 报告分析
│   │   ├── analysis.md   # 运动数据分析
│   │   ├── prescription.md # 运动处方
│   │   ├── health.md     # 风险评估
│   │   ├── diet.md       # 营养食疗
│   │   └── clinical.md   # 临床综合
│   └── opencode.jsonc    # OpenCode 配置
├── backend/              # FastAPI 后端
│   ├── inference/        # AT/VO2 预测模型
│   ├── prescription/     # 运动处方生成
│   ├── reports/          # PDF 报告生成
│   └── realtime/         # WebSocket 实时数据
├── frontend/             # React 前端
│   └── src/
│       ├── components/   # UI 组件
│       └── App.tsx       # 主应用
├── tools/                # 独立工具
│   ├── index.html        # AT 标注工具
│   └── replay.html       # AT 回放工具
├── pyproject.toml        # Python 项目配置
└── README.md
```

## 快速开始

### 1. 环境配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 填入 API Key 和数据路径
vim .env
```

### 2. 安装依赖

```bash
# Python 后端
pip install -e .

# 前端
cd frontend && npm install
```

### 3. 启动服务

```bash
# 启动后端 API
cd backend && uvicorn api_v2:app --reload --port 8000

# 启动前端开发服务器
cd frontend && npm run dev
```

### 4. 使用 OpenCode Agent

```bash
# 在 heartwise 目录下启动 opencode
cd /home/cheng/workspace/heartwise
opencode

# 选择 Agent 进行对话
# - report: CPET 报告分析
# - prescription: 运动处方
# - diet: 营养建议
# ...
```

## 技术栈

- **后端**: FastAPI + Python 3.10+
- **前端**: React 18 + TypeScript + Vite + Tailwind CSS
- **AI Agent**: OpenCode + Qwen (qwen3-max)
- **模型**: PaceFormer (AT 预测)

## API 端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/v2/health` | GET | 健康检查 |
| `/api/v2/agent/ask` | POST | AI 问答 |
| `/api/v2/predict/at` | POST | AT 预测 |
| `/api/v2/predict/vo2peak` | POST | VO2 Peak 预测 |
| `/api/v2/prescription/generate` | POST | 生成运动处方 |
| `/api/v2/prescription/pdf` | POST | 生成处方 PDF |
| `/api/v2/reports/generate` | POST | 生成报告 PDF |
| `/api/ws/realtime/{session_id}` | WebSocket | 实时数据流 |

## 环境变量

| 变量 | 说明 |
|------|------|
| `QWEN_API_KEY` | 通义千问 API Key |
| `CPET_DATA_FILE` | CPET 数据文件路径 (.h5) |
| `CPET_PACE_CONFIG` | PaceFormer 配置文件 |
| `CPET_PACE_CHECKPOINT` | PaceFormer 模型权重 |
| `OPENCODE_BASE_URL` | OpenCode 服务地址 |

## License

MIT
