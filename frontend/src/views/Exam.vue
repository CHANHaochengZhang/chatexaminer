<template>
  <div class="exam-page">
    <!-- Initial Topic Selection -->
    <template v-if="currentState === 'INIT' && !route.query.topic">
      <div class="topic-selection">
        <el-card>
          <template #header>
            <div class="card-header">
              Start Your Exam
            </div>
          </template>
          <el-form>
            <el-form-item label="Enter Topic">
              <el-input
                v-model="topic"
                placeholder="e.g., Direct Methods for Optimal Control"
                :disabled="loading"
              />
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                @click="startExam"
                :loading="loading"
              >
                Start Exam
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </div>
    </template>

    <!-- Loading Indicator -->
    <template v-else-if="currentState === 'INIT' && loading">
      <div class="loading-container">
        <el-card>
          <div class="loading-text">
            Loading...
            <el-progress type="circle" :percentage="50" status="warning" indeterminate />
          </div>
        </el-card>
      </div>
    </template>

    <!-- Exam Interface -->
    <template v-else>
      <div class="exam-container" :class="{'completed-state': currentState === 'COMPLETED'}">
        <!-- Left Panel -->
        <div class="side-panel">
          <StatePanel
            :current-state="currentState"
            :questions-answered="questionsAnswered"
            :hints-used="hintsUsed"
            :current-difficulty="currentDifficulty"
            :progress="progress"
          />

          <!-- Evaluation Report -->
          <div v-if="currentState === 'COMPLETED'" class="evaluation-section">
            <EvalReport :evaluation="evaluation" />
          </div>
        </div>

        <!-- Right Panel: Chat Interface -->
        <div class="main-content">
          <ExamChat
            :messages="messages"
            :loading="loading"
            @send="handleSend"
          />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { examService } from '../services/exam'
import type { Message, ExamState, EvaluationReport, ProgressReport } from '../types'
import StatePanel from '../components/StatePanel/index.vue'
import ExamChat from '../components/ExamChat/index.vue'
import EvalReport from '../components/EvalReport/index.vue'
import { ElMessage } from 'element-plus'
import { useRoute } from 'vue-router'

// State management
const route = useRoute()
const currentState = ref<ExamState>('INIT')
const topic = ref('')
const loading = ref(false)
const messages = ref<Message[]>([])
const questionsAnswered = ref(0)
const hintsUsed = ref(0)
const currentDifficulty = ref(3)
const evaluation = ref<EvaluationReport | null>(null)
const progress = ref<ProgressReport | null>(null)

// Topic mapping
const topicMap: Record<string, string> = {
  'finite_horizon_control': 'The dynamical programming algorithm for finite-horizon control',
  'pid_control': 'PID Control',
  'discrete_lqr': 'The discrete linear quadratic regulator and iterative LQR',
  'optimal_control': 'Direct Methods for Optimal Control',
  'bandit_algorithms': 'Bandit Algorithms',
  'bellman_equations': 'Bellman\'s equations and their relationship to reinforcement learning',
  'eligibility_traces': 'Eligibility Traces',
  'q_learning': 'Q-Learning and Value-Function Approximations'
}

// WebSocket connection
let ws: WebSocket | null = null

const setupWebSocket = () => {
  ws = examService.connectWebSocket((data) => {
    if (data.type === 'state_update') {
      currentState.value = data.state
      questionsAnswered.value = data.questions_answered || questionsAnswered.value
      hintsUsed.value = data.hints_used || hintsUsed.value
      currentDifficulty.value = data.current_difficulty || currentDifficulty.value
      progress.value = data.progress || progress.value
    }
  })
}

// Start exam
const startExam = async () => {
  if (!topic.value.trim()) {
    ElMessage.warning('Please enter an exam topic')
    return
  }

  try {
    loading.value = true
    const response = await examService.startExam(topic.value)
    currentState.value = response.state
    messages.value.push({
      role: 'system',
      content: `Welcome to your exam session，\n\nLet's talk about ${topic.value}!\n\n Are you ready?`,
      timestamp: Date.now(),
      state: currentState.value
    })

    if (response.sessionId) {
      setupWebSocket()
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || 'Failed to start exam, please try again')
    console.error('Start exam error:', error)
  } finally {
    loading.value = false
  }
}

// Check if there's a topic in route params when component mounts, and start exam automatically if exists
onMounted(() => {
  const topicFromRoute = route.query.topic as string
  if (topicFromRoute) {
    // If the input is a topic identifier, map it to the full topic name
    topic.value = topicMap[topicFromRoute] || topicFromRoute
    startExam()
  }
})

// Handle message sending
const handleSend = async (message: string) => {
  if (!message.trim()) return

  try {
    loading.value = true
    messages.value.push({
      role: 'user',
      content: message,
      timestamp: Date.now()
    })

    const response = await examService.submitAnswer(message)
    currentState.value = response.state

    if (response.data?.type === 'question' && response.data.content) {
      if (response.data.difficulty !== undefined) {
        currentDifficulty.value = response.data.difficulty
      }

      messages.value.push({
        role: 'assistant',
        content: response.data.content,
        timestamp: Date.now(),
        state: 'QUESTIONING',
        questionId: response.data.question_id
      })
    } else if (response.data?.content || response.message) {
      const messageContent = response.data?.content || response.message
      if (messageContent) {
        messages.value.push({
          role: 'system',
          content: messageContent,
          timestamp: Date.now(),
          state: currentState.value
        })
      }
    }

    if (response.state === 'COMPLETED') {
      const evalResult = await examService.getEvaluation()
      evaluation.value = evalResult
    }
  } catch (error) {
    ElMessage.error('Failed to send message, please try again')
    console.error('Send message error:', error)
  } finally {
    loading.value = false
  }
}

// Clean up when component unmounts
onBeforeUnmount(() => {
  if (ws) {
    ws.close()
  }
  examService.clearSession()
})
</script>

<style scoped lang="scss">
.exam-page {
  height: 100vh;
  padding: var(--spacing-md);
  background-color: var(--background-color);

  .topic-selection {
    max-width: 600px;
    margin: 100px auto;

    .card-header {
      font-size: 18px;
      font-weight: bold;
    }
  }

  .loading-container {
    max-width: 600px;
    margin: 100px auto;
    text-align: center;

    .loading-text {
      padding: 20px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 20px;
      font-size: 16px;
    }
  }

  .exam-container {
    display: grid;
    grid-template-columns: 300px 1fr;
    gap: var(--spacing-md);
    height: 100%;
    transition: grid-template-columns 0.5s ease-in-out;

    /* Adjust width ratio of left and right columns when exam is completed */
    &.completed-state {
      grid-template-columns: 1fr 1fr;

      /* Ensure evaluation report area is scrollable to prevent overflow */
      .side-panel {
        overflow-y: auto;
        max-height: calc(100vh - 40px);
      }

      /* Chat area width is reduced but remains usable */
      .main-content {
        min-width: 320px;
      }

      /* Highlight evaluation report in completion state */
      .evaluation-section {
        box-shadow: 0 0 10px rgba(64, 158, 255, 0.2);
        animation: highlight-report 1s ease;
      }
    }

    .side-panel {
      display: flex;
      flex-direction: column;
      gap: var(--spacing-md);

      .evaluation-section {
        transition: all 0.3s ease;
      }
    }

    .main-content {
      height: 100%;
    }
  }
}

/* Evaluation report highlight animation */
@keyframes highlight-report {
  0% { transform: translateY(10px); opacity: 0; }
  100% { transform: translateY(0); opacity: 1; }
}
</style>
