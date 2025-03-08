## 评分系统的数学表达
## RAG原理的数学表达

为了更精确地理解RAG系统的工作原理，以下使用数学符号对核心流程进行形式化表达：

### 1. 文档向量化

文档集合 $D = \{d_1, d_2, ..., d_n\}$ 经过分块处理后得到文档块集合 $C = \{c_1, c_2, ..., c_m\}$，其中每个文档块包含元数据 $M(c_i)$ 和文本内容 $T(c_i)$。

向量化过程可表示为映射函数 $f: C \rightarrow \mathbb{R}^d$，将文本映射到 $d$ 维向量空间：

$$E(c_i) = f(T(c_i))$$

其中 $E(c_i) \in \mathbb{R}^d$ 是文档块 $c_i$ 的嵌入向量。

### 2. 查询处理

给定查询 $q$，同样通过映射函数获取查询向量：

$$E(q) = f(q)$$

### 3. 相似度计算与排序

向量间相似度通常采用余弦相似度：

$$sim(q, c_i) = \frac{E(q) \cdot E(c_i)}{||E(q)|| \cdot ||E(c_i)||} = \frac{\sum_{j=1}^{d} E(q)_j \cdot E(c_i)_j}{\sqrt{\sum_{j=1}^{d} E(q)_j^2} \cdot \sqrt{\sum_{j=1}^{d} E(c_i)_j^2}}$$

### 4. 两阶段检索数学模型

#### 4.1 广泛检索阶段

给定主题 $t$，检索相关文档块集合：

$$R_{broad}(t) = TopK(\{sim(t, c_i) \mid c_i \in C\}, k_{broad})$$

其中 $TopK$ 表示取相似度最高的 $k_{broad}$ 个结果。

多样性过滤可表示为：

$$R_{filtered}(t) = \{c_i \in R_{broad}(t) \mid \forall c_j \in R_{filtered}(t), i \neq j \Rightarrow prefix(c_i) \neq prefix(c_j)\}$$

其中 $prefix(c_i)$ 表示文档块的前缀特征。

#### 4.2 聚焦检索阶段

选择子主题 $s \in R_{filtered}(t)$ 后，进行聚焦检索：

$$R_{focused}(s) = TopK(\{sim(s, c_i) \mid c_i \in C\}, k_{focused})$$

文档分组操作：

$$G(R_{focused}(s)) = \{g_1, g_2, ..., g_l\}$$

其中 $g_j = \{c_i \in R_{focused}(s) \mid M(c_i).filename = f_j \land M(c_i).page = p_j\}$

连续块识别：

$$S(g_j) = \{seq_1, seq_2, ..., seq_m\}$$

其中 $seq_k = \{c_{i_1}, c_{i_2}, ..., c_{i_p}\}$ 满足 $\forall 1 \leq a < p, M(c_{i_a}).chunk\_index + 1 = M(c_{i_{a+1}}).chunk\_index$

选择最长连续序列：

$$L(g_j) = \arg\max_{seq_k \in S(g_j)} |seq_k|$$

最终选择最佳连续序列：

$$C_{best} = \arg\max_{g_j \in G(R_{focused}(s))} |L(g_j)|$$

### 5. 增强相关性评分

混合相关性评分函数：

$$\text{score}(q, c_i) = \alpha \cdot sim(q, c_i) + (1-\alpha) \cdot \text{keyword\_overlap}(q, c_i)$$

其中关键词重叠度定义为：

$$\text{keyword\_overlap}(q, c_i) = \frac{|K(q) \cap K(c_i)|}{|K(q)|}$$

$K(x)$ 表示文本 $x$ 中的关键词集合。

### 6. 生成过程

基于检索到的上下文 $C_{retrieved}$ 和输入 $x$，增强提示构建为：

$$P(x, C_{retrieved}) = [P_{system}, x, C_{retrieved}]$$

其中 $P_{system}$ 是系统提示。

