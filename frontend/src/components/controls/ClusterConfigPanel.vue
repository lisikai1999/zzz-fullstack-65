<template>
  <div class="panel">
    <div class="panel-title">Network Config</div>
    <div class="config-row">
      <label>Base Delay (ms):</label>
      <input type="number" v-model.number="baseDelay" min="1" max="500" @change="apply" />
    </div>
    <div class="config-row">
      <label>Jitter (ms):</label>
      <input type="number" v-model.number="jitter" min="0" max="200" @change="apply" />
    </div>
    <div class="config-row">
      <label>Loss Rate:</label>
      <input type="number" v-model.number="lossRate" min="0" max="1" step="0.05" @change="apply" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useSimulationStore } from '../../stores/simulation'

const store = useSimulationStore()

const baseDelay = ref(15)
const jitter = ref(10)
const lossRate = ref(0)

function apply() {
  store.updateNetworkConfig({
    base_delay: baseDelay.value,
    delay_jitter: jitter.value,
    packet_loss_rate: lossRate.value,
  })
}
</script>

<style scoped>
.config-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.config-row label {
  font-size: 0.8rem;
  color: #90a4ae;
}

.config-row input {
  width: 80px;
  padding: 3px 6px;
  background: #1a1a2e;
  border: 1px solid #0f3460;
  border-radius: 4px;
  color: #e0e0e0;
  font-size: 0.8rem;
  text-align: right;
}
</style>
