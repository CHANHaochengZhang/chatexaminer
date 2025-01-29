# ChatExaminer API 文档

## 设计原理

### 架构概述

ChatExaminer API 采用 RESTful 架构风格设计，同时结合 WebSocket 提供实时交互能力。系统架构分为以下几个核心部分：

1. **状态管理**
   - 采用有限状态机(FSM)管理考试流程
   - 每个考试会话维护独立的状态
   - 支持状态间的平滑过渡和异常处理

2. **会话管理**
   - 基于 UUID 的会话标识
   - 服务端维护会话状态和上下文
   - 支持多用户并发考试

3. **通信模式**
   - REST API：用于基础的考试流程控制
   - WebSocket：用于实时问答交互
   - 混合模式：确保最佳的用户体验

### 系统架构图

```mermaid
graph TD
    Client[客户端] --> |HTTP/WebSocket| API[API 层]
    API --> |状态转换| FSM[状态机]
    API --> |会话管理| SessionMgr[会话管理器]
    FSM --> |状态更新| SessionMgr
    SessionMgr --> |考试数据| ExamService[考试服务]
    ExamService --> |问题生成| QGen[问题生成器]
    ExamService --> |答案评估| Eval[评估系统]

    subgraph 状态机
    FSM --> State1[INIT]
    FSM --> State2[TOPIC_SELECTED]
    FSM --> State3[QUESTIONING]
    FSM --> State4[EXPLAINING]
    FSM --> State5[EVALUATING]
    FSM --> State6[COMPLETED]
    FSM --> State7[CHAT]
    end
```

### 接口设计原则

1. **RESTful 规范**
   - 使用标准 HTTP 方法
   - 资源化的 URL 设计
   - 无状态通信原则

2. **实时交互**
   - WebSocket 保持长连接
   - 双向通信支持
   - 实时状态同步

3. **可扩展性**
   - 模块化的接口设计
   - 版本控制支持
   - 灵活的状态转换机制

4. **安全性**
   - 会话级别的隔离
   - 输入验证和消毒
   - 错误处理机制

5. **可维护性**
   - 清晰的接口文档
   - 标准的错误响应
   - 完整的状态追踪

### 数据流图

```mermaid
sequenceDiagram
    participant Client as 客户端
    participant API as API 层
    participant FSM as 状态机
    participant Service as 考试服务

    Client->>API: POST /start (选择主题)
    API->>FSM: 初始化状态
    FSM->>Service: 创建考试会话
    Service-->>API: 返回会话信息
    API-->>Client: 返回首个问题

    loop 考试过程
        Client->>API: POST /{session}/answer
        API->>FSM: 检查状态转换
        FSM->>Service: 处理答案
        Service-->>API: 返回下一问题/评估
        API-->>Client: 返回响应
    end

    Client->>API: GET /{session}/evaluation
    API->>Service: 生成评估报告
    Service-->>API: 返回评估结果
    API-->>Client: 返回最终评估
```

## 基本信息

- 基础URL: `http://localhost:8000/api/exam`
- 所有请求和响应均使用 JSON 格式
- 所有时间戳使用 ISO 8601 格式

## 通用响应格式

```json
{
    "state": "当前状态",
    "message": "响应消息",
    "data": {
        // 具体数据
    }
}
```

## 状态定义

- `INIT`: 初始状态
- `TOPIC_SELECTED`: 已选择考试主题
- `QUESTIONING`: 问答阶段
- `EXPLAINING`: 解释阶段
- `EVALUATING`: 评估阶段
- `COMPLETED`: 考试完成
- `CHAT`: 闲聊状态

## API 端点

### 1. 启动考试会话

启动新的考试会话并选择考试主题。

- **URL**: `/start`
- **方法**: `POST`
- **请求体**:
  ```json
  {
      "topic": "考试主题"
  }
  ```
- **成功响应** (200):
  ```json
  {
      "state": "QUESTIONING",
      "message": "考试会话已创建并开始",
      "data": {
          "session_id": "uuid",
          "result": {
              "type": "state_change",
              "state": "QUESTIONING"
          },
          "current_question": {
              "question": "问题内容",
              "difficulty": 3
          }
      }
  }
  ```
- **错误响应** (400):
  ```json
  {
      "detail": "错误信息"
  }
  ```

### 2. 提交答案

提交对当前问题的回答。

- **URL**: `/{session_id}/answer`
- **方法**: `POST`
- **请求体**:
  ```json
  {
      "answer": "学生的回答"
  }
  ```
- **成功响应** (200):
  ```json
  {
      "state": "QUESTIONING",
      "message": "回答已处理",
      "data": {
          "result": {
              "type": "response",
              "feedback": "反馈信息"
          },
          "current_question": {
              "question": "下一个问题",
              "difficulty": 3
          }
      }
  }
  ```
