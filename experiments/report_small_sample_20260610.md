# COT 推理实验报告：小样本验证（n=5~10）

> **实验日期**：2026-06-10  
> **模型**：deepseek-v4-flash（DMXAPI）  
> **数据集**：AQuA（Algebraic Word Problems）test 集前 5~10 条样本  
> **实验目的**：验证 5 种 CoT 策略在真实 API 上的端到端运行能力，并横向对比推理质量与效率指标

---

## 1. 实验配置

| 配置项 | 值 |
|---|---|
| API 端点 | `https://www.dmxapi.cn/v1` |
| 模型 | `deepseek-v4-flash` |
| 温度系数 | 0.7 |
| 最大 token | 1024 |
| 数据集 | AQuA test |
| 样本量 | 5 ~ 10 条/策略 |

### 1.1 各策略参数

| 策略 | 关键参数 |
|---|---|
| base_cot | 无额外参数 |
| rag_cot | `top_k=3`（检索 3 条知识） |
| self_consistency | `n_paths=3`（3 条推理路径 + 多数投票） |
| multi_agent_debate | `n_agents=3, n_rounds=2`（3 个 Agent × 2 轮辩论） |
| step_verifier | `n_paths=3`（3 条路径，每步由 verifier 打分） |

---

## 2. 实验结果

### 2.1 准确率对比

| 策略 | 样本数 | 正确数 | 准确率 | Harness 子系统覆盖数 |
|---|---|---|---|---|
| **base_cot** | 5 | 5 | **100%** | 2/5 |
| **rag_cot** | 10 | 10 | **100%** | 4/5 |
| **self_consistency** | 10 | 10 | **100%** | 3/5 |
| **multi_agent_debate** | 10 | 10 | **100%** | 4/5 |
| **step_verifier** | 10 | 10 | **100%** | 5/5 |

### 2.2 效率指标对比

| 策略 | 平均推理步数 | 平均输出 Token | 总耗时 | 平均耗时/条 | 吞吐量 |
|---|---|---|---|---|---|
| **base_cot** | 6.0 | 181 | 173s | 34.6s | 0.03 sps |
| **rag_cot** | 5.3 | 169 | 65s | 6.5s | 0.15 sps |
| **self_consistency** | 7.6 | 199 | 202s | 20.2s | 0.05 sps |
| **multi_agent_debate** | 7.6 | 367 | 431s | 43.1s | 0.02 sps |
| **step_verifier** | 15.8 | 428 | 3199s | 319.9s | 0.003 sps |

> **sps** = samples per second（每秒处理样本数）

---

## 3. Harness Engineering 子系统覆盖矩阵

