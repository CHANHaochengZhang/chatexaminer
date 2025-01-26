<template>
  <div class="exam-page">
    <!-- 初始状态：选择主题 -->
    <div v-if="currentState === 'INIT'" class="topic-selection">
      <el-card>
        <template #header>
          <div class="card-header">
            <span>选择考试主题</span>
          </div>
        </template>
        <el-form>
          <el-form-item>
            <el-input
              v-model="topic"
              placeholder="请输入考试主题"
              clearable
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="startExam" :loading="loading">
              开始考试
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </div>

    <!-- 考试进行中 -->
    <template v-else>
      <div class="exam-container">
        <!-- 左侧：状态面板 -->
        <div class="side-panel">
          <StatePanel
            :current-state="currentState"
            :questions-answered="questionsAnswered"
            :hints-used="hintsUsed"
            :current-difficulty="currentDifficulty"
          />

          <!-- 评估报告 -->
          <div v-if="currentState === 'COMPLETED'" class="evaluation-section">
            <EvalReport :evaluation="evaluation" />
          </div>
        </div>

        <!-- 右侧：聊天界面 -->
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
import { examService } from '@/services/exam'
import type { Message, ExamState, EvaluationReport } from '@/types'
import StatePanel from '@/components/StatePanel/index.vue'
import ExamChat from '@/components/ExamChat/index.vue'
import EvalReport from '@/components/EvalReport/index.vue'
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

// WebSocket 连接
let ws: WebSocket | null = null

const setupWebSocket = () => {
  ws = examService.connectWebSocket((data) => {
    if (data.type === 'state_update') {
      currentState.value = data.state
      questionsAnswered.value = data.questions_answered || questionsAnswered.value
      hintsUsed.value = data.hints_used || hintsUsed.value
      currentDifficulty.value = data.current_difficulty || currentDifficulty.value
    }
  })
}

// 开始考试
const startExam = async () => {
  if (!topic.value.trim()) {
    ElMessage.warning('请输入考试主题')
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

    // 如果成功开始考试，设置 WebSocket 连接
    if (response.sessionId) {
      setupWebSocket()
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '开始考试失败，请重试')
    console.error('Start exam error:', error)
  } finally {
    loading.value = false
  }
}

// 处理消息发送
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

    // 如果考试完成，获取评估报告
    if (response.state === 'COMPLETED') {
      const evalResult = await examService.getEvaluation()
      evaluation.value = evalResult
    }
  } catch (error) {
    ElMessage.error('发送消息失败，请重试')
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
