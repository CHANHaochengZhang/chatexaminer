<template>
  <div class="exam-chat">
    <!-- Message List -->
    <div class="message-list" ref="messageList">
      <div
        v-for="(message, index) in messages"
        :key="index"
        :class="['message-item', message.role]"
      >
        <div class="message-content">
          <div v-if="(message.role === 'assistant' || message.role === 'system') && message.state && message.state !== 'QUESTIONING'" class="state-tag">
            {{ message.state }}
          </div>
          <div class="text">{{ message.content }}</div>
          <div class="message-footer">
            <div class="time">{{ formatTime(message.timestamp) }}</div>
            <!-- If it's a student's answer and the state is questioning, show evaluation button -->
            <el-button
              v-if="shouldShowEvalButton(message)"
              type="primary"
              size="small"
              link
              @click="showEvaluation(message)"
            >
              View Evaluation
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- Input Area -->
    <div class="input-area">
      <el-input
        v-model="inputMessage"
        type="textarea"
        :rows="3"
        placeholder="Enter your answer..."
        :disabled="loading"
        @keydown.enter.exact.prevent="handleSend"
      />
      <div class="button-group">
        <el-button
          type="primary"
          :loading="loading"
          @click="handleSend"
        >
          Send
        </el-button>
      </div>
    </div>

    <!-- Evaluation Modal -->
    <el-dialog
      v-model="showEvalDialog"
      title="Answer Evaluation"
      width="500px"
    >
      <div v-if="currentEval" class="evaluation-content">
        <div class="scores">
          <div class="score-item">
            <div class="label">Accuracy:</div>
            <div class="value">{{ currentEval.score.accuracy }}</div>
          </div>
          <div class="score-item">
            <div class="label">Clarity:</div>
            <div class="value">{{ currentEval.score.clarity }}</div>
          </div>
          <div class="score-item">
            <div class="label">Understanding:</div>
            <div class="value">{{ currentEval.score.understanding }}</div>
          </div>
        </div>
        <div class="feedback">
          <div class="label">Feedback:</div>
          <div class="value">{{ currentEval.feedback }}</div>
        </div>
        <div class="time-taken">
          <div class="label">Time Taken:</div>
          <div class="value">{{ formatSeconds(currentEval.time_taken) }}</div>
        </div>
      </div>
      <div v-else class="loading-eval">
        <el-skeleton :rows="3" animated />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import type { Message } from '@/types'
import type { QuestionEvaluation } from '@/services/exam'
import { examService } from '@/services/exam'

const props = defineProps<{
  messages: Message[]
  loading: boolean
}>()

const emit = defineEmits<{
  (e: 'send', message: string): void
}>()

const inputMessage = ref('')
const messageList = ref<HTMLElement | null>(null)
const showEvalDialog = ref(false)
const currentEval = ref<QuestionEvaluation | null>(null)

// Send message
const handleSend = () => {
  if (!inputMessage.value.trim() || props.loading) return

  // Get current questionId (from the most recent assistant message)
  const currentQuestionId = getCurrentQuestionId()

  console.log('Sending message:', {
    content: inputMessage.value,
    timestamp: Date.now(),
    questionId: currentQuestionId
  })

  emit('send', inputMessage.value)
  inputMessage.value = ''
}

// Helper function to get current questionId
const getCurrentQuestionId = () => {
  // Traverse messages from back to front to find the most recent assistant message
  for (let i = props.messages.length - 1; i >= 0; i--) {
    const msg = props.messages[i]
    if (msg.role === 'assistant' && msg.state === 'QUESTIONING') {
      return msg.questionId
    }
  }
  return null
}

// Format time
const formatTime = (timestamp?: number) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString()
}

// Format seconds
const formatSeconds = (seconds: number) => {
  return `${seconds.toFixed(2)}s`
}

