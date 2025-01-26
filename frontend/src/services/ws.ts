import { ref } from 'vue'
import type { Ref } from 'vue'

export class ExamWebSocket {
  private ws: WebSocket | null = null
  private sessionId: string
  private messageHandler: ((data: any) => void) | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 3
  private reconnectTimeout = 1000

  constructor(sessionId: string) {
    this.sessionId = sessionId
  }

  connect(onMessage: (data: any) => void) {
    this.messageHandler = onMessage
    this.ws = new WebSocket(`ws://localhost:8000/api/exam/${this.sessionId}/ws`)

    this.ws.onopen = () => {
      console.log('WebSocket connected')
      this.reconnectAttempts = 0
    }

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (this.messageHandler) {
        this.messageHandler(data)
      }
    }

    this.ws.onclose = () => {
      console.log('WebSocket disconnected')
      this.handleReconnect()
    }

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  }

  private handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`)

      setTimeout(() => {
        this.connect(this.messageHandler!)
      }, this.reconnectTimeout * this.reconnectAttempts)
    }
  }

  send(message: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    } else {
      console.error('WebSocket is not connected')
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }
}

export function useExamWebSocket(sessionId: string) {
  const ws: Ref<ExamWebSocket | null> = ref(null)

  const connect = (onMessage: (data: any) => void) => {
    if (!ws.value) {
      ws.value = new ExamWebSocket(sessionId)
    }
    ws.value.connect(onMessage)
  }

  const disconnect = () => {
    if (ws.value) {
      ws.value.disconnect()
      ws.value = null
    }
  }

  const send = (message: any) => {
    if (ws.value) {
      ws.value.send(message)
    }
  }

  return {
    connect,
    disconnect,
    send
  }
}
