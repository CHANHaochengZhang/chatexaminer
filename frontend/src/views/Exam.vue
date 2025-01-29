<template>
  <div class="exam-page">
    <!-- Initial Topic Selection -->
    <template v-if="currentState === 'INIT'">
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

    <!-- Exam Interface -->
    <template v-else>
      <div class="exam-container">
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

// 状态管理
const currentState = ref<ExamState>('INIT')
const topic = ref('')
const loading = ref(false)
const messages = ref<Message[]>([])
const questionsAnswered = ref(0)
const hintsUsed = ref(0)
const currentDifficulty = ref(3)
const evaluation = ref<EvaluationReport | null>(null)
const progress = ref<ProgressReport | null>(null)

// WebSocket 连接
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
      content: response.message,
      timestamp: Date.now()
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

    messages.value.push({
      role: 'assistant',
      content: response.message,
      timestamp: Date.now()
    })

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

// 组件卸载时清理
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

  .exam-container {
    display: grid;
    grid-template-columns: 300px 1fr;
    gap: var(--spacing-md);
    height: 100%;

    .side-panel {
      display: flex;
      flex-direction: column;
      gap: var(--spacing-md);
    }

    .main-content {
      height: 100%;
    }
  }
}
</style>