// Determine whether to show evaluation button
const shouldShowEvalButton = (message: Message) => {
  console.log('Checking if message should show evaluation button:', {
    message,
    role: message.role,
  })

  if (message.role !== 'user') {
    console.log('Not a user message, do not show button')
    return false
  }

  // Find the most recent assistant message from this message
  const index = props.messages.findIndex(m => m === message)
  console.log('Current message index:', index)

  // Check previous message
  const prevMsg = props.messages[index - 1]
  console.log('Previous message:', prevMsg)

  // Check next message
  const nextMsg = props.messages[index + 1]
  console.log('Next message:', nextMsg)

  // If previous message is assistant and state is QUESTIONING, show button
  if (prevMsg?.role === 'assistant' && prevMsg?.state === 'QUESTIONING') {
    console.log('Previous message is assistant and state is QUESTIONING, show button')
    return true
  }

  return false
}

// Show evaluation results
const showEvaluation = async (message: Message) => {
  // Get questionId for this message
  const index = props.messages.findIndex(m => m === message)
  let questionId = null

  // Find the most recent assistant message's questionId from this message
  for (let i = index - 1; i >= 0; i--) {
    const prevMsg = props.messages[i]
    if (prevMsg.role === 'assistant' && prevMsg.state === 'QUESTIONING') {
      questionId = prevMsg.questionId
      break
    }
  }

  if (!questionId) {
    ElMessage.error('Unable to find corresponding question ID')
    return
  }

  try {
    showEvalDialog.value = true
    const sessionId = examService.getSessionId()
    if (!sessionId) {
      throw new Error('No active session')
    }

    const response = await examService.getQuestionEvaluation(sessionId, questionId)
    currentEval.value = response.data
  } catch (error) {
    console.error('Failed to fetch evaluation:', error)
    ElMessage.error('Failed to get evaluation')
    showEvalDialog.value = false
  }
}

// Watch message list changes, auto scroll to bottom
watch(
  () => props.messages,
  async (newMessages) => {
    console.log('Message list updated:', newMessages.map(msg => ({
      role: msg.role,
      state: msg.state,
      questionId: msg.questionId,
      content: msg.content.substring(0, 50) + '...'
    })))

    await nextTick()
    if (messageList.value) {
      messageList.value.scrollTop = messageList.value.scrollHeight
    }
  },
  { deep: true }
)
</script>

<style scoped lang="scss">
.exam-chat {
  position: relative;
  height: calc(100vh - 64px);
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);

  .message-list {
    position: relative;
    flex: 1;
    overflow-y: scroll;
    padding: 20px;

    .message-item {
      margin-bottom: 20px;
      display: flex;

      &.user {
        flex-direction: row-reverse;

        .message-content {
          background-color: var(--primary-color);
          color: #fff;
          margin-left: 0;
          margin-right: 12px;

          &::before {
            left: auto;
            right: -6px;
            border-left-color: var(--primary-color);
            border-right: none;
          }
        }
      }

      &.system {
        .message-content {
          background-color: #f4f4f5;
          margin: 0 auto;
          max-width: 80%;

          &::before {
            display: none;
          }

          .state-tag {
            background-color: #909399;
          }
        }
      }

      .message-content {
        background-color: #f4f4f5;
        padding: 12px 16px;
        border-radius: 8px;
        position: relative;
        margin-left: 12px;
        max-width: 70%;

        &::before {
          content: '';
          position: absolute;
          left: -6px;
          top: 12px;
          border: 6px solid transparent;
          border-right-color: #f4f4f5;
        }

        .state-tag {
          display: inline-block;
          padding: 2px 8px;
          background-color: #409eff;
          color: white;
          border-radius: 4px;
          font-size: 12px;
          margin-bottom: 8px;
        }

        .text {
          word-break: break-word;
          white-space: pre-wrap;
        }

        .time {
          font-size: 12px;
          color: #999;
          margin-top: 4px;
          text-align: right;
        }
      }
    }
  }

  .input-area {
    padding: 20px;
    border-top: 1px solid #eee;

    .button-group {
      margin-top: 12px;
      display: flex;
      justify-content: flex-end;
    }
  }
}
</style>
