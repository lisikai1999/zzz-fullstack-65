<template>
  <div id="app-root">
    <header class="app-header">
      <h1>Raft Consensus Simulator</h1>
      <div class="header-info">
        <span class="tick-display">Tick: {{ store.tick }}</span>
        <span :class="['connection-status', wsConnected ? 'connected' : 'disconnected']">
          {{ wsConnected ? 'Connected' : 'Disconnected' }}
        </span>
      </div>
    </header>

    <div v-if="!store.currentSession" class="setup-panel">
      <h2>Create Simulation</h2>
      <div class="form-row">
        <label>Session Name:</label>
        <input v-model="sessionName" placeholder="My Raft Experiment" />
      </div>
      <div class="form-row">
        <label>Nodes (3-9):</label>
        <input v-model.number="nodeCount" type="number" min="3" max="9" />
      </div>
      <div class="form-row">
        <label>Network Delay (ms):</label>
        <input v-model.number="baseDelay" type="number" min="1" max="500" />
      </div>
      <div class="form-row">
        <label>Packet Loss Rate:</label>
        <input v-model.number="lossRate" type="number" min="0" max="1" step="0.05" />
      </div>
      <button class="btn primary" @click="createAndStart">Start Simulation</button>
    </div>

    <div v-else class="main-layout">
      <div class="left-panel">
        <TopologyGraph />
        <LogComparisonView />
      </div>
      <div class="right-panel">
        <GlobalControlPanel />
        <FaultInjectionPanel />
        <ClusterConfigPanel />
        <div class="node-cards">
          <NodeStatusCard
            v-for="node in store.snapshot?.nodes ?? []"
            :key="node.id"
            :node="node"
          />
        </div>
        <EventTimeline />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useSimulationStore } from './stores/simulation'
import { useWebSocket } from './composables/useWebSocket'
import TopologyGraph from './components/topology/TopologyGraph.vue'
import GlobalControlPanel from './components/controls/GlobalControlPanel.vue'
import FaultInjectionPanel from './components/controls/FaultInjectionPanel.vue'
import ClusterConfigPanel from './components/controls/ClusterConfigPanel.vue'
import LogComparisonView from './components/logs/LogComparisonView.vue'
import EventTimeline from './components/timeline/EventTimeline.vue'
import NodeStatusCard from './components/status/NodeStatusCard.vue'

const store = useSimulationStore()
const { connected: wsConnected, lastSnapshot, connect: wsConnect } = useWebSocket()

const sessionName = ref('Raft Experiment')
const nodeCount = ref(5)
const baseDelay = ref(15)
const lossRate = ref(0)

watch(lastSnapshot, (snapshot) => {
  if (snapshot) store.updateSnapshot(snapshot)
})

async function createAndStart() {
  const session = await store.createSession(sessionName.value, {
    node_count: nodeCount.value,
    base_delay: baseDelay.value,
    packet_loss_rate: lossRate.value,
  })
  await store.startSimulation(session.id)
  await store.refreshState()
  wsConnect(session.id)
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #1a1a2e;
  color: #e0e0e0;
  min-height: 100vh;
}

#app-root {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 24px;
  background: #16213e;
  border-bottom: 1px solid #0f3460;
}

.app-header h1 {
  font-size: 1.3rem;
  color: #4fc3f7;
}

.header-info {
  display: flex;
  gap: 16px;
  align-items: center;
}

.tick-display {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.9rem;
  color: #81c784;
}

.connection-status {
  font-size: 0.75rem;
  padding: 3px 8px;
  border-radius: 10px;
}

.connection-status.connected {
  background: #1b5e20;
  color: #a5d6a7;
}

.connection-status.disconnected {
  background: #b71c1c;
  color: #ef9a9a;
}

.setup-panel {
  max-width: 400px;
  margin: 60px auto;
  padding: 32px;
  background: #16213e;
  border-radius: 12px;
  border: 1px solid #0f3460;
}

.setup-panel h2 {
  margin-bottom: 20px;
  color: #4fc3f7;
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 12px;
}

.form-row label {
  font-size: 0.85rem;
  color: #90a4ae;
}

.form-row input {
  padding: 8px 12px;
  background: #1a1a2e;
  border: 1px solid #0f3460;
  border-radius: 6px;
  color: #e0e0e0;
  font-size: 0.9rem;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 600;
  transition: all 0.2s;
}

.btn.primary {
  background: #1976d2;
  color: white;
  width: 100%;
  margin-top: 8px;
}

.btn.primary:hover {
  background: #1565c0;
}

.btn.danger {
  background: #c62828;
  color: white;
}

.btn.danger:hover {
  background: #b71c1c;
}

.btn.success {
  background: #2e7d32;
  color: white;
}

.btn.warning {
  background: #f57f17;
  color: white;
}

.btn.small {
  padding: 4px 10px;
  font-size: 0.75rem;
}

.main-layout {
  display: grid;
  grid-template-columns: 1fr 360px;
  flex: 1;
  overflow: hidden;
}

.left-panel {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.right-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px;
  overflow-y: auto;
  background: #16213e;
  border-left: 1px solid #0f3460;
}

.node-cards {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.panel {
  background: #1a1a2e;
  border: 1px solid #0f3460;
  border-radius: 8px;
  padding: 12px;
}

.panel-title {
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #4fc3f7;
  margin-bottom: 8px;
}
</style>
