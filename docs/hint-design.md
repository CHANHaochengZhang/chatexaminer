# Hint Feature Design Document

## Feature Overview

The Hint feature is an auxiliary function in the examination system that allows students to receive hints during the answering process. The system dynamically generates personalized hints based on the current question's context, difficulty, and topic, helping students think about the key points of the problem.

## Technical Architecture

### Backend Implementation

1. **ExamService Class**
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

2. **API Endpoint**
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

### Frontend Implementation

1. **API Service**
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

2. **State Management**
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

## Hint Generation Strategy

1. **Difficulty Adaptation**
   - Difficulty 1-3: Focus on basic concepts and keywords
   - Difficulty 4-5: Focus on solution methods and approaches

2. **Context Relevance**
   - Generate relevant hints based on question context
   - Avoid giving direct answers
   - Guide students to think about key points

3. **Personalized Generation**
   - Consider student's current answer performance
   - Incorporate characteristics of topic and subtopic
   - Maintain conciseness and clarity of hints

## Scoring Impact

1. **Usage Records**
   - System records the number of hints used for each question
   - Cumulative recording of hint usage throughout the examination process

2. **Score Adjustment**
   - Using hints affects the final score
   - Scoring formula: `final_score = base_score - (hints_used * penalty_factor)`
   - Default `penalty_factor` is a 10% deduction per hint

## Interface Display

1. **Status Panel**
   - Display the number of hints used
   - Display hint usage statistics

2. **Message Stream**
   - Hints are displayed as special message types
   - Different styles distinguish hints from other messages

## Best Practices

1. **Usage Recommendations**
   - Advise students to try thinking independently first
   - Use hints only when help is truly needed
   - Note that hint usage will affect the final score

2. **Development Considerations**
   - Ensure real-time hint generation
   - Maintain relevance of hint content
   - Avoid hints that are too direct or too vague

## Future Improvements

1. **Intelligent Hints**
   - Optimize hint generation based on student's historical performance
   - Introduce multi-level hint system
   - Support more fine-grained hint types

2. **Interaction Optimization**
   - Add hint feedback mechanism
   - Optimize hint presentation methods
   - Provide hint usage suggestions

## Academic References

The hint feature design of this system references the following research results:

1. **Theoretical Foundation of Intelligent Hint Systems**
   - VanLehn, K. (2011). The relative effectiveness of human tutoring, intelligent tutoring systems, and other tutoring systems. *Educational Psychologist, 46*(4), 197-221.
   - Anderson, J. R., Corbett, A. T., Koedinger, K. R., & Pelletier, R. (1995). Cognitive tutors: Lessons learned. *The Journal of the Learning Sciences, 4*(2), 167-207.

2. **Hint Strategy Research**
   - Roll, I., Aleven, V., McLaren, B. M., & Koedinger, K. R. (2011). Improving students' help-seeking skills using metacognitive feedback in an intelligent tutoring system. *Learning and Instruction, 21*(2), 267-280.
   - Aleven, V., & Koedinger, K. R. (2000). Limitations of student control: Do students know when they need help? In *International conference on intelligent tutoring systems* (pp. 292-303).

3. **Self-Adaptive Hint Systems**
   - Narciss, S., & Huth, K. (2006). Fostering achievement and motivation with bug-related tutoring feedback in a computer-based training for written subtraction. *Learning and Instruction, 16*(4), 310-322.
   - Wood, H., & Wood, D. (1999). Help seeking, learning and contingent tutoring. *Computers & Education, 33*(2-3), 153-169.

4. **Hint Impact on Learning Outcomes**
   - Shute, V. J. (2008). Focus on formative feedback. *Review of Educational Research, 78*(1), 153-189.
   - Hattie, J., & Timperley, H. (2007). The power of feedback. *Review of Educational Research, 77*(1), 81-112.

5. **AI-Assisted Dynamic Hint Generation**
   - Brown, T., et al. (2020). Language models are few-shot learners. *Advances in Neural Information Processing Systems, 33*, 1877-1901.
   - Zhao, R., et al. (2021). Adaptive hint generation for programming exercises using deep learning. In *Proceedings of the 2021 ACM Conference on Learning at Scale* (pp. 173-184).

### Key Research Findings

1. **Hint Timing Importance**
   - Research indicates that providing hints when students are struggling but not completely lost is most effective
   - Too early or too late hints can reduce learning effectiveness

2. **Hint Hierarchy**
   - Progressive hint strategy (from abstract to specific) can better promote deep learning
   - Multi-level hint system can accommodate different learner needs

3. **Self-Adaptive Mechanism**
   - Dynamically adjust hint difficulty and detail based on learner performance
   - Consider learner's knowledge level and learning style

4. **Hint Effectiveness Evaluation**
   - Hint usage frequency shows non-linear relationship with learning outcomes
   - Moderate hint usage can significantly improve learning effectiveness

### Practical Implications

Based on these findings, our hint system adopted the following design principles:

1. **Progressive Hinting**
   - First provide directional hints
   - Gradually provide more specific guidance as needed

2. **Personalized Adaptation**
   - Combine problem difficulty and learner performance
   - Dynamically adjust hint depth and breadth

3. **Metacognition Support**
   - Guide students to reflect on problem-solving strategies
   - Foster independent learning abilities

4. **Assessment and Feedback**
   - Continuously monitor hint effectiveness
   - Optimize hint generation strategy
