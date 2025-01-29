import axios from 'axios'
import type { Message, ExamState, EvaluationReport, ProgressReport } from '@/types'

const BASE_URL = 'http://localhost:8000/api/exam'

export interface ExamAPI {
  startExam: (topic: string) => Promise<{
    state: ExamState;
    message: string;
    sessionId: string;
  }>;
  submitAnswer: (answer: string) => Promise<{
    state: ExamState;
    message: string;
    progress: any;
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
}

class ExamService implements ExamAPI {
  private sessionId: string | null = null

  async startExam(topic: string) {
    const response = await axios.post(`${BASE_URL}/start`, { topic })
    this.sessionId = response.data.data.session_id
    if (!this.sessionId) {
      throw new Error('Failed to get session ID from server')
    }
    return {
      state: response.data.state as ExamState,
      message: response.data.message as string,
      sessionId: this.sessionId
    }
  }

  async submitAnswer(answer: string) {
    if (!this.sessionId) {
      throw new Error('No active exam session')
    }
    const response = await axios.post(`${BASE_URL}/${this.sessionId}/answer`, { answer })
    return {
      state: response.data.state as ExamState,
      message: response.data.message as string,
      progress: response.data.data.progress
    }
  }

  async getExamState() {
    if (!this.sessionId) {
      throw new Error('No active exam session')
    }
    const response = await axios.get(`${BASE_URL}/${this.sessionId}/state`)
    return {
      state: response.data.state as ExamState,
      data: response.data.data
    }
  }

  async getProgressEvaluation(): Promise<ProgressReport> {
    if (!this.sessionId) {
      throw new Error('No active exam session')
    }
    const response = await axios.get(`${BASE_URL}/${this.sessionId}/progress`)
    return response.data.data
  }

  async getEvaluation(): Promise<EvaluationReport> {
    if (!this.sessionId) {
      throw new Error('No active exam session')
    }
    const response = await axios.get(`${BASE_URL}/${this.sessionId}/evaluation`)
    return response.data.data
  }

  connectWebSocket(onMessage: (data: any) => void) {
    if (!this.sessionId) {
      throw new Error('No active exam session')
    }
    const ws = new WebSocket(`ws://localhost:8000/api/exam/${this.sessionId}/ws`)

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      onMessage(data)
    }

    return ws
  }

  clearSession() {
    this.sessionId = null
  }

  async requestHint() {
    if (!this.sessionId) {
      throw new Error('No active exam session')
    }
    const response = await axios.get(`${BASE_URL}/${this.sessionId}/hint`)
    return {
      hint: response.data.data.hint,
      hintsUsed: response.data.data.hints_used
    }
  }
}

export const examAPI: ExamAPI = new ExamService()
