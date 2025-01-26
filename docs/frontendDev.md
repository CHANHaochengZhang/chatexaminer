# ChatExaminer 前端开发文档

## 布局设计

### 整体布局
- 采用响应式设计，主要分为两种视图：
  1. 初始状态（选择主题）
  2. 考试进行状态（分栏布局）

### 组件结构
```
Exam.vue (主视图)
├── 初始状态
│   └── 主题选择表单
└── 考试状态
    ├── 左侧面板
    │   ├── StatePanel (状态面板)
    │   └── EvalReport (评估报告，仅完成状态显示)
    └── 右侧面板
        └── ExamChat (聊天界面)
```

### 组件详情

#### StatePanel（状态面板）
- 显示当前考试状态
- 显示已答题数量
- 显示使用提示次数
- 显示当前难度等级
- 使用 Element Plus 的 Card 和 Tag 组件

#### ExamChat（聊天界面）
- 消息列表显示
  - 支持系统消息、用户消息和助手消息
  - 不同角色消息使用不同样式
  - 显示发送时间
- 输入区域
  - 文本输入框
  - 发送按钮
  - 支持 Enter 发送
- 自动滚动到最新消息

#### EvalReport（评估报告）
- 总分显示
- 主题覆盖标签
- 优点列表
- 不足列表
- 建议列表

## 状态管理

### 考试状态
```typescript
type ExamState = 'INIT' | 'TOPIC_SELECTED' | 'QUESTIONING' | 'EXPLAINING' | 'EVALUATING' | 'COMPLETED' | 'CHAT'
```

### 数据流
1. 开始考试
   - 用户输入主题
   - 调用 API 创建会话
   - 建立 WebSocket 连接
   - 更新状态和显示初始消息

2. 考试过程
   - 用户发送消息
   - 通过 WebSocket 接收响应
   - 更新状态和消息列表
   - 动态更新统计数据

3. 完成评估
   - 获取评估报告
   - 显示详细评估信息

## API 服务

### ExamService 类
- 管理与后端的通信
- 维护考试会话状态
- 处理 WebSocket 连接
- 方法：
  - startExam
  - submitAnswer
  - getExamState
  - getEvaluation
  - connectWebSocket
  - clearSession

## 样式设计

### 主题变量
```scss
:root {
  --primary-color: #409eff;
  --background-color: #f5f7fa;
  --text-color: #303133;
  --spacing-md: 16px;
}
```

### 布局特点
- 使用 CSS Grid 实现分栏布局
- 固定侧边栏宽度（300px）
- 自适应主内容区域
- 统一的间距和圆角
- 阴影效果增强层次感

## 开发记录

### 2024-01-26
1. 初始化项目
   - 使用 Vue 3 + TypeScript + Vite
   - 配置 Element Plus UI 库
   - 设置路由和状态管理

2. 实现基础组件
   - 创建主视图 Exam.vue
   - 实现状态面板组件
   - 实现聊天界面组件
   - 实现评估报告组件

3. 配置 API 服务
   - 实现 ExamService 类
   - 配置 WebSocket 连接
   - 处理会话管理

4. 优化用户体验
   - 添加加载状态
   - 完善错误处理
   - 优化消息展示
   - 实现自动滚动

### 待办事项
- [ ] 添加消息重试机制
- [ ] 实现断线重连
- [ ] 优化移动端适配
- [ ] 添加主题切换功能
- [ ] 增加动画效果
