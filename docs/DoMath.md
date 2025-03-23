# Mathematical Model Expression for ChatExaminer System

This document provides mathematical formalization of the core components in the ChatExaminer system, including RAG (Retrieval Augmented Generation), scoring system, state machine, and large language models.

## 1. Mathematical Expression of RAG Principles

The core process of RAG (Retrieval Augmented Generation) system can be precisely expressed through the following mathematical models:

### 1.1 Document Vectorization

Document collection $D = \{d_1, d_2, ..., d_n\}$ after chunking becomes document chunk collection $C = \{c_1, c_2, ..., c_m\}$, where each document chunk contains metadata $M(c_i)$ and text content $T(c_i)$.

The vectorization process can be represented as a mapping function $f: C \rightarrow \mathbb{R}^d$, which maps text to a $d$-dimensional vector space:

$$E(c_i) = f(T(c_i))$$

where $E(c_i) \in \mathbb{R}^d$ is the embedding vector of document chunk $c_i$.

### 1.2 Query Processing

Given a query $q$, the query vector is similarly obtained through the mapping function:

$$E(q) = f(q)$$

### 1.3 Similarity Calculation and Ranking

Vector similarity typically uses cosine similarity:

$$\text{sim}(q, c_i) = \frac{E(q) \cdot E(c_i)}{||E(q)|| \cdot ||E(c_i)||} = \frac{\sum_{j=1}^{d} E(q)_j \cdot E(c_i)_j}{\sqrt{\sum_{j=1}^{d} E(q)_j^2} \cdot \sqrt{\sum_{j=1}^{d} E(c_i)_j^2}}$$

### 1.4 Two-Stage Retrieval Mathematical Model

#### 1.4.1 Broad Retrieval Stage

Given a topic $t$, retrieve the relevant document chunk set:

$$R_{\text{broad}}(t) = \text{TopK}(\{\text{sim}(t, c_i) \mid c_i \in C\}, k_{\text{broad}})$$

where $\text{TopK}$ represents taking the $k_{\text{broad}}$ results with the highest similarity.

Diversity filtering can be represented as:

$$R_{\text{filtered}}(t) = \{c_i \in R_{\text{broad}}(t) \mid \forall c_j \in R_{\text{filtered}}(t), i \neq j \Rightarrow \text{prefix}(c_i) \neq \text{prefix}(c_j)\}$$

where $\text{prefix}(c_i)$ represents the prefix feature of the document chunk.

#### 1.4.2 Focused Retrieval Stage

After selecting subtopic $s \in R_{\text{filtered}}(t)$, perform focused retrieval:

$$R_{\text{focused}}(s) = \text{TopK}(\{\text{sim}(s, c_i) \mid c_i \in C\}, k_{\text{focused}})$$

Document grouping operation:

$$G(R_{\text{focused}}(s)) = \{g_1, g_2, ..., g_l\}$$

where $g_j = \{c_i \in R_{\text{focused}}(s) \mid M(c_i).\text{filename} = f_j \land M(c_i).\text{page} = p_j\}$

Continuous chunk identification:

$$S(g_j) = \{seq_1, seq_2, ..., seq_m\}$$

where $seq_k = \{c_{i_1}, c_{i_2}, ..., c_{i_p}\}$ satisfies $\forall 1 \leq a < p, M(c_{i_a}).\text{chunk\_index} + 1 = M(c_{i_{a+1}}).\text{chunk\_index}$

Select the longest continuous sequence:

$$L(g_j) = \arg\max_{seq_k \in S(g_j)} |seq_k|$$

Finally, select the best continuous sequence:

$$C_{\text{best}} = \arg\max_{g_j \in G(R_{\text{focused}}(s))} |L(g_j)|$$

### 1.5 Enhanced Relevance Scoring

Mixed relevance scoring function:

$$\text{score}(q, c_i) = \alpha \cdot \text{sim}(q, c_i) + (1-\alpha) \cdot \text{keyword\_overlap}(q, c_i)$$

