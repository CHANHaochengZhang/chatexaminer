# ChatExaminer Frontend Development Documentation

## Layout Design

### Overall Layout
- Responsive design, mainly divided into two views:
  1. Initial state (topic selection)
  2. Exam in progress state (column layout)

### Component Structure
```
Exam.vue (Main View)
├── Initial State
│   └── Topic Selection Form
└── Exam State
    ├── Left Panel
    │   ├── StatePanel (Status Panel)
    │   └── EvalReport (Evaluation Report, only shown in completed state)
    └── Right Panel
        └── ExamChat (Chat Interface)
```

### Component Details

#### StatePanel (Status Panel)
- Display current exam state
- Display number of questions answered
- Display number of hints used
- Display current difficulty level
- Use Element Plus Card and Tag components

#### ExamChat (Chat Interface)
- Message list display
  - Support system messages, user messages and assistant messages
  - Different styles for different roles
  - Display sent time
- Input area
  - Text input box
  - Send button
  - Support Enter to send
- Auto-scroll to latest message

#### EvalReport (Evaluation Report)
- Total score display
- Topic coverage tags
- Strengths list
- Weaknesses list
- Suggestions list

## State Management

### Exam States
```typescript
type ExamState = 'INIT' | 'TOPIC_SELECTED' | 'QUESTIONING' | 'EXPLAINING' | 'EVALUATING' | 'COMPLETED' | 'CHAT'
```

### Data Flow
1. Start Exam
   - User inputs topic
   - Call API to create session
   - Establish WebSocket connection
   - Update state and display initial message

2. Exam Process
   - User sends message
   - Receive response via WebSocket
   - Update state and message list
   - Dynamically update statistics

3. Complete Evaluation
   - Get evaluation report
   - Display detailed evaluation information

## API Services

### ExamService Class
- Manage communication with backend
- Maintain exam session state
- Handle WebSocket connection
- Methods:
  - startExam
  - submitAnswer
  - getExamState
  - getEvaluation
  - connectWebSocket
  - clearSession

## Style Design

### Theme Variables
```scss
:root {
  --primary-color: #409eff;
  --background-color: #f5f7fa;
  --text-color: #303133;
  --spacing-md: 16px;
}
```

### Layout Features
- Use CSS Grid for column layout
- Fixed sidebar width (300px)
- Adaptive main content area
- Uniform spacing and rounded corners
- Shadow effects to enhance layering

## Development Records

### 2024-01-26
1. Initialize Project
   - Use Vue 3 + TypeScript + Vite
   - Configure Element Plus UI library
   - Set up routing and state management

2. Implement Basic Components
   - Create main view Exam.vue
   - Implement status panel component
   - Implement chat interface component
   - Implement evaluation report component

3. Configure API Services
   - Implement ExamService class
   - Configure WebSocket connection
   - Handle session management

4. Optimize User Experience
   - Add loading states
   - Improve error handling
   - Optimize message display
   - Implement auto-scrolling

### To-Do Items
- [ ] Add message retry mechanism
- [ ] Implement reconnection
- [ ] Optimize mobile adaptation
- [ ] Add theme switching functionality
- [ ] Add animation effects

## Data Flow Diagram

```mermaid
sequenceDiagram
    participant User
    participant FE as Frontend App
    participant WS as WebSocket
    participant API as RESTful API
    participant BE as Backend Service

    User->>FE: Select topic
    FE->>API: startExam(topic)
    API->>BE: Create exam session
    BE-->>API: Return sessionId
    API-->>FE: Return session info
    FE->>WS: Establish WebSocket connection
    WS-->>FE: Connection confirmation
    FE->>FE: Update state to TOPIC_SELECTED

    User->>FE: Start exam
    FE->>WS: Send start exam message
    WS->>BE: Relay message
    BE->>BE: Update state to QUESTIONING
    BE-->>WS: Send first question
    WS-->>FE: Receive question
    FE->>FE: Display question

    User->>FE: Submit answer
    FE->>WS: Send answer
    WS->>BE: Relay answer
    BE->>BE: Evaluate answer
    BE-->>WS: Send evaluation and next question
    WS-->>FE: Receive response
    FE->>FE: Update interface

    User->>FE: Request hint
    FE->>WS: Send hint request
    WS->>BE: Relay request
    BE->>BE: Generate hint
    BE-->>WS: Send hint
    WS-->>FE: Receive hint
    FE->>FE: Display hint

    User->>FE: Complete all questions
    BE->>BE: Update state to EVALUATING
    BE->>BE: Generate final evaluation
    BE-->>WS: Send evaluation report
    WS-->>FE: Receive report
    FE->>FE: Update state to COMPLETED
    FE->>FE: Display evaluation report
```

