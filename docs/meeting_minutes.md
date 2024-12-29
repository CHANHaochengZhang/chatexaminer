# Meeting Minutes

## December 20, 2024 - State Machine and Evaluation Discussion

### Attendees
- Tue Herlau (Supervisor)
- Haocheng Zhang (Student)

### Progress Presented
1. State Machine Implementation
   - Demonstrated proof of concept for state machine
   - Implemented OpenAI function calling for state detection
   - Showed basic conversation flow through different states
   - Presented state transitions: INIT -> TOPIC_SELECTED -> QUESTIONING -> EXPLAINING -> EVALUATING

2. Current Features
   - State detection using OpenAI
   - Basic question-answer flow
   - Explanation state handling
   - Pause state for breaks
   - Basic evaluation state

### Discussion Points

1. Student Evaluation System
   - Need to implement multiple evaluation metrics
   - Should track:
     - Number of questions answered
     - Answer accuracy
     - Understanding level
     - Hint request frequency
   - Focus on consistency and fairness in evaluation

2. Student Simulation Suggestions
   - Create different student types for testing:
     - High-performing students
     - Topic-specific strength/weakness students
     - Hint-dependent students
     - Random-answer students (baseline)
   - Use simulations to validate evaluation system

3. State Machine Improvements
   - Consider more flexible state transitions
   - Better handling of student responses in EXPLAINING state
   - Need clear termination conditions:
     - Based on number of questions
     - Based on time/words per question
     - Total examination duration

4. Future Considerations
   - Teacher evaluation metrics
   - System comparison with human teachers
   - Need to focus on student evaluation first
   - Consider consistency in evaluations

### Action Items
1. Integrate question generator with state machine
2. Implement basic evaluation system
3. Create student simulators
4. Prepare demo for next meeting

### Next Meeting
- Date: January 2, 2025
- Focus: Complete system demo from start to grading

### Notes
- Supervisor suggested focusing on student evaluation before teacher evaluation
- Discussion about handling hint mode and student responses
- Agreement to maintain state machine approach for version 1.0
