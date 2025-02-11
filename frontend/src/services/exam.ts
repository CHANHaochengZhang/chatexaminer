import axios from 'axios'
import type { Message, ExamState, EvaluationReport, ProgressReport } from '@/types'

const BASE_URL = '/api/exam'
const WS_BASE_URL = 'ws://localhost:8000/api/exam'

export interface QuestionEvaluation {
  question_id: string
  score: {
    accuracy: number
    clarity: number
    understanding: number
  }
  feedback: string
  time_taken: number
}

export interface ExamAPI {
  startExam: (topic: string) => Promise<{
    state: ExamState;
    message: string;
    sessionId: string;
    data: {
      session_id: string;
      result: {
        type: string;
        state: string;
      };
      current_question: {
        question_id: string;
        question: string;
        difficulty: number;
        topic: string;
      };
    };
  }>;
  submitAnswer: (answer: string) => Promise<{
    state: ExamState;
    message: string;
    data?: {
      type?: 'question';
      content?: string;
      question_id?: string;
      difficulty?: number;
    };
  }>;
  getExamState: () => Promise<{
    state: ExamState;
    data: any;
  }>;
  getProgressEvaluation: () => Promise<ProgressReport>;
  requestHint: () => Promise<{
    hint: string;
    hintsUsed: number;
  }>;
  getEvaluation: () => Promise<EvaluationReport>;
  connectWebSocket: (onMessage: (data: any) => void) => WebSocket;
  clearSession: () => void;
  getQuestionEvaluation: (sessionId: string, questionId: string) => Promise<ExamResponse<QuestionEvaluation>>;
}

interface ExamResponse<T> {
  state: string;
  message: string;
  data: T;
}

interface StartExamResponse {
  session_id: string;
  result: any;
  current_question: any;
}

interface SubmitAnswerResponse {
  result: any;
  progress: any;
  type?: 'question';
  content?: string;
  question_id?: string;
  difficulty?: number;
}

interface StateResponse {
  context: any;
  current_question: any;
}

interface HintData {
  hint: string;
  hints_used: number;
}

interface HintResponse {
  hint: string;
  hintsUsed: number;
}

class ExamService implements ExamAPI {
  private sessionId: string | null = null

  async startExam(topic: string) {
    const response = await axios.post<ExamResponse<StartExamResponse>>(`${BASE_URL}/start`, { topic })
    this.sessionId = response.data.data.session_id
    return {
      state: response.data.state as ExamState,
      message: response.data.message,
      sessionId: response.data.data.session_id,
      data: {
        session_id: response.data.data.session_id,
        result: response.data.data.result,
        current_question: response.data.data.current_question
      }
    }
  }

  async submitAnswer(answer: string) {
    if (!this.sessionId) {
      throw new Error('No active exam session')
    }
    const response = await axios.post<ExamResponse<SubmitAnswerResponse>>(
      `${BASE_URL}/${this.sessionId}/answer`,
      { answer }
    )
    return {
      state: response.data.state as ExamState,
      message: response.data.message,
      data: response.data.data
    }
  }

  async getExamState() {
    if (!this.sessionId) {
      throw new Error('No active exam session')
    }
    const response = await axios.get<ExamResponse<StateResponse>>(`${BASE_URL}/${this.sessionId}/state`)
    return {
      state: response.data.state as ExamState,
      data: response.data.data
    }
  }

  async getProgressEvaluation(): Promise<ProgressReport> {
    if (!this.sessionId) {
      throw new Error('No active exam session')
    }
    const response = await axios.get<ExamResponse<any>>(`${BASE_URL}/${this.sessionId}/progress`)
    return response.data.data
  }

  async getEvaluation(): Promise<EvaluationReport> {
    if (!this.sessionId) {
      throw new Error('No active exam session')
    }
    const response = await axios.get<ExamResponse<any>>(`${BASE_URL}/${this.sessionId}/evaluation`)
    return response.data.data
  }

  connectWebSocket(onMessage: (data: any) => void): WebSocket {
    if (!this.sessionId) {
      throw new Error('No active exam session')
    }
    const ws = new WebSocket(`${WS_BASE_URL}/${this.sessionId}/ws`)

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      onMessage(data)
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    ws.onclose = () => {
      console.log('WebSocket connection closed')
    }

    return ws
  }

  clearSession() {
    this.sessionId = null
  }

  async requestHint(): Promise<HintResponse> {
    if (!this.sessionId) {
      throw new Error('No active exam session')
    }
    const response = await axios.get<ExamResponse<HintData>>(`${BASE_URL}/${this.sessionId}/hint`)
    return {
      hint: response.data.data.hint,
      hintsUsed: response.data.data.hints_used
    }
  }

  getSessionId(): string | null {
    return this.sessionId
  }

  async getQuestionEvaluation(sessionId: string, questionId: string): Promise<ExamResponse<QuestionEvaluation>> {
    const response = await axios.get<ExamResponse<QuestionEvaluation>>(
      `${BASE_URL}/${sessionId}/question/${questionId}/evaluation`
    )
    return response.data
  }
}

export const examService = new ExamService()
