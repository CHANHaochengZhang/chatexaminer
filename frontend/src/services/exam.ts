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
    try {
      if (!this.sessionId) {
        throw new Error('No active session')
      }

      const response = await axios.get<ExamResponse<any>>(`${BASE_URL}/${this.sessionId}/evaluation`)

      // Parse API returned data
      const apiData = response.data.data;

      // Extract strengths, weaknesses, suggestions from final_feedback
      let strengths: string[] = [];
      let weaknesses: string[] = [];
      let suggestions: string[] = [];

      // Try to extract information from final_feedback
      if (apiData.final_feedback) {
        const feedbackText = apiData.final_feedback;

        // Find "Strengths include" section
        const strengthsMatch = feedbackText.match(/Strengths include(.*?)(?=Areas for improvement|$)/s);
        if (strengthsMatch && strengthsMatch[1]) {
          strengths = strengthsMatch[1].split(/\.\s+/)
            .map((s: string) => s.trim())
            .filter((s: string) => s.length > 0)
            .map((s: string) => s + (s.endsWith('.') ? '' : '.'));
        }

        // Find "Areas for improvement" section
        const weaknessesMatch = feedbackText.match(/Areas for improvement include(.*?)(?=Continuing to|$)/s);
        if (weaknessesMatch && weaknessesMatch[1]) {
          weaknesses = weaknessesMatch[1].split(/\.\s+/)
            .map((s: string) => s.trim())
            .filter((s: string) => s.length > 0)
            .map((s: string) => s + (s.endsWith('.') ? '' : '.'));
        }

        // Extract suggestions from the last part
        const suggestionsMatch = feedbackText.match(/Continuing to(.*?)(?=$)/s);
        if (suggestionsMatch && suggestionsMatch[1]) {
          suggestions = [
            'Continuing to' + suggestionsMatch[1].trim()
          ];
        }
      }

      // Extract topic coverage information
      const topicCoverage = Object.keys(apiData.topic_coverage || {});

      // Return transformed data
      return {
        totalScore: apiData.total_score || 0,
        finalScore: apiData.final_score || 0,
        finalLevel: apiData.final_level || '',
        finalFeedback: apiData.final_feedback || '',
        topicCoverage: topicCoverage,
        strengths: strengths.length > 0 ? strengths : ['Good understanding of core concepts'],
        weaknesses: weaknesses.length > 0 ? weaknesses : ['Could improve depth of explanations'],
        suggestions: suggestions.length > 0 ? suggestions : ['Continue practicing with different problem types'],
        questionEvaluations: apiData.question_evaluations || {},
        behaviorScore: apiData.behavior_score || 0
      }
    } catch (error) {
      console.error('Error getting evaluation:', error)
      throw error
    }
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