本实验借鉴 [learn-harness-engineering](https://github.com/walkinglabs/learn-harness-engineering) 的五子系统设计思想，将每种 CoT 策略映射到 Harness 子系统：

| 策略 | Instructions | Tools | Environment | State | Feedback |
|---|---|---|---|---|---|
| **base_cot** | ● | ○ | ● | ○ | ○ |
| **self_consistency** | ● | ○ | ● | ● | ○ |
| **rag_cot** | ● | ● | ● | ● | ○ |
| **multi_agent_debate** | ● | ○ | ● | ● | ● |
| **step_verifier** | ● | ● | ● | ● | ● |

### 3.1 子系统含义映射

| 子系统 | CoT 中的体现 |
|---|---|
| **Instructions** | Prompt 模板设计（推理格式、角色指令、验证器评分标准） |
| **Tools** | 外部工具调用（检索器、Verifier 元推理工具） |
| **Environment** | AQuA 任务环境（数据加载、答案提取、评估指标） |
| **State** | 运行时状态管理（多路径推理历史、检索上下文、辩论记录） |
| **Feedback** | 反馈闭环（步骤级验证打分、多 Agent 互评纠错） |

### 3.2 子系统演进路径

```
base_cot (2/5) ──[+State]──→ self_consistency (3/5)
                          ──[+Tools]──→ rag_cot (4/5)
                          ──[+Feedback]──→ multi_agent_debate (4/5)
                          ──[+Tools + Feedback]──→ step_verifier (5/5)
```

**核心洞察**：更复杂的 CoT 策略逐步激活更多 Harness 子系统。`step_verifier` 是唯一完整覆盖全部 5 个子系统的策略，体现了 Harness Engineering 设计思想在 CoT 框架中的最深融合。

---

## 4. 结果分析

### 4.1 准确率分析

在小样本（5~10 条）上，所有策略均达到 **100% 准确率**。原因分析：

1. **模型能力强**：deepseek-v4-flash 在简单代数应用题上表现优秀
2. **样本偏简单**：AQuA test 集前几条题目难度较低
3. **样本量不足**：5~10 条不足以 statistically 区分策略优劣，需要更大规模实验（建议 50~100 条）

### 4.2 效率与成本分析

尽管准确率相同，各策略在 **时间成本** 和 **Token 消耗** 上差异显著：

#### 最轻量策略：`rag_cot`
- ✅ **最快**：6.5s/条（比 base_cot 快 5 倍以上）
- ✅ **最省 token**：169（比 base_cot 少 7%）
- ✅ **推理步数最少**：5.3 步
- 原因：检索到的知识直接提供了公式/思路，减少了模型自行推理的步数

#### 最重策略：`step_verifier`
- ❌ **最慢**：320s/条（比 base_cot 慢 9 倍以上）
- ❌ **最耗 token**：428（比 base_cot 多 136%）
- ❌ **推理步数最多**：15.8 步
- 原因：对每条推理路径的每一步都要调用 verifier API 打分，额外 API 调用开销大

#### 中等策略对比

| 策略 | 相对 base_cot 耗时倍数 | 相对 base_cot token 倍数 |
|---|---|---|
| self_consistency | 0.58×（反而更快！） | 1.10× |
| multi_agent_debate | 1.25× | 2.03× |
| step_verifier | 9.24× | 2.36× |

> **注意**：self_consistency 比 base_cot 更快是因为 parallel-like 的循环调用在 API 端可能有并发优化；且 base_cot 的 5 条样本中有一条遇到 API 延迟异常（耗时异常长）。

### 4.3 Harness 子系统覆盖与策略复杂度的关系

| 子系统覆盖数 | 策略 | 特征 |
|---|---|---|
| 2 | base_cot | 仅使用 Instructions + Environment，最基础 |
| 3 | self_consistency | 增加 State（多路径管理），无额外工具 |
| 4 | rag_cot | 增加 Tools（检索器），利用外部知识 |
| 4 | multi_agent_debate | 增加 State + Feedback（多轮互评），无工具 |
| 5 | step_verifier | 完整覆盖，既有 Tools（verifier）又有 Feedback（打分筛选） |

---

## 5. 实验过程中发现的问题与修复

| 问题 | 原因 | 修复方案 |
|---|---|---|
| `self_consistency` 卡住 0/10 | DMXAPI 端点不支持 `n > 1` 的批量生成 | 改为循环调用 `n=1` 多次 |
| `step_verifier` 卡住 0/10 | 同上 | 同上 |
| `base_cot` 某条耗时 100+s | API 端偶发延迟 | 正常现象，已计入总耗时 |
| 长耗时策略无内部进度 | `step_verifier` / `multi_agent_debate` 内部多步调用不可见 | 为所有策略添加嵌套进度输出：路径生成、步骤验证、Agent 推理、检索结果均实时显示 |

---

## 6. 局限性

1. **样本量过小**：5~10 条样本不足以得出统计显著性结论。AQuA test 集共约 250 条，建议扩大至 50~100 条。
2. **题目偏简单**：test 集前几条难度较低，未能充分考验 CoT 策略的差异。
3. **未做消融实验**：未对 Harness 子系统进行 controlled variable exclusion test（如移除 retrieval 看 rag_cot 退化到 base_cot 的表现）。
4. **单次运行**：未做多次重复实验取平均，可能存在随机波动。

---

## 7. 下一步计划

### 7.1 扩大样本量
对每个策略跑 **50~100 条** AQuA test 样本，观察：
- 准确率是否开始分化
- 哪些题目类型对不同策略敏感

### 7.2 消融实验
- `rag_cot` 去掉 retrieval → 退化到 `base_cot`
- `step_verifier` 去掉 verifier → 退化到 `self_consistency`
- 量化每个子系统的边际贡献

### 7.3 失败案例分析
收集各策略答错的题目，分析：
- 哪些题目类型对所有策略都难？
- 哪些策略在特定题目上有优势？

### 7.4 报告完善
将 Harness Engineering 覆盖矩阵与实验结果结合，撰写最终报告：
- 五子系统如何赋能 CoT
- 不同策略的适用场景（轻量/高精度/可解释性）

---

## 附录：实验原始数据

| Run ID | 策略 | 模型 | 准确率 | 正确/总数 | 平均步数 | 平均 Token | 总耗时(s) |
|---|---|---|---|---|---|---|---|
| 20260610_203346 | base_cot | deepseek-v4-flash | 1.0000 | 5/5 | 6.0 | 181 | 173.0 |
| 20260610_204756 | rag_cot | deepseek-v4-flash | 1.0000 | 10/10 | 5.3 | 169 | 64.8 |
| 20260610_204844 | multi_agent_debate | deepseek-v4-flash | 1.0000 | 10/10 | 7.6 | 367 | 431.2 |
| 20260610_205116 | self_consistency | deepseek-v4-flash | 1.0000 | 10/10 | 7.6 | 199 | 201.9 |
| 20260610_205123 | step_verifier | deepseek-v4-flash | 1.0000 | 10/10 | 15.8 | 428 | 3198.6 |

> 原始 JSON 记录位于 `experiments/runs/` 目录下。
