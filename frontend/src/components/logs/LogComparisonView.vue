<template>
  <div class="log-comparison">
    <div class="panel-title">Log Comparison</div>
    <div class="log-table-wrapper">
      <table class="log-table">
        <thead>
          <tr>
            <th class="index-col">Idx</th>
            <th v-for="node in nodes" :key="node.id" class="node-col">
              {{ node.id.replace('node-', 'N') }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="idx in maxLogIndex" :key="idx">
            <td class="index-col">{{ idx }}</td>
            <td
              v-for="node in nodes"
              :key="node.id"
              :class="cellClass(node, idx)"
            >
              <template v-if="getEntry(node, idx)">
                <span class="term-badge">T{{ getEntry(node, idx)!.term }}</span>
                <span class="cmd">{{ getEntry(node, idx)!.command }}</span>
              </template>
              <span v-else class="empty">-</span>
            </td>
          </tr>
          <tr v-if="maxLogIndex === 0">
            <td :colspan="nodes.length + 1" class="empty-msg">No log entries yet</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useSimulationStore } from '../../stores/simulation'
import type { NodeSnapshot, LogEntry } from '../../types/raft'

const store = useSimulationStore()

const nodes = computed(() => store.snapshot?.nodes ?? [])

const maxLogIndex = computed(() => {
  let max = 0
  for (const node of nodes.value) {
    if (node.log_length > max) max = node.log_length
  }
  return max
})

function getEntry(node: NodeSnapshot, index: number): LogEntry | undefined {
  return node.log.find(e => e.index === index)
}

function cellClass(node: NodeSnapshot, index: number): string {
  const classes = ['entry-cell']
  if (index <= node.commit_index) classes.push('committed')
  const entry = getEntry(node, index)
  if (entry) classes.push(`term-${entry.term % 6}`)
  return classes.join(' ')
}
</script>

<style scoped>
.log-comparison {
  background: #0d1b2a;
  border-top: 1px solid #0f3460;
  padding: 12px;
  max-height: 250px;
  overflow: auto;
}

.log-table-wrapper {
  overflow-x: auto;
}

.log-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.75rem;
}

.log-table th, .log-table td {
  padding: 3px 6px;
  border: 1px solid #1a2a3e;
  text-align: center;
}

.log-table th {
  background: #16213e;
  color: #4fc3f7;
  position: sticky;
  top: 0;
}

.index-col {
  width: 36px;
  color: #78909c;
  font-family: monospace;
}

.entry-cell {
  font-family: monospace;
}

.entry-cell.committed {
  background: rgba(76, 175, 80, 0.15);
  border-color: rgba(76, 175, 80, 0.3);
}

.term-badge {
  font-size: 0.65rem;
  padding: 1px 3px;
  border-radius: 3px;
  margin-right: 3px;
  background: #37474f;
  color: #b0bec5;
}

.cmd {
  color: #e0e0e0;
}

.empty {
  color: #455a64;
}

.empty-msg {
  color: #546e7a;
  font-style: italic;
  padding: 12px;
}

.term-0 { border-left: 3px solid #42a5f5; }
.term-1 { border-left: 3px solid #66bb6a; }
.term-2 { border-left: 3px solid #ffa726; }
.term-3 { border-left: 3px solid #ab47bc; }
.term-4 { border-left: 3px solid #ef5350; }
.term-5 { border-left: 3px solid #26c6da; }
</style>
