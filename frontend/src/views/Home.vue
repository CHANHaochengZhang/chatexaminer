<template>
  <div class="home">
    <el-card class="start-exam">
      <template #header>
        <div class="card-header">
          <h1>开始考试</h1>
        </div>
      </template>

      <el-form :model="form" label-position="top">
        <el-form-item label="选择考试主题">
          <el-select
            v-model="form.topic"
            placeholder="请选择考试主题"
            class="topic-select"
          >
            <el-option
              v-for="topic in topics"
              :key="topic.value"
              :label="topic.label"
              :value="topic.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            :disabled="!form.topic"
            @click="handleStart"
          >
            开始考试
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="history" v-if="examHistory.length">
      <template #header>
        <div class="card-header">
          <h2>历史记录</h2>
        </div>
      </template>

      <el-table :data="examHistory">
        <el-table-column prop="date" label="日期" width="180" />
        <el-table-column prop="topic" label="主题" />
        <el-table-column prop="score" label="得分" width="100" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              @click="viewReport(row.sessionId)"
            >
              查看报告
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

interface ExamHistory {
  sessionId: string
  date: string
  topic: string
  score: number
}

const form = ref({
  topic: ''
})

const topics = [
  { label: 'Direct Methods for Optimal Control', value: 'optimal_control' },
  { label: '强化学习基础', value: 'rl_basics' },
  { label: '控制理论', value: 'control_theory' }
]

const examHistory = ref<ExamHistory[]>([
  {
    sessionId: '1',
    date: '2024-01-24',
    topic: 'Direct Methods for Optimal Control',
    score: 85
  }
])

const handleStart = () => {
  router.push({
    name: 'Exam',
    query: { topic: form.value.topic }
  })
}

const viewReport = (sessionId: string) => {
  router.push({
    name: 'Report',
    params: { sessionId }
  })
}
</script>

<style scoped lang="scss">
.home {
  max-width: 800px;
  margin: 40px auto;
  padding: 0 20px;
  display: flex;
  flex-direction: column;
  gap: 40px;

  .card-header {
    h1, h2 {
      margin: 0;
      font-weight: normal;
    }
  }

  .start-exam {
    .topic-select {
      width: 100%;
    }

    .el-form-item:last-child {
      margin-bottom: 0;
      text-align: center;

      .el-button {
        width: 200px;
      }
    }
  }
}
</style>
