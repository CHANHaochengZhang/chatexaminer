<template>
  <div class="report">
    <div class="report-header">
      <el-page-header @back="$router.push('/')">
        <template #content>
          <span class="page-title">评估报告</span>
        </template>
      </el-page-header>
    </div>

    <div class="report-content">
      <EvalReport
        v-if="report"
        :total-score="report.totalScore"
        :topic-coverage="report.topicCoverage"
        :behavior-score="report.behaviorScore"
        :question-evaluations="report.questionEvaluations"
        :behavior-details="report.behaviorDetails"
      />

      <div v-else class="loading">
        <el-empty
          v-if="error"
          :description="error"
        >
          <template #image>
            <el-icon :size="60" color="#909399">
              <WarningFilled />
            </el-icon>
          </template>
        </el-empty>
        <el-skeleton v-else :rows="10" animated />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { WarningFilled } from '@element-plus/icons-vue'
import EvalReport from '@/components/EvalReport/index.vue'
import type { EvalReportProps } from '@/components/EvalReport/types'

const route = useRoute()
const report = ref<EvalReportProps>()
const error = ref<string>()

const fetchReport = async () => {
  try {
    // TODO: 从后端获取报告数据
    report.value = {
      totalScore: 85.5,
      topicCoverage: '4/5',
      behaviorScore: 90,
      questionEvaluations: {
        '1': {
          score: 85,
          feedback: '回答准确，但可以提供更多细节。',
          details: {
            accuracy: '85/100',
            clarity: '90/100',
            understanding: '80/100'
          }
        }
      },
      behaviorDetails: {
        completeness: '85/100',
        logic: '90/100',
        terminology: '95/100',
        examples: '85/100'
      }
    }
  } catch (e) {
    error.value = '获取报告失败，请稍后重试'
    console.error(e)
  }
}

onMounted(() => {
  const sessionId = route.params.sessionId as string
  if (sessionId) {
    fetchReport()
  } else {
    error.value = '未找到考试会话'
  }
})
</script>

<style scoped lang="scss">
.report {
  height: 100vh;
  display: flex;
  flex-direction: column;

  .report-header {
    padding: 20px;
    border-bottom: 1px solid #eee;
    background: #fff;

    .page-title {
      font-size: 16px;
      font-weight: bold;
    }
  }

  .report-content {
    flex: 1;
    padding: 20px;
    overflow: auto;

    .loading {
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100%;
    }
  }
}
</style>
