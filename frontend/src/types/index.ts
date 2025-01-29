export type ExamState =
  | 'INIT'
  | 'TOPIC_SELECTED'
  | 'QUESTIONING'
  | 'EXPLAINING'
  | 'EVALUATING'
  | 'COMPLETED'
  | 'CHAT'

export interface Message {
  role: 'system' | 'assistant' | 'user'
  content: string
  timestamp?: number
}

export interface ExamSession {
  sessionId: string
  currentState: ExamState
  messages: Message[]
  questionsAnswered: number
  hintsUsed: number
  currentDifficulty: number
  evaluation?: EvaluationReport
}

export interface EvaluationReport {
  totalScore: number
  questionsAnswered: number
  topicCoverage: string[]
  strengths: string[]
  weaknesses: string[]
  suggestions: string[]
}

export interface ProgressReport {
  stats: {
    questions_answered: number
    hints_requested: number
    current_difficulty: number
    current_state: ExamState
  }
  current_score: number
  topic_progress: {
    [topic: string]: {
      coverage: number
      score: number
    }
  }
  recent_evaluations: Array<{
    question_id: string
    score: {
      accuracy: number
      clarity: number
      understanding: number
    }
    feedback: string
    time_taken: number
  }>
  behavior_metrics: {
    avg_time_per_question: number
    hint_usage_rate: number
    response_consistency: number
  }
}
