<template>
  <div class="home">
    <el-card class="start-exam">
      <template #header>
        <div class="card-header">
          <h1>Start Exam</h1>
        </div>
      </template>

      <el-form :model="form" label-position="top">
        <el-form-item label="Select Exam Topic">
          <el-select
            v-model="form.topic"
            placeholder="Please select an exam topic"
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
            Start Exam
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="history" v-if="examHistory.length">
      <template #header>
        <div class="card-header">
          <h2>History Records</h2>
        </div>
      </template>

      <el-table :data="examHistory">
        <el-table-column prop="date" label="Date" width="180" />
        <el-table-column prop="topic" label="Topic" />
        <el-table-column prop="score" label="Score" width="100" />
        <el-table-column label="Actions" width="120">
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              @click="viewReport(row.sessionId)"
            >
              View Report
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="privacy-notice">
        Your exam records and scores are not uploaded or stored externally.
      </div>
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
  { label: 'The dynamical programming algorithm for finite-horizon control', value: 'finite_horizon_control' },
  { label: 'PID Control', value: 'pid_control' },
  { label: 'The discrete linear quadratic regulator and iterative LQR', value: 'discrete_lqr' },
  { label: 'Direct Methods for Optimal Control', value: 'optimal_control' },
  { label: 'Bandit Algorithms', value: 'bandit_algorithms' },
  { label: 'Bellman\'s equations and their relationship to reinforcement learning', value: 'bellman_equations' },
  { label: 'Eligibility Traces', value: 'eligibility_traces' },
  { label: 'Q-Learning and Value-Function Approximations', value: 'q_learning' }
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

  .privacy-notice {
    margin-top: 15px;
    font-size: 12px;
    color: #909399;
    text-align: center;
    font-style: italic;
  }
}
</style>
