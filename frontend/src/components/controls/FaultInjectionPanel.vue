<template>
  <div class="panel">
    <div class="panel-title">Fault Injection</div>

    <div class="section">
      <label class="section-label">Node Control</label>
      <div class="node-buttons">
        <div v-for="node in nodes" :key="node.id" class="node-action">
          <span class="node-name">{{ node.id.replace('node-', 'N') }}</span>
          <button
            v-if="node.alive"
            class="btn small danger"
            @click="store.killNode(node.id)"
          >Kill</button>
          <button
            v-else
            class="btn small success"
            @click="store.restartNode(node.id)"
          >Restart</button>
        </div>
      </div>
    </div>

    <div class="section">
      <label class="section-label">Network Partition</label>
      <div class="partition-controls">
        <div class="partition-select">
          <select v-model="partitionA" multiple size="3">
            <option v-for="node in nodes" :key="node.id" :value="node.id">
              {{ node.id }}
            </option>
          </select>
          <span class="separator">|</span>
          <select v-model="partitionB" multiple size="3">
            <option v-for="node in nodes" :key="node.id" :value="node.id">
              {{ node.id }}
            </option>
          </select>
        </div>
        <div class="partition-actions">
          <button class="btn small danger" @click="applyPartition" :disabled="!canPartition">
            Partition
          </button>
          <button class="btn small success" @click="store.healPartition()">
            Heal All
          </button>
        </div>
      </div>
    </div>

    <div class="section">
      <label class="section-label">Message Fault (next message on link)</label>
      <div class="msg-fault-row">
        <select v-model="faultFrom" class="node-select">
          <option value="" disabled>From</option>
          <option v-for="node in nodes" :key="node.id" :value="node.id">
            {{ node.id.replace('node-', 'N') }}
          </option>
        </select>
        <span class="arrow">&rarr;</span>
        <select v-model="faultTo" class="node-select">
          <option value="" disabled>To</option>
          <option v-for="node in nodes" :key="node.id" :value="node.id">
            {{ node.id.replace('node-', 'N') }}
          </option>
        </select>
      </div>
      <div class="msg-fault-actions">
        <button
          class="btn small danger"
          :disabled="!canFault"
          @click="dropMsg"
        >Drop Next</button>
        <button
          class="btn small warning"
          :disabled="!canFault"
          @click="dupMsg"
        >Duplicate Next</button>
      </div>
    </div>

    <div class="section">
      <label class="section-label">Client Command</label>
      <div class="command-row">
        <input v-model="command" placeholder="key=value" @keyup.enter="submitCommand" />
        <button class="btn small primary" @click="submitCommand" :disabled="!leader">
          Propose
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useSimulationStore } from '../../stores/simulation'

const store = useSimulationStore()

const partitionA = ref<string[]>([])
const partitionB = ref<string[]>([])
const command = ref('')
const faultFrom = ref('')
const faultTo = ref('')

const nodes = computed(() => store.snapshot?.nodes ?? [])
const leader = computed(() => store.leader)

const canPartition = computed(() => partitionA.value.length > 0 && partitionB.value.length > 0)
const canFault = computed(() => faultFrom.value !== '' && faultTo.value !== '' && faultFrom.value !== faultTo.value)

function applyPartition() {
  if (canPartition.value) {
    store.createPartition(partitionA.value, partitionB.value)
  }
}

function dropMsg() {
  if (canFault.value) {
    store.dropMessage(faultFrom.value, faultTo.value)
  }
}

function dupMsg() {
  if (canFault.value) {
    store.duplicateMessage(faultFrom.value, faultTo.value)
  }
}

function submitCommand() {
  if (leader.value && command.value) {
    store.proposeCommand(leader.value.id, command.value)
    command.value = ''
  }
}
</script>

<style scoped>
.section {
  margin-bottom: 12px;
}

.section-label {
  font-size: 0.75rem;
  color: #78909c;
  display: block;
  margin-bottom: 4px;
}

.node-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.node-action {
  display: flex;
  align-items: center;
  gap: 4px;
}

.node-name {
  font-size: 0.75rem;
  font-weight: bold;
  color: #b0bec5;
  width: 24px;
}

.partition-select {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.partition-select select {
  flex: 1;
  background: #1a1a2e;
  color: #e0e0e0;
  border: 1px solid #0f3460;
  border-radius: 4px;
  font-size: 0.75rem;
  padding: 2px;
}

.separator {
  color: #f44336;
  font-weight: bold;
  font-size: 1.2rem;
}

.partition-actions {
  display: flex;
  gap: 6px;
}

.msg-fault-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.node-select {
  flex: 1;
  background: #1a1a2e;
  color: #e0e0e0;
  border: 1px solid #0f3460;
  border-radius: 4px;
  font-size: 0.75rem;
  padding: 4px;
}

.arrow {
  color: #78909c;
  font-size: 1rem;
}

.msg-fault-actions {
  display: flex;
  gap: 6px;
}

.command-row {
  display: flex;
  gap: 6px;
}

.command-row input {
  flex: 1;
  padding: 4px 8px;
  background: #1a1a2e;
  border: 1px solid #0f3460;
  border-radius: 4px;
  color: #e0e0e0;
  font-size: 0.8rem;
}
</style>
