# 心衡智问 - Heartwise

临床运动评估与健康平台

## 项目说明

本项目为 CPET（心肺运动试验）临床辅助系统，提供：
- CPET 报告智能解读
- 个体化运动处方生成
- 运动风险评估
- 营养与食疗建议

## 开发指南

### 后端开发

```bash
cd backend
uvicorn api_v2:app --reload --port 8000
```

### 前端开发

```bash
cd frontend
npm install
npm run dev
```

### OpenCode Agent 开发

Agent 定义在 `.opencode/agents/` 目录下，每个 `.md` 文件定义一个 Agent。

修改 Agent 后，重启 OpenCode 即可生效。

## 代码规范

- Python: Black + isort
- TypeScript: ESLint + Prettier
- 提交信息: Conventional Commits
