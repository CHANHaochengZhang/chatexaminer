export type ExamState = 'INIT' | 'TOPIC_SELECTED' | 'QUESTIONING' | 'EXPLAINING' | 'EVALUATING' | 'COMPLETED' | 'CHAT';

export interface StatePanelProps {
  currentState: ExamState;
  questionsAnswered: number;
  hintsUsed: number;
  currentDifficulty: number;
}
