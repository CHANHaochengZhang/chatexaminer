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

      <!-- 进度评估部分 -->
      <template v-if="progress">
        <el-divider>当前进度</el-divider>

        <!-- 当前得分 -->
        <div class="progress-section">
          <div class="section-title">当前得分</div>
          <el-progress
            :percentage="progress.current_score"
            :format="(val) => val.toFixed(1) + '分'"
            :status="getScoreStatus(progress.current_score)"
          />
        </div>

        <!-- 主题覆盖 -->
        <div class="progress-section">
          <div class="section-title">知识点覆盖</div>
          <div class="topic-tags">
            <el-tooltip
              v-for="(data, topic) in progress.topic_progress"
              :key="topic"
              :content="`得分: ${data.score.toFixed(1)}`"
            >
              <el-tag :type="getTopicTagType(data.coverage)" class="topic-tag">
                {{ topic }}: {{ data.coverage.toFixed(0) }}%
              </el-tag>
            </el-tooltip>
          </div>
        </div>

        <!-- 行为指标 -->
        <div class="progress-section">
          <div class="section-title">答题表现</div>
          <div class="behavior-metrics">
            <el-tooltip content="平均每题用时（分钟）">
              <div class="metric-item">
                <el-icon><Timer /></el-icon>
                {{ (progress.behavior_metrics.avg_time_per_question / 60).toFixed(1) }}分钟
              </div>
            </el-tooltip>
            <el-tooltip content="提示使用率">
              <div class="metric-item">
                <el-icon><QuestionFilled /></el-icon>
                {{ (progress.behavior_metrics.hint_usage_rate * 100).toFixed(0) }}%
              </div>
            </el-tooltip>
            <el-tooltip content="答案一致性">
              <div class="metric-item">
                <el-icon><TrendCharts /></el-icon>
                {{ (progress.behavior_metrics.response_consistency * 100).toFixed(0) }}%
              </div>
            </el-tooltip>
          </div>
        </div>

        <!-- 最近评估 -->
        <div class="progress-section" v-if="progress.recent_evaluations.length">
          <div class="section-title">最近表现</div>
          <div class="recent-evaluations">
            <el-collapse>
              <el-collapse-item
                v-for="evaluation in progress.recent_evaluations"
                :key="evaluation.question_id"
              >
                <template #title>
                  问题 {{ evaluation.question_id }}
                  <el-tag size="small" :type="getScoreTagType(getAverageScore(evaluation.score))">
                    {{ getAverageScore(evaluation.score).toFixed(1) }}分
                  </el-tag>
                </template>
                <div class="evaluation-details">
                  <div class="score-details">
                    <div>准确性: {{ evaluation.score.accuracy }}%</div>
                    <div>清晰度: {{ evaluation.score.clarity }}%</div>
                    <div>理解度: {{ evaluation.score.understanding }}%</div>
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
import { computed } from 'vue'
import { Timer, QuestionFilled, TrendCharts } from '@element-plus/icons-vue'
import type { ExamState } from '@/types'
import type { ProgressReport } from '@/types'

const props = defineProps<{
  currentState: ExamState
  questionsAnswered: number
  hintsUsed: number
  currentDifficulty: number
  progress?: ProgressReport
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
