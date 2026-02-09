# Xinhui - 心慧智问

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
xinhui/
├── .opencode/
│   ├── agents/           # OpenCode Agent 定义
│   └── opencode.jsonc    # OpenCode 配置
├── backend/              # FastAPI 后端
│   ├── api.py         # 主 API
│   ├── inference/        # AT/VO2 预测模型
│   ├── prescription/     # 运动处方生成
│   ├── reports/          # PDF 报告生成
│   └── realtime/         # WebSocket 实时数据
├── frontend/             # React 前端
│   ├── src/              # 源码
│   └── dist/             # 构建产物（被后端托管）
├── tools/                # 独立工具
│   ├── index.html        # AT 标注工具
│   └── replay.html       # AT 回放工具
└── pyproject.toml
```

## 快速开始

### 1. 环境配置

```bash
cp .env.example .env
# 编辑 .env 填入 API Key 和数据路径
# 生产环境务必设置强随机的 XINHUI_JWT_SECRET
```

### 2. 安装依赖

```bash
# Python 后端
pip install -e .

# 前端
cd frontend && npm install
```

### 3. 构建前端

```bash
cd frontend && npm run build
```

### 4. 启动服务

```bash
# 启动后端（同时托管前端）
cd backend && uvicorn api:app --reload --port 8000
```

访问：
- **前端应用**: http://localhost:8000/app/
- **API 文档**: http://localhost:8000/api/docs
- **工具页面**: http://localhost:8000/tools/

说明：
- 现在 **必须注册/登录** 后才能使用智能体与数据接口。

### 开发模式

前后端分离开发：

```bash
# 终端 1: 启动后端
cd backend && uvicorn api:app --reload --port 8000

# 终端 2: 启动前端开发服务器
cd frontend && npm run dev

# 或者让后端代理到前端开发服务器
FRONTEND_DEV_SERVER=http://localhost:5173 uvicorn api:app --reload --port 8000
```

## URL 路由

| 路径 | 内容 |
|------|------|
| `/` | 重定向到 `/app/` |
| `/app/` | 前端应用 |
| `/tools/` | AT 标注/回放工具 |
| `/api/` | REST API |
| `/api/docs` | Swagger 文档 |
| `/api/ws/` | WebSocket |

## 数据域与联动

后端按数据域存储与提供接口，便于 iOS / Web / Agent 共享同一份“事实数据”：

- `HealthKit`（日常/运动/健康数据同步）：`/api/healthkit/*`（数据落地 `data/healthkit/<device_id>/`）
- `Diet`（拍照识别 + 饮食记账）：`/api/diet/*`（数据落地 `data/diet/<device_id>/`）
- `Clinical`（临床记录，CPET 报告是一种临床记录）：`/api/clinical/*`（数据落地 `data/clinical/`）
- `Lifestyle`（聚合层：把 Diet + HealthKit 按天汇总给看板/智能体）：`/api/lifestyle/*`

## 技术栈

- **后端**: FastAPI + Python 3.10+
- **前端**: React 18 + TypeScript + Vite + Tailwind CSS
- **AI Agent**: OpenCode + Qwen (qwen3-max)
- **模型**: PaceFormer (AT 预测)

## License

MIT
# huixin
