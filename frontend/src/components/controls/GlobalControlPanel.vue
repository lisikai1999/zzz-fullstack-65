<template>
  <div class="panel">
    <div class="panel-title">Simulation Control</div>
    <div class="control-buttons">
      <button class="btn small" @click="store.step(1)" :disabled="isPlaying">
        Step 1
      </button>
      <button class="btn small" @click="store.step(10)" :disabled="isPlaying">
        Step 10
      </button>
      <button class="btn small" @click="store.step(100)" :disabled="isPlaying">
        Step 100
      </button>
      <button v-if="!isPlaying" class="btn small success" @click="store.play()">
        Play
      </button>
      <button v-else class="btn small warning" @click="store.pause()">
        Pause
      </button>
    </div>
    <div class="speed-control">
      <label>Speed: {{ speed.toFixed(1) }}x</label>
      <input
        type="range"
        min="0.1"
        max="20"
        step="0.1"
        :value="speed"
        @input="onSpeedChange"
      />
    </div>
    <div class="status-row">
      <span class="label">Mode:</span>
      <span :class="['mode-badge', store.clockMode]">{{ store.clockMode }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useSimulationStore } from '../../stores/simulation'

const store = useSimulationStore()
const speed = ref(1.0)

const isPlaying = computed(() => store.clockMode === 'playing')

function onSpeedChange(e: Event) {
  const value = parseFloat((e.target as HTMLInputElement).value)
  speed.value = value
  store.setSpeed(value)
}
</script>

<style scoped>
.control-buttons {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.speed-control {
  margin-bottom: 8px;
}

.speed-control label {
  font-size: 0.8rem;
  color: #90a4ae;
  display: block;
  margin-bottom: 4px;
}

.speed-control input[type="range"] {
  width: 100%;
  accent-color: #4fc3f7;
}

.status-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.label {
  font-size: 0.8rem;
  color: #78909c;
}

.mode-badge {
  font-size: 0.7rem;
  padding: 2px 8px;
  border-radius: 8px;
  text-transform: uppercase;
  font-weight: bold;
}

.mode-badge.paused {
  background: #37474f;
  color: #b0bec5;
}

.mode-badge.playing {
  background: #1b5e20;
  color: #a5d6a7;
}

.mode-badge.stepping {
  background: #e65100;
  color: #ffcc80;
}
</style>
