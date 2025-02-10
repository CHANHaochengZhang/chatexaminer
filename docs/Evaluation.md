# Evaluation System Documentation

## Overview

The evaluation system implements a comprehensive assessment framework for oral examinations, combining real-time response evaluation with cumulative performance tracking.

## Components

| Component | Purpose | Implementation |
|-----------|----------|----------------|
| EvaluationMetrics | Core metrics model | `models/evaluation.py` |
| EvaluationService | Evaluation logic | `services/evaluation_service.py` |
| QuestionEvaluation | Per-question assessment | `models/evaluation.py` |
| ExamEvaluation | Overall exam assessment | `models/evaluation.py` |

## Scoring System

### Per-Question Metrics

| Metric | Weight | Range | Penalty |
|--------|--------|-------|---------|
| Accuracy | 33.3% | 0-100 | - |
| Clarity | 33.3% | 0-100 | - |
| Understanding | 33.3% | 0-100 | - |
| Hint Usage | - | - | -10 per hint |

### Final Score Composition

| Component | Calculation | Description |
|-----------|-------------|-------------|
| Question Score | `(accuracy + clarity + understanding) / 3 * difficulty_weight - hint_penalty` | Base score adjusted by difficulty and hints |
| Difficulty Weight | Level 1: 0.7 (-30%)<br>Level 2: 0.85 (-15%)<br>Level 3: 1.0 (neutral)<br>Level 4: 1.2 (+20%)<br>Level 5: 1.5 (+50%) | Encourages tackling harder questions |
| Hint Penalty | `base_score * 0.05 * hints_used` | 5% deduction per hint |

The final score is calculated as the average of all question scores:
```python
final_score = sum(question_scores) / number_of_questions
```

Each question's score is:
1. Base score: Average of accuracy, clarity, and understanding
2. Weighted by difficulty level
3. Reduced by hint penalties
4. Capped between 0 and 100

## Implementation Details

### 1. Real-time Evaluation
python
async def evaluate_response(
question: Dict,
student_response: str,
hints_used: int,
time_taken: float
) -> QuestionEvaluation

### 2. Difficulty Adjustment

- Uses GPT-4 for response analysis
- Context-aware evaluation using question materials
- Immediate feedback generation

def _adjust_difficulty(metrics: EvaluationMetrics):
    avg_performance = (metrics.accuracy + metrics.understanding) / 2
    if avg_performance > 85:
        increase_difficulty()
    elif avg_performance < 60:
        decrease_difficulty()

### 3. Topic Coverage Tracking
```python
def update_topic_coverage(
    topic: str,
    score: float,
    covered_points: List[str]
)
```

## Performance Metrics

### Behavioral Analysis

| Metric | Threshold | Penalty |
|--------|-----------|---------|
| Response Time | >5 min | -20 points |
| Hint Usage | >2 per question | -20 points |
| Consistency | <70% | -20 points |

### Response Quality Assessment

| Level | Score Range | Characteristics |
|-------|-------------|-----------------|
| Excellent | 85-100 | Complete, accurate, well-expressed |
| Good | 70-84 | Mostly correct, clear expression |
| Fair | 60-69 | Basic understanding shown |
| Poor | <60 | Incomplete or incorrect |

## References

For evaluation methodologies:

```bibtex
@article{hattie2007power,
    title = {The Power of Feedback},
    author = {Hattie, John and Timperley, Helen},
    journal = {Review of Educational Research},
    volume = {77},
    number = {1},
    pages = {81-112},
    year = {2007}
}
```

For adaptive testing:

```bibtex
@book{wainer2000computerized,
    title = {Computerized Adaptive Testing: A Primer},
    author = {Wainer, Howard},
    year = {2000},
    publisher = {Routledge}
}
```

## Future Improvements

1. Enhanced Context Analysis
   - [ ] Implement semantic similarity scoring
   - [ ] Add concept relationship mapping

2. Feedback Refinement
   - [ ] Generate personalized improvement suggestions
   - [ ] Include concept prerequisite tracking

3. Performance Analytics
   - [ ] Add learning curve analysis
   - [ ] Implement progress tracking over multiple sessions

## System Architecture

