<template>
  <div class="eval-report">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>Evaluation Report</span>
          <el-tag type="success">Total Score: {{ evaluation?.totalScore || 0 }}</el-tag>
        </div>
      </template>

      <div class="report-content">
        <!-- Topic Coverage -->
        <div class="section">
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

        <!-- Strengths -->
        <div class="section">
          <h3>Strengths</h3>
          <ul>
            <li v-for="(strength, index) in evaluation?.strengths" :key="index">
              {{ strength }}
            </li>
          </ul>
        </div>

        <!-- Weaknesses -->
        <div class="section">
          <h3>Weaknesses</h3>
          <ul>
            <li v-for="(weakness, index) in evaluation?.weaknesses" :key="index">
              {{ weakness }}
            </li>
          </ul>
        </div>

        <!-- Suggestions -->
        <div class="section">
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
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
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
