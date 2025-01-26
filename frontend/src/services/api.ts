import axios from 'axios'
import type { AxiosInstance } from 'axios'
import type { Message } from '@/components/ExamChat/types'
import type { EvalReportProps } from '@/components/EvalReport/types'

const BASE_URL = 'http://localhost:8000/api/exam'

class ExamAPI {
  private api: AxiosInstance

  constructor() {
    this.api = axios.create({
      baseURL: BASE_URL,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json'
      }
    })
  }

  async startExam(topic: string) {
    const response = await this.api.post('/start', { topic })
    return response.data
  }

  async submitAnswer(sessionId: string, answer: string) {
    const response = await this.api.post(`/${sessionId}/answer`, { answer })
    return response.data
  }

  async getExamState(sessionId: string) {
    const response = await this.api.get(`/${sessionId}/state`)
    return response.data
  }

  async getEvaluation(sessionId: string) {
    const response = await this.api.get(`/${sessionId}/evaluation`)
    return response.data
  }
}

export const examAPI = new ExamAPI()