where keyword overlap is defined as:

$$\text{keyword\_overlap}(q, c_i) = \frac{|K(q) \cap K(c_i)|}{|K(q)|}$$

$K(x)$ represents the set of keywords in text $x$.

### 1.6 Generation Process

Based on the retrieved context $C_{\text{retrieved}}$ and input $x$, the enhanced prompt is constructed as:

$$P(x, C_{\text{retrieved}}) = [P_{\text{system}}, x, C_{\text{retrieved}}]$$

where $P_{\text{system}}$ is the system prompt.

The final generation process can be represented as a conditional probability:

$$p(y|P(x, C_{\text{retrieved}})) = \prod_{i=1}^{|y|} p(y_i|y_{<i}, P(x, C_{\text{retrieved}}))$$

where $y$ is the generated output (question or evaluation), and $y_{<i}$ represents all previously generated tokens.

## 2. Mathematical Expression of the Scoring System

The scoring mechanism of the ChatExaminer system can be precisely expressed through the following mathematical models:

### 2.1 Individual Question Score Calculation

Given an answer to question $q$, evaluation metrics include accuracy $A_q$, clarity $C_q$, and depth of understanding $U_q$, all ranging from 0-100 points. The base score $S_{\text{base}}(q)$ calculation formula is:

$$S_{\text{base}}(q) = \frac{A_q + C_q + U_q}{3}$$

### 2.2 Difficulty Weight Adjustment

The system applies a weight function $W_d: \{1,2,3,4,5\} \rightarrow \mathbb{R}^+$ based on question difficulty $d_q \in \{1,2,3,4,5\}$, defined as:

$$W_d(d_q) =
\begin{cases}
0.7, & \text{if } d_q = 1 \\
0.85, & \text{if } d_q = 2 \\
1.0, & \text{if } d_q = 3 \\
1.2, & \text{if } d_q = 4 \\
1.5, & \text{if } d_q = 5
\end{cases}$$

The score after applying difficulty weight is:

$$S_{\text{weighted}}(q) = S_{\text{base}}(q) \cdot W_d(d_q)$$

### 2.3 Hint Penalty Factor

For questions using $h_q$ hints, the hint penalty $P_h(q)$ is calculated as follows:

$$P_h(q) = S_{\text{base}}(q) \cdot 0.05 \cdot h_q$$

### 2.4 Final Individual Question Score

Combining the above factors, the final score for question $q$, $S_{\text{final}}(q)$ is:

$$S_{\text{final}}(q) = \max(0, \min(100, S_{\text{weighted}}(q) - P_h(q)))$$

where $\max$ and $\min$ functions ensure the score is within the 0-100 range.

### 2.5 Overall Exam Score

For an exam $E = \{q_1, q_2, ..., q_n\}$ containing $n$ questions, the final score is calculated by weighting three components:

1. **Question Component** (60% weight):
   $$S_{\text{questions}} = \frac{1}{n} \sum_{i=1}^{n} S_{\text{final}}(q_i) \cdot 0.6$$

2. **Topic Coverage** (20% weight):
   For $m$ main knowledge points $T = \{t_1, t_2, ..., t_m\}$ and their coverage rates $\text{Cov}(t_j) \in [0,1]$:
   $$S_{\text{coverage}} = \frac{1}{m} \sum_{j=1}^{m} \text{Cov}(t_j) \cdot 0.2$$

3. **Behavior Score** (20% weight):
   Defined as:
   $$S_{\text{behavior}} = \left(1 - \frac{\sum_{i=1}^{n} h_{q_i}}{n} \cdot 0.1\right) \cdot \text{consistency} \cdot \left(1 - \min\left(1, \frac{\text{avg\_time}}{300}\right)\right) \cdot 100 \cdot 0.2$$

   where:
   - $\frac{\sum_{i=1}^{n} h_{q_i}}{n}$ is the average number of hints used per question
   - $\text{consistency}$ is the answer consistency indicator (0-1)
   - $\text{avg\_time}$ is the average answer time (seconds)

