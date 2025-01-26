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
