# Career Intelligence Preparation Layer

## 背景

当前系统的输入为：

```text
parsed_confirmed_cv.json
```

目标包括：

1. 为用户生成：
   - Career Identity Statement
   - 1-2 个 follow-up questions
   - Career directions / fields suggestions

2. 为后续系统生成：
   - embedding input
   - RAG retrieval context
   - career path planning signals

当前实现已经具备 MVP 雏形，但仍然属于：

```text
CV field projection + LLM surface generation
```

而不是完整的：

```text
Career Intelligence Preparation Layer
```

---

# 一、当前系统流程分析

当前系统主要包含：

## 1. `/starter-profile`

文件：

- `service.py`
- `schemas.py`
- `router.py`

负责：

```text
confirmed_cv
↓
privacy stripped draft
↓
LLM generation
↓
starter identity + followup questions
```

---

## 2. `/embedding-input`

文件：

- `embedding_preparation_service.py`

负责：

```text
confirmed_cv
↓
deterministic text concatenation
↓
embedding_input_text
```

---

## 3. Artifact Storage

文件：

- `artifact_service.py`

负责：

```text
identity_followups.json
followup_answers.json
embedding_input.txt
```

版本化存储。

---

# 二、这一步本来应该做什么？

这一步实际上应该是：

# Career Intelligence Preparation Layer

而不仅仅是：

```text
prompt engineering
```

---

## 正确目标应该包括三类输出

---

# A. User-facing Career Identity Layer

给用户看的：

```text
Career Identity Statement
Follow-up Questions
Suggested Directions
```

作用：

- 验证系统是否正确理解用户
- 获取缺失 career signal
- 降低后续 career path uncertainty

---

# B. Structured Career Profile Layer

给内部系统使用：

```json
{
  "normalized_roles": [],
  "career_domains": [],
  "technical_domains": [],
  "competency_signals": [],
  "research_orientation": "",
  "engineering_orientation": "",
  "seniority_evidence": [],
  "career_direction_candidates": []
}
```

这是：

# Career Intelligence Core

当前系统缺失这一层。

---

# C. Semantic Embedding Layer

给 RAG 使用：

```json
{
  "chunks": [
    {
      "chunk_type": "experience",
      "text": "...",
      "skills": [],
      "domains": []
    }
  ]
}
```

而不是：

```text
single embedding_input_text
```

---

# 三、当前实现的优点

---

# 1. Privacy-aware design

当前：

`build_privacy_stripped_profile_draft()`

明确移除了：

- 姓名
- 邮箱
- 地址
- 电话
- 链接
- location

这是非常正确的。

因为：

embedding vector database 不应该包含 PII。

---

# 2. LLM Prompt Constraints 合理

Prompt 中明确要求：

- 不夸大 seniority
- 不使用 buzzwords
- evidence-backed positioning
- realistic career identity

这很好。

因为 career identity 最容易被 LLM 写成：

```text
motivated AI enthusiast passionate about innovation
```

这种无意义内容。

---

# 3. Deterministic embedding input

当前 embedding input：

不调用 LLM。

优点：

- 可复现
- 低成本
- 不会 hallucinate

作为 MVP 合理。

---

# 4. Artifact Versioning

identity_followups：

支持 generation history。

这对于：

- 用户修改
- A/B testing
- iterative refinement

都非常有帮助。

---

# 四、当前实现的主要问题

---

# 1. 缺失 Structured Career Profile Extraction

当前：

```text
confirmed CV
↓
identity generation
```

中间缺少：

```text
Career Profile Extraction
```

因此系统无法：

- role normalization
- competency abstraction
- domain inference
- career direction inference
- seniority reasoning

---

# 2. Embedding Input 过于字段拼接

当前格式：

```text
Role: ...
Responsibilities: ...
```

这对于 embedding 可用。

但不是最佳。

embedding 更适合：

# semantic narrative chunk

例如：

```text
The candidate completed a computer vision internship involving synthetic image generation with Unreal Engine 5 and downstream tasks such as person re-identification and camera alignment.
```

---

# 3. Projects 未进入 Embedding Input

这是当前最大缺陷之一。

当前：

```text
experience
education
technical skills
```

会进入 embedding。

但：

```text
Gaussian Splatting
TacticAI GNN
```

这些高价值项目没有进入 embedding。

会导致：

- AI
- CV
- GNN
- Research Engineering

方向严重低估。

---

# 4. Technical Skill Extraction 依赖 Parser

当前 confirmed JSON：

```json
"technical_skills": []
```

但 CV 实际包含：

- Python
- TypeScript
- C++
- Unreal Engine 5
- Selenium
- Qt
- GNN
- Deep Learning

说明：

Parser 不可靠。

当前系统缺少：

# secondary skill extraction

---

# 5. Current Role Fallback 不合理

当前：

```python
_fallback_current_role()
```

取第一段 experience role。

但：

对于学生 / research-oriented candidate：

当前身份不应该等于：

```text
Internship in Computer Vision Development
```

而更应该是：

```text
MSc Robotics and AI student with research engineering orientation
```

---

# 五、这一步真正应该做的数据处理

---

# Step 1 — Privacy Filtering

当前已有。

保留即可。

---

# Step 2 — Structured Career Profile Extraction

新增：

```text
confirmed_cv
↓
CareerProfile
```

输出：

```json
{
  "normalized_roles": [],
  "career_domains": [],
  "technical_domains": [],
  "competency_signals": [],
  "career_orientation": [],
  "seniority_estimate": ""
}
```