### Class Diagram
```mermaid
classDiagram
    class ExamService {
        +state_machine: ExamStateMachine
        +evaluation_service: EvaluationService
        +start_exam(topic: str)
        +process_answer(answer: str)
        +get_next_interaction()
        -_adjust_difficulty()
    }

    class EvaluationService {
        +current_evaluation: ExamEvaluation
        +evaluate_response()
        +update_topic_coverage()
        +update_behavior_score()
        +get_final_evaluation()
    }

    class ExamStateMachine {
        +current_state: ExamState
        +context: Dict
        +transition(state: ExamState)
        +get_current_question()
    }

    class EvaluationMetrics {
        +accuracy: float
        +clarity: float
        +understanding: float
        +hints_used: int
    }

    class QuestionEvaluation {
        +question_id: str
        +metrics: EvaluationMetrics
        +feedback: str
        +difficulty: int
        +time_taken: float
    }

    class ExamEvaluation {
        +total_score: float
        +question_evaluations: Dict
        +topic_coverage: Dict
        +behavior_score: float
        +calculate_total_score()
    }

    ExamService --> ExamStateMachine
    ExamService --> EvaluationService
    EvaluationService --> ExamEvaluation
    ExamEvaluation --> QuestionEvaluation
    QuestionEvaluation --> EvaluationMetrics
```

### Run Exam Flow
```mermaid
sequenceDiagram
    participant U as User
    participant R as run_exam.py
    participant E as ExamService
    participant S as StateMachine
    participant V as EvaluationService

    U->>R: Start Exam
    R->>E: Create ExamService
    R->>U: Request Topic
    U->>R: Input Topic
    R->>E: start_exam(topic)
    E->>S: start_exam(topic)
    S-->>E: QUESTIONING State
    E-->>R: First Question
    R->>U: Display Question

    loop Question-Answer
        U->>R: Submit Answer
        R->>E: process_answer(answer)
        E->>V: evaluate_response()
        V-->>E: Evaluation Result
        E->>S: Update State/Difficulty
        E->>R: Next Question/Complete
        R->>U: Display Result
    end

    U->>R: End Exam
    R->>E: Generate Final Evaluation
    E->>V: get_final_evaluation()
    V-->>E: Final Report
    E-->>R: Complete Report
    R->>U: Display Final Results
```

### State Transitions
```mermaid
stateDiagram-v2
    [*] --> INIT
    INIT --> TOPIC_SELECTED: Select Topic
    TOPIC_SELECTED --> QUESTIONING: Start Exam
    QUESTIONING --> QUESTIONING: Answer Question
    QUESTIONING --> EXPLAINING: Need Explanation
    EXPLAINING --> QUESTIONING: Understanding Confirmed
    QUESTIONING --> EVALUATING: End Command/All Questions Done
    EVALUATING --> COMPLETED: Report Generated
    COMPLETED --> [*]
```

These figures demonstrate:
1. The relationships and dependencies between system components
2. The flow of interactions during an exam
3. The complete state transitions

Each component has a clear role:
- `run_exam.py`: The user interface
- `ExamService`: The core business logic coordinator
- `StateMachine`: The state manager
- `EvaluationService`: The answer evaluation and score calculation

## Evaluation Models

### 1. Core Metrics
```python
class EvaluationMetrics:
    accuracy: float      # 0-100: Correctness of the answer
    clarity: float      # 0-100: Clarity of expression
    understanding: float # 0-100: Depth of concept understanding
    hints_used: int     # Number of hints requested
```

### 2. Question Evaluation
```python
class QuestionEvaluation:
    question_id: str
    metrics: EvaluationMetrics
    feedback: str
    difficulty: int     # 1-5
    time_taken: float   # in seconds
    raw_response: str
```

### 3. Complete Exam Evaluation
```python
class ExamEvaluation:
    total_score: float
    question_evaluations: Dict[str, QuestionEvaluation]
    topic_coverage: Dict[str, float]
    behavior_score: float
    final_feedback: str
```

## Evaluation Process

### 1. Individual Question Assessment
- **Timing**: Evaluated immediately after each answer submission
- **Metrics Evaluated**:
  - Accuracy (correctness of content)
  - Clarity (expression quality)
  - Understanding (concept comprehension)
- **Adjustments**:
  - Hint penalty: -10 points per hint used
  - Difficulty weighting: Score weighted by question difficulty (1-5)

### 2. Topic Coverage Assessment
- Tracks knowledge points covered
- Measures depth and breadth of topic understanding
- Calculates percentage of topic points addressed

