<template>
  <div class="eval-report">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>Evaluation Report</span>
          <div class="score-info">
            <el-tooltip
              content="Automatically calculated based on question metrics and difficulty weights"
              placement="top"
            >
              <el-tag type="success" class="score-tag">System Score: {{ Math.round(evaluation?.totalScore || 0) }}</el-tag>
            </el-tooltip>

            <el-tooltip
              content="Holistic assessment provided by AI examiner based on overall performance"
              placement="top"
            >
              <el-tag type="warning" class="score-tag">Examiner Score: {{ Math.round(evaluation?.finalScore || 0) }}</el-tag>
            </el-tooltip>

            <el-tooltip
              content="Overall performance classification"
              placement="top"
            >
              <el-tag type="info" class="score-tag">Performance Level: {{ evaluation?.finalLevel || 'N/A' }}</el-tag>
            </el-tooltip>
          </div>
        </div>
      </template>

      <div class="report-content">
        <!-- Score Explanation -->
        <div class="section score-explanation">
          <p class="explanation-text">
            Your exam has been evaluated using two scoring methods: a systematic algorithm-based assessment (System Score) and a comprehensive examiner evaluation (Examiner Score). The Performance Level reflects your overall proficiency.
          </p>
        </div>

        <!-- Topic Coverage -->
        <div class="section" v-if="evaluation?.topicCoverage?.length">
          <h3>Topic Coverage</h3>
          <div class="tags">
            <el-tag
              v-for="topic in evaluation?.topicCoverage"
              :key="topic"
              size="small"
              class="tag"
            >
              {{ topic }}
            </el-tag>
          </div>
        </div>

        <!-- Final Feedback -->
        <div class="section" v-if="evaluation?.finalFeedback">
          <h3>Overall Feedback</h3>
          <p class="feedback-text">{{ evaluation?.finalFeedback }}</p>
        </div>

        <!-- Strengths -->
        <div class="section" v-if="evaluation?.strengths?.length">
          <h3>Strengths</h3>
          <ul>
            <li v-for="(strength, index) in evaluation?.strengths" :key="index">
              {{ strength }}
            </li>
          </ul>
        </div>

        <!-- Weaknesses -->
        <div class="section" v-if="evaluation?.weaknesses?.length">
          <h3>Areas for Improvement</h3>
          <ul>
            <li v-for="(weakness, index) in evaluation?.weaknesses" :key="index">
              {{ weakness }}
            </li>
          </ul>
        </div>

        <!-- Suggestions -->
        <div class="section" v-if="evaluation?.suggestions?.length">
          <h3>Suggestions</h3>
          <ul>
            <li v-for="(suggestion, index) in evaluation?.suggestions" :key="index">
              {{ suggestion }}
            </li>
          </ul>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import type { EvaluationReport } from '@/types'

defineProps<{
  evaluation: EvaluationReport | null
}>()
</script>

<style scoped lang="scss">
.eval-report {
  /* 给卡片添加一些美化效果 */
  .el-card {
    transition: all 0.3s ease;

    &:hover {
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .score-info {
      display: flex;
      gap: 8px;

      .score-tag {
        font-weight: bold;
      }
    }
  }

  .report-content {
    .section {
      margin-bottom: 24px;

      h3 {
        font-size: 16px;
        margin: 0 0 12px;
        color: var(--text-color);
      }

      .tags {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }

      .score-explanation {
        background-color: #f9f9f9;
        border-radius: 6px;
        padding: 12px 16px;
        margin-bottom: 20px;
        border-left: 4px solid #409eff;

        .explanation-text {
          margin: 0;
          font-size: 14px;
          line-height: 1.6;
          color: #606266;
        }
      }

      .feedback-text {
        white-space: pre-line;
        line-height: 1.5;
        color: var(--text-color);
      }

      ul {
        margin: 0;
        padding-left: 20px;

        li {
          margin-bottom: 8px;
          color: var(--text-color);

          &:last-child {
            margin-bottom: 0;
          }
        }
      }
    }
  }
}
</style>