---

## 应新增的数据推断

---

### A. Role Normalization

例如：

```text
Internship in Computer Vision Development
```

↓

```text
Computer Vision Engineer Intern
```

---

### B. Domain Inference

从：

- projects
- coursework
- thesis
- responsibilities

推断：

```json
[
  "Computer Vision",
  "Deep Learning",
  "3D Vision",
  "Graph ML",
  "Research Engineering"
]
```

---

### C. Competency Extraction

从：

```text
single-view image to 3D person generation
```

抽象：

```json
[
  "3D Human Modeling",
  "Resource-efficient ML systems",
  "Applied Deep Learning"
]
```

---

### D. Seniority Reasoning

结合：

- internships
- freelance
- entrepreneurship
- MSc
- project complexity

推断：

```json
{
  "estimated_level": "student/junior research engineer"
}
```

---

# Step 3 — Follow-up Question Generation

问题应该：

# 为 career path disambiguation 服务

而不是 generic preference。

---

## 当前问题

Prompt：

```text
one capability-focused
one orientation-focused
```

方向对。

但不够具体。

---

## 更好的问题

例如：

```text
你更倾向于哪种 AI 工作模式？

A. research engineering
B. product ML engineering
C. robotics perception
D. applied AI consulting
```

这类问题：

可以直接影响：

- career path generation
- retrieval weighting
- transition graph

---

# Step 4 — Semantic Chunk Generation

这是当前系统最缺失的部分。

---

## 当前实现

```text
single embedding_input_text
```

---

## 应改成

```json
{
  "chunks": [
    {
      "chunk_type": "experience",
      "text": "...",
      "skills": [],
      "domains": []
    }
  ]
}
```

---

# 六、推荐的 Chunk Types

---

# 1. Experience Chunks

按工作经历拆。

---

# 2. Project Chunks（高优先级）

例如：

```text
Gaussian Splatting
TacticAI GNN
```

这些比 education 更重要。

---

# 3. Competency Chunks

聚合抽象：

```text
Candidate repeatedly worked on computer vision and deep learning systems involving synthetic datasets and human modeling.
```

---

# 4. Career Intent Chunks

推断：

```text
research-oriented AI engineering trajectory
```

---

# 七、为什么不能只用一个 embedding_input_text？

因为 career RAG 检索目标很多：

- occupations
- competencies
- skills
- career transitions
- SFIA levels

一个大文本：

会把信号混在一起。

导致：

- retrieval precision 下降
- occupation ambiguity
- competency dilution

---

# 八、当前 Schema 的问题

当前：

```python
class EmbeddingInputResponse(BaseModel):
    embedding_input_text: str
    embedding_metadata: EmbeddingMetadata
```

建议：

```python
class EmbeddingChunk(BaseModel):
    chunk_id: str
    chunk_type: str
    text: str
    skills: list[str]
    domains: list[str]
```

---

# 九、建议的新架构

---

# 推荐 Pipeline

```text
confirmed_cv
↓
Privacy Filtering
↓
Career Profile Extraction
↓
Identity Generation
↓
Follow-up Question Generation
↓
Semantic Chunk Generation
↓
Embedding
↓
RAG Retrieval
↓
Career Path Planning
```

---

# 十、推荐的系统分层

---

# Layer 1 — Raw CV Parsing

当前已有。

---

# Layer 2 — Structured Career Intelligence

新增。

最重要。

---

# Layer 3 — Semantic Chunk Layer

新增。

用于 embedding。

---

# Layer 4 — Retrieval Layer

未来：

- ESCO
- O*NET
- SFIA
- Career Graph

---

# Layer 5 — Career Reasoning Layer

LLM：

- explainability
- path planning
- gap analysis

---

# 十一、哪些部分可以精简？

---

# 1. soft skills embedding

soft skills：

优先级较低。

可只放 metadata。

---

# 2. interests embedding

interests：

没有 strong evidence 时：

不建议 embedding。

---

# 3. duplicated unmapped filters

当前：

- `_privacy_safe_career_signals`
- `_format_unmapped_information`

都有 keyword filtering。

建议统一。

---

# 4. current_role fallback

建议移除：

```python
include_personal_info
```

逻辑。

改成：

Career Profile Extraction 统一推断。

---

# 十二、真正需要新增的核心模块

---

# CareerProfileExtractionService

这是整个系统最关键的新增模块。

作用：

```text
confirmed_cv
↓
career intelligence profile
```

输出：

```json
{
  "normalized_roles": [],
  "technical_domains": [],
  "competency_signals": [],
  "career_orientation": [],
  "seniority_estimate": ""
}
```

---

# 十三、最终推荐的数据结构

---

## User-facing

```json
{
  "career_identity_statement": "",
  "followup_questions": []
}
```

---

## Internal

```json
{
  "career_profile": {},
  "embedding_chunks": []
}
```

---

# 十四、总结

当前系统：

已经是一个不错的 MVP。

但本质仍然是：

```text
CV field projection + LLM surface generation
```

还没有进入：

# Career Intelligence System

真正需要补齐的是：

1. Structured career profile extraction
2. Semantic chunk generation
3. Competency abstraction
4. Project-centric retrieval signals
5. Career-direction disambiguation

未来真正决定系统质量的：

不是 LLM。

而是：

- retrieval precision
- competency calibration
- evidence grounding
- semantic chunk quality
- career graph realism
