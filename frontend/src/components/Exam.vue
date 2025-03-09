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
  console.group('[Chat] New Message Processing')
  console.log('[Chat] User message:', {
    content: message,
    timestamp: new Date().toISOString(),
    state: currentState.value
  })

  try {
    // 添加用户消息
    messages.value.push({
      role: 'user',
      content: message,
      timestamp: Date.now()
    })
    console.log('[Chat] Message history updated:', messages.value.length, 'messages total')

    // 发送答案
    console.group('[API] Submit Answer Request')
    console.log('Request:', {
      sessionId: props.sessionId,
      message: message,
      currentState: currentState.value,
      timestamp: new Date().toISOString()
    })

    const response = await examService.submitAnswer(message)
    console.log('Response:', {
      state: response.state,
      type: response.data?.type,
      content: response.data?.content || response.data?.result?.content,
      progress: {
        questionsAnswered: response.data?.progress?.stats?.questions_answered,
        currentScore: response.data?.progress?.current_score,
        state: response.data?.progress?.stats?.current_state
      }
    })
    console.groupEnd()

    // 处理聊天响应
    if (response.data?.type === 'chat') {
      console.group('[Chat] Processing Chat Response')
      console.log('Chat content:', response.data.content)
      console.log('Current state:', response.state)
      messages.value.push({
        role: 'assistant',
        content: response.data.content,
        timestamp: Date.now()
      })
      console.log('Updated message history:', messages.value.length, 'messages')
      console.groupEnd()
    } else if (response.data?.result?.type === 'question') {
      console.group('[Chat] Processing Question Response')
      console.log('Question:', {
        content: response.data.result.content,
        id: response.data.result.question_id,
        difficulty: response.data.result.difficulty,
        topic: response.data.result.topic
      })
      messages.value.push({
        role: 'assistant',
        content: response.data.result.content,
        timestamp: Date.now()
      })
      console.log('Updated message history:', messages.value.length, 'messages')
      console.groupEnd()
    }

    // 更新状态
    console.group('[State] State Update')
    console.log('Previous state:', currentState.value)
    console.log('New state:', response.state)
    currentState.value = response.state as ExamState
    console.groupEnd()

    if (response.data?.progress) {
      console.group('[Progress] Progress Update')
      console.log('Questions answered:', response.data.progress.stats.questions_answered)
      console.log('Current score:', response.data.progress.current_score)
      console.log('Current state:', response.data.progress.stats.current_state)
      console.log('Topic progress:', response.data.progress.topic_progress)
      console.log('Recent evaluations:', response.data.progress.recent_evaluations)
      console.log('Behavior metrics:', response.data.progress.behavior_metrics)
      examProgress.value = response.data.progress
      console.groupEnd()
    }

    // 立即获取最新状态
    await updateExamState()

  } catch (error: any) {
    console.group('[Error] Error Processing')
    console.error('Error details:', {
      message: error.message,
      response: error.response?.data,
      status: error.response?.status
    })
    console.trace('Error stack trace')
    console.groupEnd()

    const errorMessage = error.response?.data?.detail || error.message
    messages.value.push({
      role: 'system',
      content: `Error: ${errorMessage}`,
      timestamp: Date.now()
    })
  } finally {
    console.log('[Chat] Message processing completed')
    console.groupEnd()
    loading.value = false
  }
}

// WebSocket连接处理
const setupWebSocket = (sessionId: string) => {
  console.group('[WebSocket] Setup')
  console.log('Initializing WebSocket connection for session:', sessionId)

  try {
    const ws = examService.connectWebSocket((data) => {
      console.group('[WebSocket] Message Received')
      console.log('Raw data:', data)
      console.log('Timestamp:', new Date().toISOString())
      if (data.type === 'state_update') {
        console.log('State update:', {
          previousState: currentState.value,
          newState: data.state
        })
        currentState.value = data.state
      } else if (data.type === 'response') {
        console.log('Response received:', {
          state: data.state,
          message: data.message,
          hasResult: !!data.data?.result
        })

        // 处理服务器返回的message
        if (data.message) {
          // 添加系统消息，显示状态变化的信息
          messages.value.push({
            role: 'system',
            content: data.message,
            timestamp: Date.now(),
            state: data.state
          })
        }

        // 处理结果中的内容
        if (data.data?.result?.type === 'chat' && data.data?.result?.content) {
          messages.value.push({
            role: 'assistant',
            content: data.data.result.content,
            timestamp: Date.now()
          })
        } else if (data.data?.result?.type === 'question' && data.data?.result?.content) {
          messages.value.push({
            role: 'assistant',
            content: data.data.result.content,
            timestamp: Date.now(),
            questionId: data.data.result.question_id
          })
        }

        // 更新当前状态
        currentState.value = data.state
      }
      console.groupEnd()
    })

    ws.onopen = () => {
      console.log('[WebSocket] Connection established', {
        sessionId,
        timestamp: new Date().toISOString()
      })
    }

    ws.onclose = () => {
      console.log('[WebSocket] Connection closed', {
        sessionId,
        timestamp: new Date().toISOString()
      })
    }

    ws.onerror = (error) => {
      console.group('[WebSocket] Error')
      console.error('Connection error:', error)
      console.trace('Error stack trace')
      console.groupEnd()
    }

    console.log('WebSocket setup completed')
    console.groupEnd()
    return ws
  } catch (error) {
    console.group('[WebSocket] Setup Failed')
    console.error('Setup error:', error)
    console.trace('Error stack trace')
    console.groupEnd()
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