4. **Overall Score**:
   $$S_{\text{total}}(E) = S_{\text{questions}} + S_{\text{coverage}} + S_{\text{behavior}}$$

## 3. Mathematical Expression of the State Machine

The dialogue control of the ChatExaminer system is based on finite state machine (FSM) for formalized modeling, which can be represented as a five-tuple $M = (Q, \Sigma, \delta, q_0, F)$, where:

### 3.1 State Set

The system's state set $Q$ contains all possible dialogue states:

$$Q = \{\text{INIT}, \text{TOPIC\_SELECTED}, \text{QUESTIONING}, \text{EXPLAINING}, \text{EVALUATING}, \text{PAUSED}, \text{CHAT}, \text{COMPLETED}\}$$

### 3.2 Input Symbol Set

The input symbol set $\Sigma$ represents the intent type of user input:

$$\Sigma = \{\text{student\_ready}, \text{student\_not\_ready}, \text{casual\_conversation}, \text{good\_response}, \text{student\_confused}, \text{questions\_completed}, \text{student\_needs\_break}, \text{understanding\_confirmed}, \text{report\_generated}, \text{resume\_exam}, \text{return\_to\_state}\}$$

### 3.3 Transition Function

The state transition function $\delta: Q \times \Sigma \rightarrow Q$ defines the rules for transitioning from one state to another, with some key transitions including:

$$\delta(\text{INIT}, \text{student\_ready}) = \text{TOPIC\_SELECTED}$$
$$\delta(\text{TOPIC\_SELECTED}, \text{start\_exam}) = \text{QUESTIONING}$$
$$\delta(\text{QUESTIONING}, \text{good\_response}) = \text{QUESTIONING}$$
$$\delta(\text{QUESTIONING}, \text{student\_confused}) = \text{EXPLAINING}$$
$$\delta(\text{QUESTIONING}, \text{questions\_completed}) = \text{EVALUATING}$$
$$\delta(\text{EVALUATING}, \text{report\_generated}) = \text{COMPLETED}$$

### 3.4 Initial State

The system's initial state $q_0$ is:

$$q_0 = \text{INIT}$$

### 3.5 Accept State Set

The system's accept state set $F$ contains:

$$F = \{\text{COMPLETED}\}$$

### 3.6 State Transition Probability Model

In actual implementation, state transition is not deterministic but based on probability judgment from output of large language model. This probability state machine can be represented as:

$$P(q_{t+1} = q_j | q_t = q_i, m_t) = f_{\text{LLM}}(q_i, m_t, q_j)$$

where:
- $q_t$ is the state at time $t$
- $m_t$ is the user's message at time $t$
- $f_{\text{LLM}}$ is the function for judging state intent through LLM

### 3.7 State Context Representation

Each state $q \in Q$ has associated context information $C(q)$, containing multiple key attributes:

$$C(q) = \{topic, difficulty\_level, hints\_used, questions\_asked, responses, ...\}$$

## 4. Mathematical Expression of Large Language Model (LLM)

The core generation and reasoning ability of the ChatExaminer system is provided by large language model, and this section uses mathematical language to formalize the working principle of LLM and its application in the system.

### 4.1 Transformer Architecture Basis

LLM is based on Transformer architecture, and its mathematical basis can be represented as:

Let $X = [x_1, x_2, ..., x_n]$ represent the input token sequence, where each token is embedded into a $d$-dimensional vector. Position encoding $P = [p_1, p_2, ..., p_n]$ is added to the input to provide position information, resulting in:

$$H^0 = [x_1 + p_1, x_2 + p_2, ..., x_n + p_n]$$

### 4.2 Self-Attention Mechanism

Self-attention mechanism is the core of Transformer, calculated as follows:

$$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V$$

where:
- $Q = H^{l-1}W_Q^l$ is the query matrix
- $K = H^{l-1}W_K^l$ is the key matrix
- $V = H^{l-1}W_V^l$ is the value matrix
- $d_k$ is the dimension of the key vector
- $W_Q^l, W_K^l, W_V^l$ are learnable parameter matrices

