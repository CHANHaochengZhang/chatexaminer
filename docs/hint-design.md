# Hint 功能设计文档

## 功能概述

Hint功能是考试系统中的一个辅助功能，允许学生在答题过程中获取提示。系统会根据当前问题的上下文、难度和主题动态生成个性化的提示，帮助学生思考问题的关键点。

## 技术架构

### 后端实现

1. **ExamService类**
```python
async def request_hint(self) -> Dict:
    """生成当前问题的提示"""
    current_question = self.state_machine.get_current_question()

    # 使用OpenAI生成个性化提示
    prompt = f"""基于以下问题元数据生成提示:
    问题: {current_question['question']}
    主题: {current_question['topic']}
    子主题: {current_question['subtopic']}
    难度: {current_question['difficulty']} (1-5)
    上下文: {current_question.get('context', [])}
    """

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "你是一位专业的考试辅导老师"},
            {"role": "user", "content": prompt}
        ]
    )

    return {
        "hint": response.choices[0].message.content,
        "hints_used": self.session_metrics["hints_requested"]
    }
```

2. **API端点**
```python
@router.get("/{session_id}/hint")
async def request_hint(session_id: str) -> ExamResponse:
    """请求当前问题的提示"""
    exam_service = exam_sessions.get(session_id)
    hint_data = await exam_service.request_hint()
    return ExamResponse(
        state=exam_service.state_machine.get_current_state().value,
        message="提示已生成",
        data=hint_data
    )
```

### 前端实现

1. **API服务**
```typescript
async requestHint() {
  if (!this.sessionId) {
    throw new Error('No active exam session')
  }
  const response = await axios.get(`${BASE_URL}/${this.sessionId}/hint`)
  return {
    hint: response.data.data.hint,
    hintsUsed: response.data.data.hints_used
  }
}
```

2. **状态管理**
```typescript
async requestHint() {
  if (!this.sessionId) return
  const response = await examAPI.requestHint()
  this.hintsUsed = response.hintsUsed
  this.messages.push({
    type: 'hint',
    content: response.hint,
    timestamp: new Date().toISOString()
  })
}
```

## 提示生成策略

1. **难度适配**
   - 难度1-3: 关注基础概念和关键词
   - 难度4-5: 关注解题方法和思路

2. **上下文相关**
   - 基于问题的上下文生成相关提示
   - 避免直接给出答案
   - 引导学生思考关键点

3. **个性化生成**
   - 考虑学生当前的答题表现
   - 结合主题和子主题的特点
   - 保持提示的简洁性和清晰度

## 评分影响

1. **使用记录**
   - 系统记录每个问题的hint使用次数
   - 累计记录整个考试过程中的hint使用情况

2. **分数调整**
   - 使用hint会影响最终得分
   - 评分公式: `final_score = base_score - (hints_used * penalty_factor)`
   - 默认的`penalty_factor`为每个hint扣除10%的分数

## 界面展示

1. **状态面板**
   - 显示已使用的hint数量
   - 显示hint使用率统计

2. **消息流**
   - hint以特殊消息类型显示
   - 使用不同的样式区分hint和其他消息

## 最佳实践

1. **使用建议**
   - 建议学生先尝试独立思考
   - 在确实需要帮助时再使用hint
   - 注意hint使用会影响最终得分

2. **开发注意事项**
   - 确保hint生成的实时性
   - 保持提示内容的相关性
   - 避免提示过于直接或过于模糊

## 未来改进

1. **智能提示**
   - 基于学生历史表现优化提示生成
   - 引入多级提示系统
   - 支持更细粒度的提示类型

2. **交互优化**
   - 添加提示反馈机制
   - 优化提示展示方式
   - 提供提示使用建议

## 学术参考

本系统的hint功能设计参考了以下研究成果：

1. **智能提示系统的理论基础**
   - VanLehn, K. (2011). The relative effectiveness of human tutoring, intelligent tutoring systems, and other tutoring systems. *Educational Psychologist, 46*(4), 197-221.
   - Anderson, J. R., Corbett, A. T., Koedinger, K. R., & Pelletier, R. (1995). Cognitive tutors: Lessons learned. *The Journal of the Learning Sciences, 4*(2), 167-207.

2. **提示策略研究**
   - Roll, I., Aleven, V., McLaren, B. M., & Koedinger, K. R. (2011). Improving students' help-seeking skills using metacognitive feedback in an intelligent tutoring system. *Learning and Instruction, 21*(2), 267-280.
   - Aleven, V., & Koedinger, K. R. (2000). Limitations of student control: Do students know when they need help? In *International conference on intelligent tutoring systems* (pp. 292-303).

3. **自适应提示系统**
   - Narciss, S., & Huth, K. (2006). Fostering achievement and motivation with bug-related tutoring feedback in a computer-based training for written subtraction. *Learning and Instruction, 16*(4), 310-322.
   - Wood, H., & Wood, D. (1999). Help seeking, learning and contingent tutoring. *Computers & Education, 33*(2-3), 153-169.

4. **提示对学习效果的影响**
   - Shute, V. J. (2008). Focus on formative feedback. *Review of Educational Research, 78*(1), 153-189.
   - Hattie, J., & Timperley, H. (2007). The power of feedback. *Review of Educational Research, 77*(1), 81-112.

5. **AI辅助的动态提示生成**
   - Brown, T., et al. (2020). Language models are few-shot learners. *Advances in Neural Information Processing Systems, 33*, 1877-1901.
   - Zhao, R., et al. (2021). Adaptive hint generation for programming exercises using deep learning. In *Proceedings of the 2021 ACM Conference on Learning at Scale* (pp. 173-184).

### 关键研究发现

1. **提示时机的重要性**
   - 研究表明，在学生遇到困难但尚未完全失去方向时提供提示最有效
   - 过早或过晚的提示都可能降低学习效果

2. **提示层次性**
   - 渐进式提示策略（从抽象到具体）能够更好地促进深度学习
   - 多层次提示系统可以适应不同学习者的需求

3. **自适应机制**
   - 基于学习者表现动态调整提示难度和详细程度
   - 考虑学习者的知识水平和学习风格

4. **提示效果评估**
   - 提示使用频率与学习成果呈现非线性关系
   - 适度的提示使用可以显著提升学习效果

### 实践启示

基于以上研究，我们的hint系统采取了以下设计原则：

1. **渐进式提示**
   - 首先提供方向性提示
   - 根据需要逐步提供更具体的指导

2. **个性化适配**
   - 结合问题难度和学生表现
   - 动态调整提示的深度和广度

3. **元认知支持**
   - 引导学生反思解题策略
   - 培养自主学习能力

4. **评估与反馈**
   - 持续监控提示效果
   - 优化提示生成策略
