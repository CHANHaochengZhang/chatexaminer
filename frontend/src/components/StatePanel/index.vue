<template>
  <div class="state-panel">
    <el-card>
      <template #header>
        <div class="card-header">
          <span> Status Panel </span>
          <el-tag :type="stateTagType">{{ stateText }}</el-tag>
        </div>
      </template>

      <div class="stats">
        <div class="stat-item timer-container">
          <div class="label">Time Elapsed</div>
          <div class="value timer">{{ formattedTime }}</div>
        </div>

        <div class="stat-item difficulty-container">
          <div class="label">Current Difficulty</div>
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

      <!-- Progress Section -->
      <template v-if="progress">
        <el-divider>Current Progress</el-divider>

        <!-- Current Score -->
        <div class="progress-section">
          <div class="section-title">Current Score</div>
          <el-progress
            :percentage="progress.current_score"
            :format="(val) => val.toFixed(1) + ' pts'"
            :status="getScoreStatus(progress.current_score)"
          />
        </div>

        <!-- Topic Coverage -->
        <div class="progress-section">
          <div class="section-title">Topic Coverage</div>
          <div class="topic-tags">
            <el-tooltip
              v-for="(data, topic) in progress.topic_progress"
              :key="topic"
              :content="`Score: ${data.score.toFixed(1)}`"
            >
              <el-tag :type="getTopicTagType(data.coverage)" class="topic-tag">
                {{ topic }}: {{ data.coverage.toFixed(0) }}%
              </el-tag>
            </el-tooltip>
          </div>
        </div>

        <!-- Performance Metrics -->
        <div class="progress-section">
          <div class="section-title">Performance</div>
          <div class="behavior-metrics">
            <el-tooltip content="Average time per question (minutes)">
              <div class="metric-item">
                <el-icon><Timer /></el-icon>
                {{ (progress.behavior_metrics.avg_time_per_question / 60).toFixed(1) }}min
              </div>
            </el-tooltip>
            <el-tooltip content="Hint usage rate">
              <div class="metric-item">
                <el-icon><QuestionFilled /></el-icon>
                {{ (progress.behavior_metrics.hint_usage_rate * 100).toFixed(0) }}%
              </div>
            </el-tooltip>
            <el-tooltip content="Response consistency">
              <div class="metric-item">
                <el-icon><TrendCharts /></el-icon>
                {{ (progress.behavior_metrics.response_consistency * 100).toFixed(0) }}%
              </div>
            </el-tooltip>
          </div>
        </div>

        <!-- Recent Evaluations -->
        <div class="progress-section" v-if="progress.recent_evaluations.length">
          <div class="section-title">Recent Performance</div>
          <div class="recent-evaluations">
            <el-collapse>
              <el-collapse-item
                v-for="evaluation in progress.recent_evaluations"
                :key="evaluation.question_id"
              >
                <template #title>
                  Question {{ evaluation.question_id }}
                  <el-tag size="small" :type="getScoreTagType(getAverageScore(evaluation.score))">
                    {{ getAverageScore(evaluation.score).toFixed(1) }} pts
                  </el-tag>
                </template>
                <div class="evaluation-details">
                  <div class="score-details">
                    <div>Accuracy: {{ evaluation.score.accuracy }}%</div>
                    <div>Clarity: {{ evaluation.score.clarity }}%</div>
                    <div>Understanding: {{ evaluation.score.understanding }}%</div>
                  </div>
                  <div class="feedback">{{ evaluation.feedback }}</div>
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>
        </div>
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onBeforeUnmount, onUpdated } from 'vue'
import { Timer, QuestionFilled, TrendCharts } from '@element-plus/icons-vue'
import type { ExamState } from '@/types'
import type { ProgressReport } from '@/types'

const props = defineProps<{
  currentState: ExamState
  questionsAnswered: number
  hintsUsed: number
  currentDifficulty: number
  progress?: ProgressReport | null
}>()

// Timer logic
const examStartTime = ref(Date.now())
const currentTime = ref(Date.now())
const timerInterval = ref<number | null>(null)

const elapsedTimeInSeconds = computed(() => {
  return Math.floor((currentTime.value - examStartTime.value) / 1000)
})

const formattedTime = computed(() => {
  const seconds = elapsedTimeInSeconds.value
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const remainingSeconds = seconds % 60

  const pad = (num: number) => num.toString().padStart(2, '0')

  return `${pad(hours)}:${pad(minutes)}:${pad(remainingSeconds)}`
})

const startTimer = () => {
  if (timerInterval.value !== null) return

  timerInterval.value = window.setInterval(() => {
    currentTime.value = Date.now()
  }, 1000)
}

const stopTimer = () => {
  if (timerInterval.value !== null) {
    clearInterval(timerInterval.value)
    timerInterval.value = null
  }
}

onMounted(() => {
  examStartTime.value = Date.now()
  startTimer()
})

onBeforeUnmount(() => {
  stopTimer()
})

onUpdated(() => {
  // Restart timer if it was stopped and exam is not completed
  if (timerInterval.value === null && props.currentState !== 'COMPLETED') {
    startTimer()
  }

  // Stop timer if exam is completed
  if (props.currentState === 'COMPLETED' && timerInterval.value !== null) {
    stopTimer()
  }
})

const stateText = computed(() => {
  const stateMap: Record<ExamState, string> = {
    'INIT': 'Initializing',
    'TOPIC_SELECTED': 'Topic Selected',
    'QUESTIONING': 'Questioning',
    'EXPLAINING': 'Explaining',
    'EVALUATING': 'Evaluating',
    'COMPLETED': 'Completed',
    'CHAT': 'Chat'
  }
  return stateMap[props.currentState]
})

const stateTagType = computed(() => {
  const typeMap: Record<ExamState, 'success' | 'warning' | 'info' | 'primary' | 'danger'> = {
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

const getScoreStatus = (score: number) => {
  if (score >= 85) return 'success'
  if (score >= 70) return 'warning'
  return 'exception'
}

const getTopicTagType = (coverage: number): 'success' | 'warning' | 'danger' => {
  if (coverage >= 80) return 'success'
  if (coverage >= 60) return 'warning'
  return 'danger'
}

const getScoreTagType = (score: number): 'success' | 'warning' | 'danger' => {
  if (score >= 85) return 'success'
  if (score >= 70) return 'warning'
  return 'danger'
}

const getAverageScore = (score: { accuracy: number; clarity: number; understanding: number }) => {
  return (score.accuracy + score.clarity + score.understanding) / 3
}
</script>

<style scoped lang="scss">
.state-panel {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .stats {
    display: flex;
    flex-direction: column;
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

        &.timer {
          font-family: 'Courier New', monospace;
          letter-spacing: 1px;
          color: #409EFF;
          font-size: 28px;
        }
      }
    }

    .timer-container {
      margin-bottom: 10px;
    }
  }

  .progress-section {
    margin-top: 16px;

    .section-title {
      font-size: 14px;
      color: #606266;
      margin-bottom: 8px;
    }

    .topic-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;

      .topic-tag {
        cursor: pointer;
      }
    }

    .behavior-metrics {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;

      .metric-item {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 14px;
        color: #606266;

        .el-icon {
          font-size: 16px;
        }
      }
    }

    .recent-evaluations {
      .evaluation-details {
        font-size: 14px;

        .score-details {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 8px;
          margin-bottom: 8px;
        }

        .feedback {
          color: #606266;
          font-style: italic;
        }
      }
    }
  }
}
</style>
