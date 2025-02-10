# Meeting Minutes

## February 6, 2025 - Evaluation System and Thesis Discussion

### Attendees
- Tue Herlau (Supervisor)
- Haocheng Zhang (Student)

### Progress Presented
1. Evaluation System Status
   - Single question evaluation works well
   - Overall grading needs improvement (current test shows 4.75/100)
   - Using GPT-4o-mini for answer verification
   - Implemented context-aware evaluation

### Discussion Points

1. Evaluation System Approach
   - Focus on distinguishing different levels of understanding rather than exact scores
   - Create artificial students with defined behaviors:
     - High-performing students (80% understanding)
     - Topic-specific strength/weakness students
     - Hint-dependent students
     - Confused/nervous students
   - Implement state machines for both examiner and students

2. Testing Framework
   - Create rigorous experiments to validate system
   - Test examiner's ability to handle different student behaviors
   - Focus on measuring:
     - Response consistency
     - Time taken per question
     - Hint usage patterns
     - Understanding progression

3. Thesis Structure and Writing
   - Use DTU thesis template
   - Focus on research questions as backbone
   - Write for technical audience but explain concepts clearly
   - Include literature review of existing AI examiners
   - Start with draft notes and figures
   - First two pages crucial for setting expectations

### Action Items
1. Implement artificial student behaviors
2. Create testing framework for examiner-student interactions
3. Begin thesis draft within two weeks
4. Research existing AI examiner systems

### Key Solutions Proposed
1. State Machine Testing:
   - Create paired state machines (examiner and student)
   - Test interactions between different student types and examiner
   - Validate system robustness through varied scenarios

2. Evaluation Framework:
   - Focus on relative performance rather than absolute scores
   - Track progression over time for different student types
   - Measure examiner's ability to adapt to student needs

3. Documentation Strategy:
   - Focus on experimental validation
   - Document system's ability to distinguish student types
   - Emphasize robustness testing results

### Next Meeting
- Date: February 13, 2025
- Focus: Review artificial student implementation and testing framework

### Notes
- Project deadline: March 25, 2025 (40 days remaining)
- Consider including local LLM testing results
- Focus on scientific rigor rather than machine learning aspects


## January 30, 2025 - GUI Progress and Evaluation System Discussion

### Attendees
- Tue Herlau (Supervisor)
- Haocheng Zhang (Student)

### Progress Presented
1. GUI Implementation
   - Completed basic examination interface
   - Implemented real-time evaluation display
   - Created basic API endpoints
   - Demonstrated working chat-based examination flow

2. Current Features
   - Live evaluation reporting
   - Topic selection interface
   - State-based conversation flow
   - Basic evaluation metrics

### Discussion Points

1. Evaluation System Improvements
   - Proposed coarse-grained scoring system (0-2 points)
   - Need clear examples for each score level
   - Focus on ranking preservation rather than exact scores
   - Include reference answers in evaluation prompt

2. Student Simulation Development
   - Create AI-powered student simulators:
     - High-performing student template
     - Poor-performing student template
   - Implement probability-based mixing (e.g., 80/20 split)
   - Use for system validation and testing

3. Technical Improvements
   - Refine function calling implementation
   - Improve state management approach
   - Better prompt engineering for evaluation
   - Focus on structured output generation

4. Project Focus
   - Prioritize student evaluation system
   - Postpone teacher evaluation component
   - Focus on creating reproducible experiments
   - Prepare for results section of report

### Action Items
1. Implement student simulator system
2. Refine evaluation metrics to coarse-grained scale
3. Improve state management system
4. Prepare initial experiments for system validation

### Next Meeting
- Date: February 6, 2025
- Focus: Review student simulation results and evaluation metrics

### Notes
- Supervisor suggested focusing on artificial student testing rather than real student recruitment
- Agreement to maintain focus on evaluation system before expanding scope
- Discussion about handling function calling instability

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