最终生成过程可表示为条件概率：

$$p(y|P(x, C_{retrieved})) = \prod_{i=1}^{|y|} p(y_i|y_{<i}, P(x, C_{retrieved}))$$

其中 $y$ 是生成的输出（问题或评估），$y_{<i}$ 表示之前生成的所有标记。



ChatExaminer系统的评分机制可以通过以下数学模型精确表达：

### 1. 单题得分计算

给定问题 $q$ 的回答，评估指标包括准确性 $A_q$、清晰度 $C_q$ 和理解深度 $U_q$，均为0-100分。基础得分 $S_{\text{base}}(q)$ 计算公式为：

$$S_{\text{base}}(q) = \frac{A_q + C_q + U_q}{3}$$

### 2. 难度权重调整

系统根据问题难度 $d_q \in \{1,2,3,4,5\}$ 应用权重函数 $W_d: \{1,2,3,4,5\} \rightarrow \mathbb{R}^+$，定义为：

$$W_d(d_q) =
\begin{cases}
0.7, & \text{if } d_q = 1 \\
0.85, & \text{if } d_q = 2 \\
1.0, & \text{if } d_q = 3 \\
1.2, & \text{if } d_q = 4 \\
1.5, & \text{if } d_q = 5
\end{cases}$$

应用难度权重后的得分为：

$$S_{\text{weighted}}(q) = S_{\text{base}}(q) \cdot W_d(d_q)$$

### 3. 提示惩罚因子

对于使用了 $h_q$ 个提示的问题，提示惩罚 $P_h(q)$ 计算如下：

$$P_h(q) = S_{\text{base}}(q) \cdot 0.05 \cdot h_q$$

### 4. 最终单题得分

综合以上因素，问题 $q$ 的最终得分 $S_{\text{final}}(q)$ 为：

$$S_{\text{final}}(q) = \max(0, \min(100, S_{\text{weighted}}(q) - P_h(q)))$$

其中 $\max$ 和 $\min$ 函数确保分数在0-100范围内。

### 5. 整体考试得分

对于包含 $n$ 个问题的考试 $E = \{q_1, q_2, ..., q_n\}$，最终得分由三个组成部分加权计算：

1. **问题组成部分**（权重60%）：
   $$S_{\text{questions}} = \frac{1}{n} \sum_{i=1}^{n} S_{\text{final}}(q_i) \cdot 0.6$$

2. **主题覆盖度**（权重20%）：
   对于 $m$ 个主要知识点 $T = \{t_1, t_2, ..., t_m\}$ 及其覆盖率 $\text{Cov}(t_j) \in [0,1]$：
   $$S_{\text{coverage}} = \frac{1}{m} \sum_{j=1}^{m} \text{Cov}(t_j) \cdot 0.2$$

3. **行为分数**（权重20%）：
   定义为：
   $$S_{\text{behavior}} = \left(1 - \frac{\sum_{i=1}^{n} h_{q_i}}{n} \cdot 0.1\right) \cdot \text{consistency} \cdot \left(1 - \min\left(1, \frac{\text{avg\_time}}{300}\right)\right) \cdot 100 \cdot 0.2$$

   其中：
   - $\frac{\sum_{i=1}^{n} h_{q_i}}{n}$ 是平均每题使用的提示数
   - $\text{consistency}$ 是回答一致性指标（0-1）
   - $\text{avg\_time}$ 是平均每题回答时间（秒）

4. **整体得分**：
   $$S_{\text{total}}(E) = S_{\text{questions}} + S_{\text{coverage}} + S_{\text{behavior}}$$

该数学模型保证了评分系统的客观性和一致性，同时考虑了多维度因素对学生表现的综合评估。

## 状态机的数学表达

ChatExaminer系统的对话控制基于有限状态机(FSM)进行形式化建模，可表示为五元组 $M = (Q, \Sigma, \delta, q_0, F)$，其中：

### 1. 状态集合