- **错误响应** (404):
  ```json
  {
      "detail": "考试会话不存在"
  }
  ```

### 3. 获取考试状态

获取当前考试会话的状态信息。

- **URL**: `/{session_id}/state`
- **方法**: `GET`
- **成功响应** (200):
  ```json
  {
      "state": "QUESTIONING",
      "message": "当前考试状态",
      "data": {
          "context": {
              "questions_answered": 3,
              "hints_requested": 1,
              "current_difficulty": 3,
              "topic": "考试主题"
          },
          "current_question": {
              "question": "当前问题",
              "difficulty": 3
          }
      }
  }
  ```

### 4. 获取评估结果

获取考试的最终评估结果。

- **URL**: `/{session_id}/evaluation`
- **方法**: `GET`
- **成功响应** (200):
  ```json
  {
      "state": "COMPLETED",
      "message": "考试评估结果",
      "data": {
          "total_score": 85.5,
          "topic_coverage": "4/5",
          "behavior_score": 90.0,
          "question_evaluations": {
              "1": {
                  "score": 85,
                  "feedback": "详细反馈",
                  "details": {
                      "准确性": "85/100",
                      "清晰度": "90/100",
                      "理解度": "80/100"
                  }
              }
          },
          "behavior_details": {
              "回答完整性": "85/100",
              "思维逻辑性": "90/100",
              "专业术语": "95/100",
              "举例能力": "85/100"
          }
      }
  }
  ```

## WebSocket 接口

### 实时交互

- **URL**: `ws://localhost:8000/api/exam/{session_id}/ws`
- **发送消息格式**:
  ```json
  {
      "answer": "学生的回答"
  }
  ```
- **接收消息格式**:
  ```json
  {
      "type": "response",
      "state": "QUESTIONING",
      "data": {
          "result": {
              "type": "response",
              "feedback": "反馈信息"
          },
          "current_question": {
              "question": "问题内容",
              "difficulty": 3
          }
      }
  }
  ```
- **错误消息格式**:
  ```json
  {
      "type": "error",
      "message": "错误信息"
  }
  ```

## 错误代码

- 400: 请求参数错误
- 404: 资源不存在
- 500: 服务器内部错误

## 使用示例

### Python 示例

```python
import requests
import json

BASE_URL = "http://localhost:8000/api/exam"

# 1. 启动考试
start_response = requests.post(f"{BASE_URL}/start",
                             json={"topic": "Direct Methods for Optimal Control"})
session_id = start_response.json()["data"]["session_id"]

# 2. 提交答案
answer_response = requests.post(f"{BASE_URL}/{session_id}/answer",
                              json={"answer": "这是答案"})

# 3. 获取状态
state_response = requests.get(f"{BASE_URL}/{session_id}/state")

# 4. 获取评估
evaluation_response = requests.get(f"{BASE_URL}/{session_id}/evaluation")
```

### WebSocket 示例

```python
import websockets
import asyncio
import json

async def connect_exam():
    uri = f"ws://localhost:8000/api/exam/{session_id}/ws"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"answer": "这是答案"}))
        response = await ws.recv()
        print(json.loads(response))

asyncio.run(connect_exam())
```

## 注意事项

1. 所有请求都需要包含正确的 session_id（除了启动考试）
2. WebSocket 连接在考试会话不存在时会自动关闭
3. 评估结果只有在考试完成状态才能获取
4. 建议使用 WebSocket 进行实时交互，以获得更好的体验

## Hint 相关接口

### 获取提示

获取当前考试问题的提示信息。

**请求**

```http
GET /api/exam/{session_id}/hint
```

**路径参数**

| 参数 | 类型 | 描述 |
|------|------|------|
| session_id | string | 考试会话ID |

**响应**

```json
{
  "state": "string",     // 当前考试状态
  "message": "string",   // 响应消息
  "data": {
    "hint": "string",    // 生成的提示内容
    "hints_used": number // 已使用的提示次数
  }
}
```

**状态码**

| 状态码 | 描述 |
|--------|------|
| 200 | 成功获取提示 |
| 404 | 考试会话不存在 |
| 400 | 请求参数错误 |
| 403 | 无权限访问该考试会话 |

**示例**

请求:
```http
GET /api/exam/abc123/hint
```

成功响应:
```json
{
  "state": "IN_PROGRESS",
  "message": "提示已生成",
  "data": {
    "hint": "考虑使用微分方程来解决这个问题,首先写出物体的运动方程...",
    "hints_used": 2
  }
}
```

错误响应:
```json
{
  "state": "ERROR",
  "message": "考试会话不存在",
  "data": null
}
```

### 使用限制

