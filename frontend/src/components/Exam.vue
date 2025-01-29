// 导入所需的组件和工具
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import type { Message, ExamState, ProgressReport } from '@/types'
import { examService } from '@/services/exam'

// 定义状态更新间隔（毫秒）
const STATE_UPDATE_INTERVAL = 3000

// 状态更新定时器
let stateUpdateTimer: number | null = null

// 获取最新状态
const updateExamState = async () => {
  if (!props.sessionId) return

  try {
    console.log('[State] Fetching latest exam state...')
    const response = await examService.getExamState()
    console.log('[State] Received state update:', response)

    currentState.value = response.state as ExamState
    if (response.data?.progress) {
      console.log('[Progress] Updating exam progress from state check')
      examProgress.value = response.data.progress
    }
  } catch (error) {
    console.error('[Error] Failed to fetch exam state:', error)
  }
}

// 开始定期更新状态
const startStateUpdates = () => {
  console.log('[State] Starting periodic state updates')
  stateUpdateTimer = window.setInterval(updateExamState, STATE_UPDATE_INTERVAL)
}

// 停止定期更新状态
const stopStateUpdates = () => {
  if (stateUpdateTimer) {
    console.log('[State] Stopping periodic state updates')
    clearInterval(stateUpdateTimer)
    stateUpdateTimer = null
  }
}

// 处理答案提交
const handleSend = async (message: string) => {
  loading.value = true
  console.log('[Chat] User message:', message)

  try {
    // 添加用户消息
    messages.value.push({
      role: 'user',
      content: message,
      timestamp: Date.now()
    })
    console.log('[Chat] Message added to chat history')

    // 发送答案
    console.log('[API] Sending answer to server...')
    const response = await examService.submitAnswer(message)
    console.log('[API] Server response:', response)

    // 处理聊天响应
    if (response.data?.type === 'chat') {
      console.log('[Chat] Received chat response:', response.data.content)
      messages.value.push({
        role: 'assistant',
        content: response.data.content,
        timestamp: Date.now()
      })
    } else if (response.data?.result?.type === 'question') {
      console.log('[Chat] Received question:', response.data.result.content)
      messages.value.push({
        role: 'assistant',
        content: response.data.result.content,
        timestamp: Date.now()
      })
    }

    // 更新状态
    console.log('[State] Updating exam state:', response.state)
    currentState.value = response.state as ExamState

    if (response.data?.progress) {
      console.log('[Progress] Updating exam progress:', {
        questionsAnswered: response.data.progress.stats.questions_answered,
        currentScore: response.data.progress.current_score,
        state: response.data.progress.stats.current_state
      })
      examProgress.value = response.data.progress
    }

    // 立即获取最新状态
    await updateExamState()

  } catch (error: any) {
    console.error('[Error] Failed to process answer:', error)
    const errorMessage = error.response?.data?.detail || error.message
    console.log('[Chat] Adding error message to chat')

    messages.value.push({
      role: 'system',
      content: `Error: ${errorMessage}`,
      timestamp: Date.now()
    })
  } finally {
    console.log('[Chat] Message processing completed')
    loading.value = false
  }
}

// WebSocket连接处理
const setupWebSocket = (sessionId: string) => {
  console.log('[WebSocket] Setting up connection...')
  try {
    const ws = examService.connectWebSocket((data) => {
      console.log('[WebSocket] Received message:', data)
      if (data.type === 'state_update') {
        console.log('[WebSocket] Updating state:', data.state)
        currentState.value = data.state
      }
    })

    ws.onopen = () => {
      console.log('[WebSocket] Connection established')
    }

    ws.onclose = () => {
      console.log('[WebSocket] Connection closed')
    }

    ws.onerror = (error) => {
      console.error('[WebSocket] Connection error:', error)
    }

    return ws
  } catch (error) {
    console.error('[WebSocket] Setup failed:', error)
    return null
  }
}

// 监听会话ID变化
watch(() => props.sessionId, (newSessionId) => {
  console.log('[Watch] Session ID changed:', newSessionId)
  if (newSessionId) {
    setupWebSocket(newSessionId)
    startStateUpdates()
  } else {
    stopStateUpdates()
  }
})

// 组件挂载时的处理
onMounted(() => {
  console.log('[Lifecycle] Component mounted')
  if (props.sessionId) {
    console.log('[Init] Setting up exam with session:', props.sessionId)
    setupWebSocket(props.sessionId)
    startStateUpdates()
    updateExamState() // 立即获取初始状态
  }
})

// 组件卸载时的处理
onBeforeUnmount(() => {
  console.log('[Lifecycle] Component unmounting')
  stopStateUpdates()
  if (ws.value) {
    console.log('[WebSocket] Closing connection')
    ws.value.close()
  }
})