系统的状态集合 $Q$ 包含所有可能的对话状态：

$$Q = \{\text{INIT}, \text{TOPIC\_SELECTED}, \text{QUESTIONING}, \text{EXPLAINING}, \text{EVALUATING}, \text{PAUSED}, \text{CHAT}, \text{COMPLETED}\}$$

### 2. 输入符号集

输入符号集 $\Sigma$ 代表用户输入的意图类型：

$$\Sigma = \{\text{student\_ready}, \text{student\_not\_ready}, \text{casual\_conversation}, \text{good\_response}, \text{student\_confused}, \text{questions\_completed}, \text{student\_needs\_break}, \text{understanding\_confirmed}, \text{report\_generated}, \text{resume\_exam}, \text{return\_to\_state}\}$$

### 3. 转换函数

状态转换函数 $\delta: Q \times \Sigma \rightarrow Q$ 定义系统从一个状态转移到另一个状态的规则，部分关键转换包括：

$$\delta(\text{INIT}, \text{student\_ready}) = \text{TOPIC\_SELECTED}$$
$$\delta(\text{TOPIC\_SELECTED}, \text{start\_exam}) = \text{QUESTIONING}$$
$$\delta(\text{QUESTIONING}, \text{good\_response}) = \text{QUESTIONING}$$
$$\delta(\text{QUESTIONING}, \text{student\_confused}) = \text{EXPLAINING}$$
$$\delta(\text{QUESTIONING}, \text{questions\_completed}) = \text{EVALUATING}$$
$$\delta(\text{EVALUATING}, \text{report\_generated}) = \text{COMPLETED}$$

### 4. 初始状态

系统的初始状态 $q_0$ 为：

$$q_0 = \text{INIT}$$

### 5. 接受状态集合

系统的接受状态集合 $F$ 包含：

$$F = \{\text{COMPLETED}\}$$

### 6. 状态转换概率模型

在实际实现中，状态转换并不是确定性的，而是基于大语言模型的输出进行概率判断。这种概率化状态机可表示为:

$$P(q_{t+1} = q_j | q_t = q_i, m_t) = f_{\text{LLM}}(q_i, m_t, q_j)$$

其中：
- $q_t$ 是时间 $t$ 的状态
- $m_t$ 是用户在时间 $t$ 的消息
- $f_{\text{LLM}}$ 是通过LLM进行状态意图判断的函数

### 7. 状态上下文表示

每个状态 $q \in Q$ 都有关联的上下文信息 $C(q)$，包含多个关键属性：

$$C(q) = \{topic, difficulty\_level, hints\_used, questions\_asked, responses, ...\}$$

这种形式化表示为ChatExaminer状态机提供了严格的数学基础，确保系统行为的一致性和可预测性，同时支持基于概率的灵活转换机制。



// ... existing code ...

这种形式化表示为ChatExaminer状态机提供了严格的数学基础，确保系统行为的一致性和可预测性，同时支持基于概率的灵活转换机制。

## 大语言模型(LLM)的数学表达

ChatExaminer系统的核心生成和推理能力由大语言模型提供，本节使用数学语言形式化描述LLM的工作原理及其在系统中的应用。

### 1. Transformer架构基础

LLM基于Transformer架构，其数学基础可表示为：

令 $X = [x_1, x_2, ..., x_n]$ 表示输入的token序列，每个token被嵌入为 $d$ 维向量。位置编码 $P = [p_1, p_2, ..., p_n]$ 添加到输入中以提供位置信息，得到：

$$H^0 = [x_1 + p_1, x_2 + p_2, ..., x_n + p_n]$$

### 2. 自注意力机制

自注意力机制是Transformer的核心，计算如下：

$$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V$$

其中：
- $Q = H^{l-1}W_Q^l$ 为查询矩阵
- $K = H^{l-1}W_K^l$ 为键矩阵
- $V = H^{l-1}W_V^l$ 为值矩阵
- $d_k$ 是键向量的维度
- $W_Q^l, W_K^l, W_V^l$ 是可学习的参数矩阵

