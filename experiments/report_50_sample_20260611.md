# COT 推理实验报告：50 样本大规模测试（n=50）

> **实验日期**：2026-06-10 ~ 2026-06-11
> **模型**：deepseek-v4-flash（DMXAPI）
> **数据集**：AQuA（Algebraic Word Problems）test 集前 50 条样本
> **实验目的**：在更大样本量上对比 5 种 CoT 策略的准确率与效率

---

## 1. 实验配置

| 配置项 | 值 |
|---|---|
| API 端点 | https://www.dmxapi.cn/v1 |
| 模型 | deepseek-v4-flash |
| 温度系数 | 0.7 |
| 最大 token | 1024 |
| 数据集 | AQuA test |
| 样本量 | **50 条/策略** |

### 1.1 各策略参数

| 策略 | 关键参数 |
|---|---|
| base_cot | 无额外参数 |
| rag_cot | top_k=3 |
| self_consistency | n_paths=3 |
| multi_agent_debate | n_agents=3, n_rounds=2 |
| step_verifier | n_paths=3 |

---

## 2. 核心结果汇总

### 2.1 准确率与效率对比

| 策略 | 正确数 | 准确率 | 总耗时 | 平均耗时/条 | 平均步数 | 平均 Token |
|---|---|---|---|---|---|---|
| base_cot | 46/50 | 92.00% | 4.4 min | 5.2s | 5.7 | 174.4 |
| rag_cot | 39/50 | 78.00% | 3.5 min | 4.2s | 5.4 | 151.3 |
| self_consistency | 46/50 | 92.00% | 13.4 min | 16.1s | 6.9 | 189.1 |
| multi_agent_debate | 47/50 | 94.00% | 35.4 min | 42.4s | 9.2 | 368.6 |
| step_verifier | 46/50 | 92.00% | 172.2 min | 206.6s | 13.7 | 387.9 |

> **吞吐量** = samples per second

### 2.2 准确率排名

```
1. multi_agent_debate  47/50 = 94.0%  ★ 最高
2. base_cot            46/50 = 92.0%
3. self_consistency    46/50 = 92.0%
4. step_verifier       46/50 = 92.0%
5. rag_cot             39/50 = 78.0%  ▼ 最低
```

---

## 3. 关键发现

### 3.1 multi_agent_debate 表现最佳

- **准确率 94%**，高于所有其他策略
- 仅在 3 道题上出错（index 10, 20, 48）
- 在 index 32 上，它是**唯一答对**的策略
- 代价：耗时较长（35.4 min），token 消耗最高（368.6 avg）

### 3.2 rag_cot 意外表现最差

- **准确率仅 78%**，比 base_cot 低 14 个百分点
- 错误数 11 题，远超其他策略（3~4 题）
- **原因分析**：检索到的知识可能引入了干扰信息（retrieval noise），导致模型被错误知识误导
- 虽然 rag_cot 在小样本测试（10 条）中达到 100%，但在 50 样本上暴露了 retrieval noise 问题
- **启示**：RAG 的知识库质量至关重要，低质量检索会损害而非提升推理性能

### 3.3 self_consistency 未明显优于 base_cot

- 两者准确率相同（92%），错的是**完全相同的 4 道题**（index 10, 20, 32, 48）
- self-consistency 的多数投票机制未能挽救 base_cot 的失败案例
- 说明这些题目的错误不是偶然波动，而是模型本身的系统性盲区
- 时间成本：self-consistency 耗时是 base_cot 的 3 倍（13.4 min vs 4.4 min）

### 3.4 step_verifier 性价比极低

- 准确率 92%，与 base_cot 持平，但**耗时高达 172.2 分钟**（约 3 小时）
- 单条平均 206.6 秒，是 base_cot 的 47 倍
- 额外代价：每步验证带来大量额外 API 调用
- **结论**：在当前配置下，step_verifier 的验证开销远大于准确率收益

---

## 4. 错误案例分析

### 4.1 所有策略都错的题目（共 3 题）

| 题号 | base_cot | rag_cot | self_consistency | multi_agent_debate | step_verifier | 正确答案 |
|---|---|---|---|---|---|---|
| 10 | C | C | C | C | C | B |
| 20 | D | D | E | D | D | C |
| 48 | C | C | C | C | C | D |

> 这些题目属于**模型系统性盲区**，所有 CoT 策略均无法解决。
> 可能原因：几何/复杂代数、题目理解歧义、或答案标注错误。

### 4.2 multi_agent_debate 独对的题目（index 32）

| 策略 | 预测 | 正确答案 | 状态 |
|---|---|---|---|
| base_cot | (empty) | B | ❌ |
| rag_cot | (empty) | B | ❌ |
| self_consistency | (empty) | B | ❌ |
| multi_agent_debate | B | B | ✅ |
| step_verifier | (empty) | B | ❌ |

- 其他策略全部输出为空或错误答案，只有 multi_agent_debate 通过多 Agent 讨论纠正了理解
- 体现了 debate 机制在处理歧义题目时的优势

### 4.3 rag_cot 特有的错误（7 题）

rag_cot 做错但 base_cot 做对的题目索引：[8, 11, 21, 23, 27, 37, 43]（共 7 题）

- 这说明检索引入的知识**干扰了**模型原本正确的推理
- retrieval noise 是 RAG+COT 的实际部署中需要重点解决的问题

---

## 5. 效率与成本分析

### 5.1 时间成本

