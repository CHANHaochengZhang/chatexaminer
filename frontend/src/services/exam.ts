import axios from 'axios'
import type { Message, ExamState, EvaluationReport } from '@/types'

const BASE_URL = 'http://localhost:8000/api/exam'

class ExamService {
  private sessionId: string | null = null

  async startExam(topic: string) {
    const response = await axios.post(`${BASE_URL}/start`, { topic })
    this.sessionId = response.data.data.session_id
    return {
      state: response.data.state as ExamState,
      message: response.data.message,
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
      message: response.data.message
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
}

export const examService = new ExamService()