多头注意力机制为：

$$\text{MultiHead}(H^{l-1}) = \text{Concat}(\text{head}_1, ..., \text{head}_h)W^O$$

其中每个头部 $\text{head}_i$ 计算为：

$$\text{head}_i = \text{Attention}(H^{l-1}W_{Q_i}, H^{l-1}W_{K_i}, H^{l-1}W_{V_i})$$

### 3. 前馈网络层

每个Transformer层还包含一个前馈网络：

$$\text{FFN}(x) = \max(0, xW_1 + b_1)W_2 + b_2$$

综合起来，第 $l$ 层的输出为：

$$H^l = \text{LayerNorm}(H^{l-1} + \text{MultiHead}(H^{l-1}))$$
$$H^l = \text{LayerNorm}(H^l + \text{FFN}(H^l))$$

### 4. 生成过程

给定上下文 $c = [c_1, c_2, ..., c_m]$，LLM生成下一个token的概率分布为：

$$P(x_{m+1} | c) = \text{softmax}(H^L W_E^T)$$

其中 $H^L$ 是最后一层的隐藏状态，$W_E$ 是嵌入矩阵。

整个序列的生成概率可表示为：

$$P(x_{1:n}) = \prod_{i=1}^{n} P(x_i | x_{1:i-1})$$

### 5. 在ChatExaminer中的应用

#### 5.1 提示工程数学表示

ChatExaminer系统中的提示可表示为函数 $\Phi: (q, c, r) \rightarrow p$，将问题 $q$、上下文 $c$ 和规则 $r$ 映射到提示 $p$：

$$p = \Phi(q, c, r) = r \oplus q \oplus c$$

其中 $\oplus$ 表示字符串连接操作。

#### 5.2 提示模板化

系统使用结构化提示模板 $T(·)$，参数化为：

$$T(q, c, \theta) = \theta_{\text{prefix}} \oplus q \oplus \theta_{\text{mid}} \oplus c \oplus \theta_{\text{suffix}}$$

其中 $\theta = \{\theta_{\text{prefix}}, \theta_{\text{mid}}, \theta_{\text{suffix}}\}$ 是提示模板参数。

#### 5.3 思维链提示

对于复杂推理任务，系统使用思维链（Chain-of-Thought，CoT）提示：

$$P_{\text{CoT}}(y|x) = \sum_{z \in Z} P(y|z,x) \cdot P(z|x)$$

其中 $z$ 是推理步骤，$Z$ 是所有可能的推理路径集合。

#### 5.4 LLM与RAG集成

RAG系统中的LLM生成过程可形式化为：

$$P_{\text{RAG}}(y|x) = \sum_{z \in \text{retrieve}(x)} P_{\text{LLM}}(y|x,z) \cdot P(z|x)$$

其中 $\text{retrieve}(x)$ 是检索函数，$P(z|x)$ 是文档 $z$ 相对于查询 $x$ 的相关性概率。

### 6. LLM评估过程

在评估学生回答时，LLM的判断过程可以表示为：

$$\text{Score}(a_s, q) = f_{\text{LLM}}(a_s, q, a_r, c_q)$$

其中：
- $a_s$ 是学生回答
- $q$ 是问题
- $a_r$ 是参考答案
- $c_q$ 是相关上下文
- $f_{\text{LLM}}$ 是LLM的评估函数

### 7. 校准与一致性

为增强评估的一致性，系统使用校准函数：

$$\text{Calibrated}(s) = \gamma \cdot s + \beta$$

其中 $\gamma$ 和 $\beta$ 是基于历史评估数据学习的参数，调整原始分数 $s$ 的分布。

这些数学表达式揭示了LLM在ChatExaminer系统中的核心作用，从token级别的概率计算到高层次的提示工程和评估过程，为系统的生成和推理能力提供了理论基础。