1. 每个问题最多可以请求3次提示
2. 使用提示会影响最终得分,每使用一次提示扣除该题分数的10%
3. 提示生成会考虑:
   - 问题难度
   - 主题/子主题
   - 上下文信息
   - 学生当前表现

### 错误码说明

| 错误码 | 描述 | 解决方案 |
|--------|------|----------|
| HINT_LIMIT_EXCEEDED | 超出提示使用次数限制 | 等待下一道题目 |
| SESSION_NOT_FOUND | 考试会话不存在 | 检查session_id是否正确 |
| QUESTION_NOT_ACTIVE | 当前没有活动的问题 | 确保考试正在进行中 |
| UNAUTHORIZED | 无访问权限 | 检查用户认证状态 |

### WebSocket 事件

提示相关的实时事件通知:

```typescript
interface HintEvent {
  type: 'HINT_REQUESTED' | 'HINT_GENERATED' | 'HINT_ERROR';
  data: {
    questionId: string;
    hint?: string;
    error?: string;
    timestamp: string;
  }
}
```

### 客户端集成

TypeScript 示例:

```typescript
interface HintResponse {
  hint: string;
  hintsUsed: number;
}

class ExamAPI {
  async requestHint(): Promise<HintResponse> {
    if (!this.sessionId) {
      throw new Error('No active exam session');
    }
    const response = await axios.get(
      `${BASE_URL}/${this.sessionId}/hint`
    );
    return {
      hint: response.data.data.hint,
      hintsUsed: response.data.data.hints_used
    };
  }
}
```

### 安全性考虑

1. 访问控制
   - 验证用户是否有权访问该考试会话
   - 检查提示请求频率限制
   - 防止提示内容泄露

2. 数据保护
   - 所有API请求需要通过HTTPS
   - 提示内容在传输和存储时进行加密
   - 定期清理历史提示数据

### 性能优化

1. 缓存策略
   - 对相似问题的提示进行缓存
   - 使用Redis存储会话状态
   - CDN加速静态资源

2. 限流措施
   - 基于用户的请求频率限制
   - 服务器负载自适应调节
   - 队列处理大量并发请求

### 监控指标

1. 业务指标
   - 提示使用率
   - 提示效果评分
   - 用户满意度

2. 技术指标
   - API响应时间
   - 错误率统计
   - 系统资源使用率

# API 实现文档

## 系统架构图

```mermaid
graph TD
    A[前端应用] -->|HTTP请求| B[API网关]
    B -->|路由转发| C[考试服务]
    C -->|会话管理| D[状态机]
    C -->|提示生成| E[OpenAI服务]
    C -->|数据存储| F[(Redis)]
    C -->|持久化| G[(PostgreSQL)]

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#bbf,stroke:#333,stroke-width:2px
    style C fill:#bfb,stroke:#333,stroke-width:2px
    style D fill:#fbb,stroke:#333,stroke-width:2px
    style E fill:#bff,stroke:#333,stroke-width:2px
```

## 提示请求流程

```mermaid
sequenceDiagram
    participant U as 用户
    participant F as 前端
    participant B as 后端
    participant AI as OpenAI
    participant DB as 数据库

    U->>F: 点击获取提示
    F->>B: GET /api/exam/{session_id}/hint
    B->>DB: 检查会话状态
    B->>DB: 获取当前问题
    B->>AI: 生成提示请求
    AI-->>B: 返回生成的提示
    B->>DB: 更新提示使用统计
    B-->>F: 返回提示内容
    F-->>U: 显示提示
```

## 状态转换图

```mermaid
stateDiagram-v2
    [*] --> 未开始
    未开始 --> 进行中: 开始考试
    进行中 --> 已暂停: 暂停
    已暂停 --> 进行中: 继续
    进行中 --> 已完成: 提交
    已完成 --> [*]

    state 进行中 {
        [*] --> 答题中
        答题中 --> 查看提示: 请求提示
        查看提示 --> 答题中: 继续答题
    }
```

## 组件交互图

```mermaid
graph LR
    A[ExamStore] -->|状态管理| B[ExamAPI]
    B -->|HTTP请求| C[FastAPI Router]
    C -->|服务调用| D[ExamService]
    D -->|状态维护| E[StateMachine]
    D -->|提示生成| F[OpenAI]

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#bbf,stroke:#333,stroke-width:2px
    style C fill:#bfb,stroke:#333,stroke-width:2px
    style D fill:#fbb,stroke:#333,stroke-width:2px
```

## 数据流图

```mermaid
graph TD
    A[用户输入] -->|触发| B[前端Store]
    B -->|API调用| C[后端服务]
    C -->|查询| D[会话状态]
    C -->|生成| E[提示内容]
    E -->|存储| D
    D -->|返回| C
    C -->|响应| B
    B -->|更新| F[UI显示]

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style F fill:#f9f,stroke:#333,stroke-width:2px
```
