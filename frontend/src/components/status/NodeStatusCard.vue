<template>
  <div :class="['node-card', node.role, { dead: !node.alive }]">
    <div class="card-header">
      <span class="node-id">{{ node.id }}</span>
      <span :class="['role-badge', node.role]">{{ node.role }}</span>
    </div>
    <div class="card-body">
      <div class="stat">
        <span class="stat-label">Term</span>
        <span class="stat-value">{{ node.current_term }}</span>
      </div>
      <div class="stat">
        <span class="stat-label">Log</span>
        <span class="stat-value">{{ node.log_length }}</span>
      </div>
      <div class="stat">
        <span class="stat-label">Commit</span>
        <span class="stat-value">{{ node.commit_index }}</span>
      </div>
      <div class="stat">
        <span class="stat-label">Applied</span>
        <span class="stat-value">{{ node.last_applied }}</span>
      </div>
    </div>
    <div v-if="node.snapshot_index" class="snapshot-info">
      <span class="snap-label">Snapshot:</span>
      <span class="snap-value">idx={{ node.snapshot_index }} term={{ node.snapshot_term }}</span>
    </div>
    <div v-if="!node.alive" class="dead-overlay">DEAD</div>
  </div>
</template>

<script setup lang="ts">
import type { NodeSnapshot } from '../../types/raft'

const props = defineProps<{ node: NodeSnapshot }>()
</script>

<style scoped>
.node-card {
  border: 1px solid #0f3460;
  border-radius: 6px;
  padding: 8px;
  position: relative;
  overflow: hidden;
  transition: border-color 0.3s;
}

.node-card.leader {
  border-color: #4caf50;
  background: rgba(76, 175, 80, 0.05);
}

.node-card.candidate {
  border-color: #ff9800;
  background: rgba(255, 152, 0, 0.05);
}

.node-card.follower {
  border-color: #2196f3;
  background: rgba(33, 150, 243, 0.05);
}

.node-card.dead {
  opacity: 0.5;
  border-color: #616161;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.node-id {
  font-weight: bold;
  font-size: 0.8rem;
}

.role-badge {
  font-size: 0.65rem;
  padding: 2px 6px;
  border-radius: 8px;
  text-transform: uppercase;
  font-weight: bold;
}

.role-badge.leader {
  background: #1b5e20;
  color: #a5d6a7;
}

.role-badge.candidate {
  background: #e65100;
  color: #ffcc80;
}

.role-badge.follower {
  background: #0d47a1;
  color: #90caf9;
}

.card-body {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 4px;
}

.stat {
  text-align: center;
}

.stat-label {
  display: block;
  font-size: 0.6rem;
  color: #78909c;
  text-transform: uppercase;
}

.stat-value {
  font-size: 0.85rem;
  font-weight: bold;
  font-family: monospace;
}

.dead-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%) rotate(-20deg);
  font-size: 1.5rem;
  font-weight: bold;
  color: #f44336;
  opacity: 0.5;
  pointer-events: none;
}

.snapshot-info {
  margin-top: 4px;
  padding-top: 4px;
  border-top: 1px solid #1a2a3e;
  font-size: 0.65rem;
}

.snap-label {
  color: #ce93d8;
  margin-right: 4px;
}

.snap-value {
  color: #b0bec5;
  font-family: monospace;
}
</style>
