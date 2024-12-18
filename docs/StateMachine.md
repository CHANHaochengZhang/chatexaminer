# AI Examiner Dialogue System

## Overview
The AI Examiner implements an intelligent dialogue system for conducting oral examinations. The system uses OpenAI Function Calling for state transitions and evaluations.

## Dialogue System Architecture

```mermaid
stateDiagram-v2
    [*] --> INIT

    INIT --> TOPIC_SELECTED: student_ready
    note right of INIT
        Initial difficulty = 3
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

    QUESTIONING --> PAUSED: student_needs_break
    PAUSED --> QUESTIONING: resume_exam
    note right of PAUSED
        Handles:
        - Break requests
        - Technical issues
        - Other interruptions
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
- Load question bank and topics

### 2. TOPIC_SELECTED
- Randomly select topic and subtopic
- Load relevant pre-generated questions
- Prepare evaluation criteria

### 3. QUESTIONING
- Core examination state
- Dynamic question selection
- Immediate response evaluation
- Can be paused if needed

### 4. EXPLAINING
- Provide concept explanations
- Track hint requests
- Ensure no answer disclosure

### 5. PAUSED
- Handle temporary interruptions
- Maintain exam progress
- Allow for breaks and technical issues
- Resume capability

### 6. EVALUATING
- Comprehensive assessment
- Consider hint requests
- Generate detailed feedback

### 7. COMPLETED
- Generate final report
- Save conversation history
- Provide suggestions

## Implementation Notes

### State Transitions
Using OpenAI Function Calling:
```python
{
    "intention": int,     # Dialog intention type
    "evaluation": int,    # Response score (1-5)
    "metadata": {
        "hint_requested": bool,
        "difficulty": int,
        "topic": str,
        "pause_reason": str,  # New field
        "resume_time": int    # New field
    }
}
```

### Evaluation Criteria
- Concept accuracy (40%)
- Understanding depth (30%)
- Expression clarity (20%)
- Technical terminology (10%)
- Hint requests (affects score)
