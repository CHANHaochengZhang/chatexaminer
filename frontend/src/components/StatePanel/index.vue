<template>
  <div class="state-panel">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>考试状态</span>
          <el-tag :type="stateTagType">{{ stateText }}</el-tag>
        </div>
      </template>

      <div class="stats">
        <div class="stat-item">
          <div class="label">已答题数</div>
          <div class="value">{{ questionsAnswered }}</div>
        </div>
        <div class="stat-item">
          <div class="label">使用提示</div>
          <div class="value">{{ hintsUsed }}</div>
        </div>
        <div class="stat-item">
          <div class="label">当前难度</div>
          <div class="value">
            <el-rate
              :model-value="currentDifficulty"
              :max="5"
              disabled
              show-score
            />
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ExamState } from '@/types'

const props = defineProps<{
  currentState: ExamState
  questionsAnswered: number
  hintsUsed: number
  currentDifficulty: number
}>()

const stateText = computed(() => {
  const stateMap: Record<ExamState, string> = {
    'INIT': '初始化',
    'TOPIC_SELECTED': '已选题',
    'QUESTIONING': '答题中',
    'EXPLAINING': '解释中',
    'EVALUATING': '评估中',
    'COMPLETED': '已完成',
    'CHAT': '闲聊中'
  }
  return stateMap[props.currentState]
})

const stateTagType = computed(() => {
  const typeMap: Record<ExamState, string> = {
    'INIT': 'info',
    'TOPIC_SELECTED': 'warning',
    'QUESTIONING': 'primary',
    'EXPLAINING': 'warning',
    'EVALUATING': 'warning',
    'COMPLETED': 'success',
    'CHAT': 'info'
  }
  return typeMap[props.currentState]
})
</script>

<style scoped lang="scss">
.state-panel {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .stats {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;

    .stat-item {
      text-align: center;

      .label {
        color: #999;
        font-size: 14px;
        margin-bottom: 8px;
      }

      .value {
        font-size: 24px;
        font-weight: bold;
        color: var(--primary-color);

        &:deep(.el-rate) {
          display: flex;
          justify-content: center;
        }
      }

      &:last-child {
        grid-column: span 2;
      }
    }
  }
}
</style>
