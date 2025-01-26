import { defineStore } from 'pinia'
import { examAPI } from '@/services/api'
import type { Message } from '@/components/ExamChat/types'
import type { ExamState } from '@/components/StatePanel/types'
import type { EvalReportProps } from '@/components/EvalReport/types'

interface ExamStoreState {
  sessionId: string | null
  currentState: ExamState
  messages: Message[]
  questionsAnswered: number
  hintsUsed: number
  currentDifficulty: number
  evaluation: EvalReportProps | null
}

export const useExamStore = defineStore('exam', {
  state: (): ExamStoreState => ({
    sessionId: null,
    currentState: 'INIT',
    messages: [],
    questionsAnswered: 0,
    hintsUsed: 0,
    currentDifficulty: 3,
    evaluation: null
  }),

  getters: {
    isExamActive: (state) => state.sessionId !== null,
    currentQuestion: (state) => state.messages[state.messages.length - 1]
  },

  actions: {
    async startExam(topic: string) {
      try {
        const response = await examAPI.startExam(topic)
        this.sessionId = response.data.session_id
        this.currentState = response.data.state
        if (response.data.current_question) {
          this.messages.push({
            type: 'question',
            content: response.data.current_question.question,
            timestamp: new Date().toISOString()
          })
        }
        return response
      } catch (error) {
        console.error('Failed to start exam:', error)
        throw error
      }
    },

    async submitAnswer(answer: string) {
      if (!this.sessionId) return

      try {
        const response = await examAPI.submitAnswer(this.sessionId, answer)
        this.currentState = response.data.state

        // 添加学生的答案到消息列表
        this.messages.push({
          type: 'answer',
          content: answer,
          timestamp: new Date().toISOString()
        })

        // 如果有新问题，添加到消息列表
        if (response.data.current_question) {
          this.messages.push({
            type: 'question',
            content: response.data.current_question.question,
            timestamp: new Date().toISOString()
          })
        }

        this.questionsAnswered++
        return response
      } catch (error) {
        console.error('Failed to submit answer:', error)
        throw error
      }
    },

    async requestHint() {
      if (!this.sessionId) return

      try {
        this.hintsUsed++
        // TODO: 实现请求提示的 API
        this.messages.push({
          type: 'hint',
          content: '这是一个提示信息...',
          timestamp: new Date().toISOString()
        })
      } catch (error) {
        console.error('Failed to request hint:', error)
        throw error
      }
    },

    async getEvaluation() {
      if (!this.sessionId) return

      try {
        const response = await examAPI.getEvaluation(this.sessionId)
        this.evaluation = response.data
        return response
      } catch (error) {
        console.error('Failed to get evaluation:', error)
        throw error
      }
    },

    reset() {
      this.sessionId = null
      this.currentState = 'INIT'
      this.messages = []
      this.questionsAnswered = 0
      this.hintsUsed = 0
      this.currentDifficulty = 3
      this.evaluation = null
    }
  }
})