Multi-head attention mechanism is:

$$\text{MultiHead}(H^{l-1}) = \text{Concat}(\text{head}_1, ..., \text{head}_h)W^O$$

where each head $\text{head}_i$ is calculated as:

$$\text{head}_i = \text{Attention}(H^{l-1}W_{Q_i}, H^{l-1}W_{K_i}, H^{l-1}W_{V_i})$$

### 4.3 Feedforward Network Layer

Each Transformer layer also contains a feedforward network:

$$\text{FFN}(x) = \max(0, xW_1 + b_1)W_2 + b_2$$

Combining these, the output of layer $l$ is:

$$H^l = \text{LayerNorm}(H^{l-1} + \text{MultiHead}(H^{l-1}))$$
$$H^l = \text{LayerNorm}(H^l + \text{FFN}(H^l))$$

### 4.4 Generation Process

Given context $c = [c_1, c_2, ..., c_m]$, LLM generates the probability distribution of the next token as:

$$P(x_{m+1} | c) = \text{softmax}(H^L W_E^T)$$

where $H^L$ is the hidden state of the last layer, and $W_E$ is the embedding matrix.

The generation probability of the entire sequence can be represented as:

$$P(x_{1:n}) = \prod_{i=1}^{n} P(x_i | x_{1:i-1})$$

### 4.5 Application in ChatExaminer

#### 4.5.1 Mathematical Representation of Hint Engineering

The hints in the ChatExaminer system can be represented as a function $\Phi: (q, c, r) \rightarrow p$, which maps question $q$, context $c$, and rule $r$ to hint $p$:

$$p = \Phi(q, c, r) = r \oplus q \oplus c$$

where $\oplus$ represents the string concatenation operation.

#### 4.5.2 Hint Templateization

The system uses structured hint template $T(\cdot)$, parameterized as:

$$T(q, c, \theta) = \theta_{\text{prefix}} \oplus q \oplus \theta_{\text{mid}} \oplus c \oplus \theta_{\text{suffix}}$$

where $\theta = \{\theta_{\text{prefix}}, \theta_{\text{mid}}, \theta_{\text{suffix}}\}$ is the hint template parameter.

#### 4.5.3 Chain-of-Thought Hint

For complex reasoning tasks, the system uses Chain-of-Thought (CoT) hint:

$$P_{\text{CoT}}(y|x) = \sum_{z \in Z} P(y|z,x) \cdot P(z|x)$$

where $z$ is the reasoning step, and $Z$ is the set of all possible reasoning path.

#### 4.5.4 LLM and RAG Integration

The LLM generation process in RAG system can be formalized as:

$$P_{\text{RAG}}(y|x) = \sum_{z \in \text{retrieve}(x)} P_{\text{LLM}}(y|x,z) \cdot P(z|x)$$

where $\text{retrieve}(x)$ is the retrieval function, and $P(z|x)$ is the relevance probability of document $z$ relative to query $x$.

### 4.6 LLM Evaluation Process

When evaluating student answers, the LLM judgment process can be represented as:

$$\text{Score}(a_s, q) = f_{\text{LLM}}(a_s, q, a_r, c_q)$$

where:
- $a_s$ is the student answer
- $q$ is the question
- $a_r$ is the reference answer
- $c_q$ is the related context
- $f_{\text{LLM}}$ is the LLM evaluation function

### 4.7 Calibration and Consistency

To enhance evaluation consistency, the system uses calibration function:

$$\text{Calibrated}(s) = \gamma \cdot s + \beta$$

where $\gamma$ and $\beta$ are parameters learned from historical evaluation data to adjust the distribution of original score $s$.

These mathematical expressions reveal the core role of LLM in the ChatExaminer system, from token-level probability calculation to high-level hint engineering and evaluation process, providing theoretical basis for system generation and reasoning ability.
