<template>
  <div class="panel">
    <div class="panel-title">Event Timeline</div>
    <div class="timeline-scroll">
      <div
        v-for="(event, i) in recentEvents"
        :key="i"
        :class="['event-item', event.event_type]"
      >
        <span class="event-tick">{{ event.tick }}</span>
        <span :class="['event-dot', eventColor(event.event_type)]"></span>
        <span class="event-desc">{{ event.description }}</span>
      </div>
      <div v-if="recentEvents.length === 0" class="empty">No events yet</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useSimulationStore } from '../../stores/simulation'
import type { SimulationEvent } from '../../types/raft'

const store = useSimulationStore()

const recentEvents = computed(() => {
  const events = store.snapshot?.events_recent ?? []
  return events.slice(-20).reverse()
})

function eventColor(type: string): string {
  if (type.includes('leader')) return 'green'
  if (type.includes('election')) return 'orange'
  if (type.includes('vote')) return 'yellow'
  if (type.includes('partition')) return 'red'
  if (type.includes('commit') || type.includes('applied')) return 'cyan'
  return 'blue'
}
</script>

<style scoped>
.timeline-scroll {
  max-height: 200px;
  overflow-y: auto;
}

.event-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 0;
  border-bottom: 1px solid #1a2a3e;
  font-size: 0.72rem;
}

.event-tick {
  font-family: monospace;
  color: #78909c;
  min-width: 40px;
  text-align: right;
}

.event-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.event-dot.green { background: #4caf50; }
.event-dot.orange { background: #ff9800; }
.event-dot.yellow { background: #ffeb3b; }
.event-dot.red { background: #f44336; }
.event-dot.cyan { background: #00bcd4; }
.event-dot.blue { background: #2196f3; }

.event-desc {
  color: #b0bec5;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.empty {
  color: #546e7a;
  font-size: 0.8rem;
  font-style: italic;
  padding: 8px 0;
}
</style>