## Responsive Layout Diagram

Showing frontend layout changes across different screen sizes:

```mermaid
graph TD
    subgraph Desktop Layout
    A[Left Panel\n30% width] --- B[Right Panel\n70% width]
    end

    subgraph Tablet Layout
    C[Left Panel\n40% width] --- D[Right Panel\n60% width]
    end

    subgraph Mobile Layout
    E[Top Panel\nStatus Info] --- F[Middle Panel\nChat Area]
    F --- G[Bottom Panel\nInput Area]
    H[Evaluation Button] --- I[Fullscreen Evaluation Report]
    end
```

## Other Suggestions

1. **Interface Screenshots**: In addition to diagrams, it's recommended to add actual interface screenshots to show UI in different states

2. **Interactive Prototype Link**: A Figma or other prototype tool link can be added for team members to reference complete interactions

3. **Component State Change Diagram**: Show how main components change in different states

```mermaid
stateDiagram-v2
    direction LR
    [*] --> Default
    Default --> Loading: Submit Answer
    Loading --> Success: Receive Response
    Loading --> Error: Network Error
    Success --> Default: After 3 seconds
    Error --> Retry: Click Retry
    Retry --> Loading: Resend
    Error --> Default: Cancel
```

4. **User Experience Flow Chart**: Show complete user journey

```mermaid
journey
    title Student Experience with ChatExaminer
    section Preparation Phase
      Access System: 5: Student
      Review Introduction: 4: Student
      Select Topic: 5: Student
    section Examination Phase
      Answer Questions: 3: Student
      Request Hints: 4: Student
      Continue Answering: 3: Student
    section Evaluation Phase
      View Immediate Feedback: 5: Student
      Complete Exam: 5: Student
      Review Overall Assessment: 4: Student
```

## Implementation Suggestions

1. Add these visual charts to the corresponding sections of the existing document, do not delete the original content

2. Consider using actual interface screenshots to supplement abstract charts

3. Add interface previews for different devices and states

4. Add development roadmap, showing frontend future iteration plan

These visual enhancements will make the document more intuitive and easier to understand for new developers, while also better showing frontend interaction and design ideas.

## Technology Stack Diagram

```mermaid
graph TD
    subgraph Frontend
    A[Vue 3] --- B[TypeScript]
    B --- C[Vite]
    C --- D[Element Plus]
    D --- E[SCSS]
    end

    subgraph Communication
    F[WebSocket] --- G[RESTful API]
    G --- H[Axios]
    end

    subgraph State Management
    I[Pinia] --- J[Vue Router]
    end

    A --- F
    A --- I
```

## Development Roadmap

```mermaid
gantt
    title ChatExaminer Frontend Development Roadmap
    dateFormat  YYYY-MM-DD

    section Phase 1
    Initial Setup           :done, 2024-01-24, 3d
    Core Components         :done, 2024-01-26, 7d

    section Phase 2
    API Integration         :active, 2024-02-01, 14d
    Responsive Design       :2024-02-10, 10d

    section Phase 3
    Testing & Optimization  :2024-02-20, 14d
    User Experience Polish  :2024-03-01, 10d

    section Future
    Offline Support         :2024-03-15, 14d
    Multi-language Support  :2024-03-25, 21d
    Analytics Integration   :2024-04-10, 14d
```

## Implementation Suggestions

1. Integrate these English charts into the existing document, replacing the original Chinese charts

2. Consider adding actual interface screenshots, and show actual effects with each chart

3. Add interface preview for different devices and states

4. Ensure that the English terms in the charts are consistent with the variable and function names used in the code library

These visual contents will greatly improve the readability and professionalism of the document, while maintaining the clear contrast between Chinese descriptions and English technical tables.
