# CLAUDE.md

基于大语言模型的思维链推理（Chain-of-Thought Reasoning）实验项目。

## 项目简介

本项目基于 chatgpt 或开源 LLM（Qwen、LLaMA、vicuna 等），进行思维链推理的进阶探索，包括：

- 基础 COT、Self-Consistency、Step-Aware Verifier 等策略
- 检索增强（RAG）赋能 COT
- Multi-Agent Debate 协作推理
- BONUS: 借鉴 Harness Engineering 设计思想，系统化实现与管理 CoT 策略

数据集：AQuA（Algebraic Word Problems）及其他下游任务

## Startup Workflow

1. **确认工作目录**：`pwd`
2. **阅读本文档**完整内容
3. **运行 `./init.sh`** 验证环境
4. **阅读 `feature_list.json`** 查看当前功能状态
5. **选择一项未完成的功能**开始实现

## Working Rules

- **一次一个策略**：从 `feature_list.json` 中选择一项未完成的功能
- **必须验证**：每次实验后必须运行评估并记录结果
- **更新状态**：结束会话前更新 `progress.md` 和 `feature_list.json`
- **保持范围**：不修改与当前功能无关的文件
- **实验可复现**：所有配置（模型、prompt、策略）必须可追踪

## 项目结构

```
.
├── data/                   # 数据集（AQuA 等）
├── prompts/                # COT 策略 prompt 模板
├── strategies/             # COT 策略实现
│   ├── base_cot.py
│   ├── self_consistency.py
│   ├── step_verifier.py
│   └── multi_agent_debate.py
├── tasks/                  # 任务环境定义
│   ├── aqua_task.py
│   └── agentic_task.py
├── models/                 # LLM 接口封装
├── eval/                   # 评估指标与工具
├── experiments/            # 实验记录与结果
│   └── runs/
├── harness.py              # 实验管理主入口
├── CLAUDE.md               # 本文件
├── feature_list.json       # 功能状态追踪
├── progress.md             # 会话进度日志
├── session-handoff.md      # 多会话交接
└── init.sh                 # 环境验证脚本
```

## Definition of Done

一个功能完成当且仅当：

- [ ] 目标行为已实现（策略代码 + prompt 模板）
- [ ] 在 AQuA 验证集上运行并通过评估
- [ ] 实验结果记录在 `experiments/runs/` 中
- [ ] `feature_list.json` 和 `progress.md` 已更新
- [ ] 代码可通过 `./init.sh` 验证

## 验证命令

```bash
# 完整验证
./init.sh

# 运行单次实验示例
python harness.py --strategy base_cot --dataset aqua --n_samples 100

# 评估实验结果
python eval/evaluate.py --run_id <run_id>
```

## 关键技术参考

- Self-Consistency: https://arxiv.org/abs/2203.11171
- Step-Aware Verifier: https://arxiv.org/abs/2310.15123
- RAG + COT: https://arxiv.org/abs/2212.09095
- Multi-Agent Debate: https://arxiv.org/abs/2305.14325
- Harness Engineering: https://github.com/walkinglabs/learn-harness-engineering
