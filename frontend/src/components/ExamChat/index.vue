<template>
  <div class="exam-chat">
    <!-- 消息列表 -->
    <div class="message-list" ref="messageList">
      <div
        v-for="(message, index) in messages"
        :key="index"
        :class="['message-item', message.role]"
      >
        <div class="message-content">
          <div class="text">{{ message.content }}</div>
          <div class="time">{{ formatTime(message.timestamp) }}</div>
        </div>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="input-area">
      <el-input
        v-model="inputMessage"
        type="textarea"
        :rows="3"
        placeholder="请输入你的回答..."
        :disabled="loading"
        @keydown.enter.exact.prevent="handleSend"
      />
      <div class="button-group">
        <el-button
          type="primary"
          :loading="loading"
          @click="handleSend"
        >
          发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import type { Message } from '@/types'

const props = defineProps<{
  messages: Message[]
  loading?: boolean
}>()

const emit = defineEmits<{
  (e: 'send', message: string): void
}>()

const inputMessage = ref('')
const messageList = ref<HTMLElement | null>(null)

// 发送消息
const handleSend = () => {
  if (!inputMessage.value.trim() || props.loading) return

  emit('send', inputMessage.value)
  inputMessage.value = ''
}

// 格式化时间
const formatTime = (timestamp?: number) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString()
}

// 监听消息列表变化，自动滚动到底部
watch(
  () => props.messages,
  async () => {
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
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);

  .message-list {
    flex: 1;
    overflow-y: auto;
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