| 策略 | 50 样本总耗时 | 相对 base_cot 倍数 |
|---|---|---|
| base_cot | 4.4 min | 1.0x |
| rag_cot | 3.5 min | 0.8x |
| self_consistency | 13.4 min | 3.1x |
| multi_agent_debate | 35.4 min | 8.1x |
| step_verifier | 172.2 min | 39.4x |

### 5.2 Token 成本

| 策略 | 平均输出 Token | 相对 base_cot 倍数 |
|---|---|---|
| base_cot | 174.4 | 1.00x |
| rag_cot | 151.3 | 0.87x |
| self_consistency | 189.1 | 1.08x |
| multi_agent_debate | 368.6 | 2.11x |
| step_verifier | 387.9 | 2.22x |

### 5.3 性价比矩阵

| 策略 | 准确率 | 速度 | Token 消耗 | 综合性价比 |
|---|---|---|---|---|
| base_cot | 92% | 快 | 低 | ⭐⭐⭐⭐⭐ 最佳性价比 |
| rag_cot | 78% | 最快 | 最低 | ⭐⭐ 因准确率过低不推荐 |
| self_consistency | 92% | 中 | 中 | ⭐⭐⭐ 与 base 同准但慢 3x |
| multi_agent_debate | 94% | 慢 | 高 | ⭐⭐⭐⭐ 准确率最高但成本高 |
| step_verifier | 92% | 极慢 | 高 | ⭐ 性价比最低 |

---

## 6. Harness Engineering 子系统覆盖与表现关系

| 策略 | 子系统覆盖数 | 准确率 | 观察 |
|---|---|---|---|
| base_cot | 2/5 | 92% | 简单但有效 |
| self_consistency | 3/5 | 92% | 增加 State 但未提升准确率 |
| rag_cot | 4/5 | 78% | 增加 Tools 但检索噪声损害性能 |
| multi_agent_debate | 4/5 | 94% | 增加 Feedback 显著提升准确率 |
| step_verifier | 5/5 | 92% | 完整覆盖但 Feedback 粒度太细导致过犹不及 |

**核心洞察**：
- 子系统覆盖数 ≠ 准确率。`rag_cot` 和 `multi_agent_debate` 都覆盖 4/5，但准确率相差 16%。
- **Feedback 子系统（multi_agent_debate）对准确率提升最有效**，而 Tools 子系统（rag_cot）在当前实现下反而有害。
- `step_verifier` 覆盖 5/5 但准确率未提升，说明 verifier 的**粒度**和**评分标准**可能需要优化。

---

## 7. 与小样本实验（n=5~10）的对比

| 策略 | 小样本准确率 | 50 样本准确率 | 变化 |
|---|---|---|---|
| base_cot | 100% | 92% | ▼ -8%（回归真实水平） |
| rag_cot | 100% | 78% | ▼ -22%（暴露 retrieval noise） |
| self_consistency | 100% | 92% | ▼ -8% |
| multi_agent_debate | 100% | 94% | ▼ -6%（最稳定） |
| step_verifier | 100% | 92% | ▼ -8% |

- 小样本（5~10 条）因题目偏简单，所有策略均达到 100%，**无法区分优劣**。
- 50 样本实验揭示了真实差距：`multi_agent_debate` 最稳健，`rag_cot` 最差。

---

## 8. 结论与建议

### 8.1 策略选择建议

| 场景 | 推荐策略 | 理由 |
|---|---|---|
| 追求最高准确率，预算充足 | multi_agent_debate | 94% 准确率，能纠正单模型盲区 |
| 追求性价比，快速部署 | base_cot | 92% 准确率，最快最省 |
| 需要可解释性（每步验证） | step_verifier | 虽然慢，但提供步骤级打分 |
| 有高质量知识库 | rag_cot | 当前实现下不推荐，需先解决 retrieval noise |
| 需要中等提升，可接受额外耗时 | self_consistency | 但当前效果与 base 持平 |

### 8.2 后续优化方向

1. **RAG 知识库优化**：当前 keyword-based 检索可能引入了无关知识。建议：
   - 使用更精确的语义检索（embedding-based）
   - 对检索结果进行相关性过滤
   - 做消融实验：对比有/无检索的 rag_cot 表现

2. **Step Verifier 优化**：当前每步调用 verifier 开销过大。建议：
   - 改为稀疏验证（只验证关键步骤）
   - 使用本地轻量模型做 verifier，减少 API 调用
   - 调整评分阈值，避免过度惩罚

3. **Self-Consistency 优化**：当前 n_paths=3 可能不足。建议：
   - 尝试 n_paths=5 或 10，观察是否能挽救 index 10/20/48 的失败案例

4. **失败案例深度分析**：
   - 人工检查 index 10, 20, 48 的题目和模型输出
   - 分析是题目标注错误、理解歧义，还是模型能力边界

---

## 附录：原始数据

| Run ID | 策略 | 准确率 | 正确/总数 | 平均步数 | 平均 Token | 总耗时(s) |
|---|---|---|---|---|---|---|
| 20260610_224644 | base_cot | 0.9200 | 46/50 | 5.7 | 174.4 | 261.9 |
| 20260610_225338 | rag_cot | 0.7800 | 39/50 | 5.4 | 151.3 | 209.0 |
| 20260610_235458 | self_consistency | 0.9200 | 46/50 | 6.9 | 189.1 | 805.6 |
| 20260611_001603 | multi_agent_debate | 0.9400 | 47/50 | 9.2 | 368.6 | 2121.6 |
| 20260611_123110 | step_verifier | 0.9200 | 46/50 | 13.7 | 387.9 | 10330.9 |

> 原始 JSON 记录位于 `experiments/runs/` 目录下。
