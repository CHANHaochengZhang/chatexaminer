# AI Examiner Dialogue System

## Overview
The AI Examiner implements an intelligent dialogue system for conducting oral examinations. The system uses OpenAI Function Calling for state transitions and evaluations.

## Dialogue System Architecture

```mermaid
stateDiagram-v2
    [*] --> INIT

    INIT --> PREPARATION: student_not_ready
    PREPARATION --> INIT: need_more_preparation
    PREPARATION --> TOPIC_SELECTED: student_ready

    INIT --> TOPIC_SELECTED: student_ready
    note right of INIT
        Initial difficulty = 3
        Check student readiness
    end note

    TOPIC_SELECTED --> QUESTIONING: start_exam()
    note right of TOPIC_SELECTED
        Loads pre-generated questions
        for selected topic
    end note

    QUESTIONING --> EXPLAINING: intention="need_clarification"
    EXPLAINING --> QUESTIONING: provide_explanation()
    note right of EXPLAINING
        Tracks hint requests
        Affects final evaluation
    end note

    QUESTIONING --> QUESTIONING: evaluate_response()/\nselect_next_question()
    note right of QUESTIONING
        Response evaluation:
        - Score (1-5)
        - Understanding level
        - Updates difficulty
    end note

    QUESTIONING --> EVALUATING: questions_completed
    note right of EVALUATING
        Accumulates:
        - Question scores
        - Hint requests
        - Response patterns
    end note

    EVALUATING --> COMPLETED: generate_final_evaluation()

    COMPLETED --> [*]
```

## State Descriptions

### 1. INIT
- Initialize examination session
- Check student readiness
- Load question bank and topics

### 2. PREPARATION
- Handle pre-exam questions
- Explain exam procedures
- Confirm language preferences
- Check student comfort level

### 3. TOPIC_SELECTED
- Randomly select topic and subtopic
- Load relevant pre-generated questions
- Prepare evaluation criteria

### 4. QUESTIONING
- Core examination state
- Dynamic question selection based on:
  - Current difficulty level
  - Student performance
  - Question history
- Immediate evaluation of each response

### 5. EXPLAINING
- Provide concept explanations and hints
- Track hint request frequency
- Ensure no answer disclosure
- Hint requests affect final score

### 6. EVALUATING
- Comprehensive assessment of all responses
- Consider hint request frequency
- Generate detailed feedback

### 7. COMPLETED
- Generate final evaluation report
- Save conversation history
- Provide improvement suggestions

## Implementation Notes

### State Transitions
Using OpenAI Function Calling for state transitions:
```python
{
    "intention": int,  # Dialog intention type
    "evaluation": int, # Response score (1-5)
    "metadata": {
        "hint_requested": bool,
        "difficulty": int,
        "topic": str,
        "subtopic": str,
        "student_ready": bool
    }
}
```

### Evaluation Criteria
- Concept accuracy (40%)
- Understanding depth (30%)
- Expression clarity (20%)
- Technical terminology usage (10%)
- Hint request frequency (affects final score)
