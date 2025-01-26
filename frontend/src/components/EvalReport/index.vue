<template>
  <div class="eval-report">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>评估报告</span>
          <el-tag type="success">总分：{{ evaluation?.totalScore || 0 }}</el-tag>
        </div>
      </template>

      <div class="report-content">
        <!-- 主题覆盖 -->
        <div class="section">
          <h3>主题覆盖</h3>
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

        <!-- 优点 -->
        <div class="section">
          <h3>优点</h3>
          <ul>
            <li v-for="(strength, index) in evaluation?.strengths" :key="index">
              {{ strength }}
            </li>
          </ul>
        </div>

        <!-- 不足 -->
        <div class="section">
          <h3>不足</h3>
          <ul>
            <li v-for="(weakness, index) in evaluation?.weaknesses" :key="index">
              {{ weakness }}
            </li>
          </ul>
        </div>

        <!-- 建议 -->
        <div class="section">
          <h3>建议</h3>
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