### 3. Behavioral Assessment
Evaluates student behavior during the exam:
```python
behavior_score = (
    (1 - avg_hints_per_question * 0.1)    # Hint usage impact
    * response_consistency                 # Answer consistency
    * (1 - min(1, avg_time_per_question / 300))  # Time management
) * 100
```

## Scoring Algorithm

### Final Score Components
1. **Question Performance (60%)**
   ```python
   question_score = (accuracy + clarity + understanding) / 3
   question_score -= hints_used * 10
   question_score *= difficulty / 5
   ```

2. **Topic Coverage (20%)**
   - Based on percentage of topic points covered
   - Weighted by importance of each topic

3. **Behavioral Score (20%)**
   - Hint usage efficiency
   - Time management
   - Response consistency

### Score Calculation
```python
def calculate_total_score(self) -> float:
    # Question component (60%)
    question_scores = []
    for eval in question_evaluations:
        # Calculate base score
        base_score = (eval.metrics.accuracy + eval.metrics.clarity +
                     eval.metrics.understanding) / 3

        # Apply difficulty weights
        difficulty_weights = {
            1: 0.7,   # Easy (-30%)
            2: 0.85,  # Basic (-15%)
            3: 1.0,   # Medium (neutral)
            4: 1.2,   # Advanced (+20%)
            5: 1.5    # Expert (+50%)
        }

        # Apply difficulty weight
        weighted_score = base_score * difficulty_weights[eval.difficulty]

        # Apply hint penalty (5% of base score per hint)
        hint_penalty = (base_score * 0.05) * eval.metrics.hints_used
        score = weighted_score - hint_penalty

        # Ensure score stays within 0-100 range
        score = max(0, min(100, score))
        question_scores.append(score)

    question_component = avg(question_scores) * 0.6

    # Topic coverage (20%)
    topic_component = avg(topic_coverage.values()) * 20

    # Behavior component (20%)
    behavior_component = behavior_score * 0.2

    return question_component + topic_component + behavior_component
```

## GPT-Based Evaluation

### Evaluation Prompt Template
```
Evaluate this student's answer based on the following criteria:

Question: {question}
Expected Answer: {expected_answer}
Student's Answer: {student_response}

Please evaluate on three metrics (0-100):
1. Accuracy: How correct is the answer?
2. Clarity: How well is it expressed?
3. Understanding: How well does the student understand the concept?

Provide brief feedback explaining the evaluation.
```

### Response Format
```json
{
    "accuracy": 85,
    "clarity": 90,
    "understanding": 80,
    "feedback": "Demonstrates good understanding but could provide more detailed examples..."
}
```
## Evaluation Report

### Report Components
1. **Overall Score**
   - Final weighted score
   - Component breakdowns

2. **Question-by-Question Analysis**
   - Individual scores
   - Specific feedback
   - Time taken
   - Hints used

3. **Topic Coverage Analysis**
   - Coverage percentage
   - Strength/weakness areas
   - Knowledge gaps

4. **Behavioral Metrics**
   - Total exam time
   - Average time per question
   - Hint usage patterns
   - Response consistency

## Implementation Notes

### Key Features
1. **Multi-dimensional Assessment**
   - Beyond simple right/wrong evaluation
   - Considers expression and understanding
   - Behavioral analysis integration

2. **Dynamic Weighting**
   - Difficulty-based adjustment
   - Progressive scoring system
   - Behavioral impact consideration

3. **Comprehensive Feedback**
   - Detailed per-question feedback
   - Overall performance analysis
   - Improvement suggestions

### Best Practices
1. **Evaluation Timing**
   - Immediate question evaluation
   - Progressive score calculation
   - Final review phase

2. **Data Persistence**
   - Secure evaluation storage
   - Session state management
   - Progress tracking

3. **Error Handling**
   - Incomplete answer handling
   - Timeout management
   - State transition validation

## Future Improvements

1. **Enhanced Metrics**
   - More sophisticated hint penalty system
   - Advanced behavioral analytics
   - Machine learning-based evaluation

2. **Reporting Enhancements**
   - Interactive visualization
   - Trend analysis
   - Comparative assessment

3. **System Integration**
   - Real-time feedback
   - Progress monitoring
   - Learning path recommendations
