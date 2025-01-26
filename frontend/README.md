# ChatExaminer 前端

ChatExaminer 是一个基于 AI 的智能口试系统的前端项目。本项目使用 Vue 3 + TypeScript + Vite 构建，提供了一个现代化的考试交互界面。

## 技术栈

- Vue 3 - 渐进式 JavaScript 框架
- TypeScript - JavaScript 的超集，提供类型系统
- Vite - 下一代前端构建工具
- Element Plus - Vue 3 的组件库
- Pinia - Vue 的状态管理方案
- Axios - HTTP 客户端
- WebSocket - 实时通信

## 目录结构

```
frontend/
├── src/
│   ├── assets/        # 静态资源
│   ├── components/    # 公共组件
│   │   ├── ExamChat/  # 考试对话组件
│   │   ├── StatePanel/# 状态面板组件
│   │   └── EvalReport/# 评估报告组件
│   ├── views/         # 页面组件
│   │   ├── Home.vue   # 首页
│   │   ├── Exam.vue   # 考试页
│   │   └── Report.vue # 报告页
│   ├── stores/        # Pinia 状态管理
│   ├── services/      # API 服务
│   ├── router/        # 路由配置
│   ├── App.vue        # 根组件
│   └── main.ts        # 入口文件
├── public/            # 公共资源
└── vite.config.ts     # Vite 配置
```

## 功能特性

- 💬 实时对话：基于 WebSocket 的实时考试对话
- 📊 状态追踪：实时显示考试进度和状态
- 📝 智能评估：自动生成详细的评估报告
- 🎨 美观界面：基于 Element Plus 的现代化 UI
- 📱 响应式设计：支持多种设备尺寸

## 开发指南

### 环境准备

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 代码检查
npm run lint
```

### 开发端口

- 前端开发服务器运行在 http://localhost:3000
- API 请求代理到 http://localhost:8000
- WebSocket 连接代理到 ws://localhost:8000

### 环境变量

开发环境下的环境变量配置在 `.env.development` 文件中：

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
```

## 组件说明

### ExamChat
考试对话组件，处理学生与系统之间的实时对话。支持：
- 发送答案
- 请求提示
- 显示历史消息
- 自动滚动

### StatePanel
状态面板组件，显示当前考试状态：
- 考试阶段
- 已答题数
- 使用提示数
- 当前难度

### EvalReport
评估报告组件，展示考试结果：
- 总分统计
- 知识点覆盖
- 行为评估
- 详细反馈

## 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情
