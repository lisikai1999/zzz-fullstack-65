<template>
  <div class="topology-container" ref="containerRef">
    <svg ref="svgRef" :width="width" :height="height">
      <defs>
        <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
          <polygon points="0 0, 8 3, 0 6" fill="#64b5f6" />
        </marker>
      </defs>

      <!-- Links between nodes -->
      <g class="links">
        <line
          v-for="link in links"
          :key="link.id"
          :x1="link.source.x"
          :y1="link.source.y"
          :x2="link.target.x"
          :y2="link.target.y"
          :class="['link', { partitioned: link.partitioned }]"
          @click="togglePartition(link)"
        />
      </g>

      <!-- In-flight messages -->
      <g class="messages">
        <g
          v-for="msg in animatedMessages"
          :key="msg.id"
          :transform="`translate(${msg.x}, ${msg.y})`"
        >
          <circle r="5" :fill="getMessageColor(msg.message_type)" opacity="0.9" />
          <text dy="-8" text-anchor="middle" font-size="9" fill="#b0bec5">
            {{ msg.message_type.replace('Request', '').replace('Response', 'Resp') }}
          </text>
        </g>
      </g>

      <!-- Nodes -->
      <g class="nodes">
        <g
          v-for="node in renderedNodes"
          :key="node.id"
          :transform="`translate(${node.x}, ${node.y})`"
          class="node-group"
          @mousedown="startDrag(node.id, $event)"
        >
          <circle
            :r="nodeRadius"
            :fill="getRoleFill(node)"
            :stroke="node.alive ? getRoleStroke(node) : '#616161'"
            stroke-width="3"
            :opacity="node.alive ? 1 : 0.4"
          />
          <text dy="4" text-anchor="middle" font-size="11" font-weight="bold" fill="white">
            {{ node.id.replace('node-', 'N') }}
          </text>
          <text dy="22" text-anchor="middle" font-size="9" fill="#b0bec5">
            {{ node.role.charAt(0).toUpperCase() }} | T{{ node.current_term }}
          </text>
          <text dy="34" text-anchor="middle" font-size="8" fill="#78909c">
            Log:{{ node.log_length }} C:{{ node.commit_index }}
          </text>
          <!-- Snapshot badge -->
          <text v-if="node.snapshot_index" dy="46" text-anchor="middle" font-size="7" fill="#ce93d8">
            Snap:{{ node.snapshot_index }}
          </text>
          <!-- Dead X overlay -->
          <g v-if="!node.alive" opacity="0.8">
            <line x1="-12" y1="-12" x2="12" y2="12" stroke="#f44336" stroke-width="3" />
            <line x1="12" y1="-12" x2="-12" y2="12" stroke="#f44336" stroke-width="3" />
          </g>
        </g>
      </g>
    </svg>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { useSimulationStore } from '../../stores/simulation'
import type { NodeSnapshot, InFlightMessage } from '../../types/raft'

const store = useSimulationStore()
const containerRef = ref<HTMLElement | null>(null)
const svgRef = ref<SVGElement | null>(null)

const width = ref(800)
const height = ref(500)
const nodeRadius = 28

// Persistent position storage — survives snapshot updates
const positions = reactive<Record<string, { x: number; y: number }>>({})

interface RenderedNode extends NodeSnapshot {
  x: number
  y: number
}

interface Link {
  id: string
  source: { x: number; y: number; id: string }
  target: { x: number; y: number; id: string }
  partitioned: boolean
}

interface AnimatedMessage extends InFlightMessage {
  x: number
  y: number
}

function getDefaultPosition(nodeId: string, index: number, total: number): { x: number; y: number } {
  const cx = width.value / 2
  const cy = height.value / 2
  const radius = Math.min(width.value, height.value) * 0.35
  const angle = (2 * Math.PI * index) / total - Math.PI / 2
  return {
    x: cx + radius * Math.cos(angle),
    y: cy + radius * Math.sin(angle),
  }
}

// Initialize positions for new nodes only — never overwrite existing
watch(
  () => store.snapshot?.nodes,
  (nodes) => {
    if (!nodes) return
    nodes.forEach((node, i) => {
      if (!(node.id in positions)) {
        const pos = getDefaultPosition(node.id, i, nodes.length)
        positions[node.id] = pos
      }
    })
  },
  { immediate: true }
)

const renderedNodes = computed<RenderedNode[]>(() => {
  const nodes = store.snapshot?.nodes ?? []
  return nodes.map((node) => ({
    ...node,
    x: positions[node.id]?.x ?? 0,
    y: positions[node.id]?.y ?? 0,
  }))
})

const links = computed<Link[]>(() => {
  const nodes = renderedNodes.value
  const partitions = store.snapshot?.partitions ?? []
  const result: Link[] = []

  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const a = nodes[i]
      const b = nodes[j]
      const isPartitioned = partitions.some(
        p => (p.includes(a.id) && p.includes(b.id))
      )
      result.push({
        id: `${a.id}-${b.id}`,
        source: { x: a.x, y: a.y, id: a.id },
        target: { x: b.x, y: b.y, id: b.id },
        partitioned: isPartitioned,
      })
    }
  }
  return result
})

const animatedMessages = computed<AnimatedMessage[]>(() => {
  const messages = store.snapshot?.in_flight_messages ?? []
  const currentTick = store.tick

  return messages.map(msg => {
    const from = positions[msg.from]
    const to = positions[msg.to]
    if (!from || !to) return { ...msg, x: 0, y: 0 }

    const totalTime = msg.deliver_tick - msg.send_tick
    const elapsed = currentTick - msg.send_tick
    const progress = Math.min(1, Math.max(0, elapsed / totalTime))

    return {
      ...msg,
      x: from.x + (to.x - from.x) * progress,
      y: from.y + (to.y - from.y) * progress,
    }
  })
})

function getRoleFill(node: RenderedNode): string {
  if (!node.alive) return '#424242'
  switch (node.role) {
    case 'leader': return '#1b5e20'
    case 'candidate': return '#e65100'
    case 'follower': return '#1a237e'
  }
}

function getRoleStroke(node: RenderedNode): string {
  switch (node.role) {
    case 'leader': return '#4caf50'
    case 'candidate': return '#ff9800'
    case 'follower': return '#42a5f5'
  }
}

function getMessageColor(type: string): string {
  if (type.includes('Vote')) return '#ffeb3b'
  if (type.includes('Append')) return '#4fc3f7'
  if (type.includes('Snapshot')) return '#ce93d8'
  return '#90a4ae'
}

let draggingId: string | null = null

function startDrag(nodeId: string, event: MouseEvent) {
  draggingId = nodeId
  event.preventDefault()
}

function onMouseMove(event: MouseEvent) {
  if (!draggingId || !svgRef.value) return
  const rect = svgRef.value.getBoundingClientRect()
  positions[draggingId] = {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top,
  }
}

function onMouseUp() {
  draggingId = null
}

function togglePartition(link: Link) {
  if (link.partitioned) {
    store.healLink(link.source.id, link.target.id)
  } else {
    store.createPartition([link.source.id], [link.target.id])
  }
}

onMounted(() => {
  if (containerRef.value) {
    const rect = containerRef.value.getBoundingClientRect()
    width.value = rect.width || 800
    height.value = rect.height || 500
  }
  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
})

onUnmounted(() => {
  document.removeEventListener('mousemove', onMouseMove)
  document.removeEventListener('mouseup', onMouseUp)
})
</script>

<style scoped>
.topology-container {
  flex: 1;
  min-height: 400px;
  background: #0d1b2a;
  border-bottom: 1px solid #0f3460;
}

svg {
  width: 100%;
  height: 100%;
}

.link {
  stroke: #2a4a6b;
  stroke-width: 1.5;
  cursor: pointer;
  transition: stroke 0.3s;
}

.link:hover {
  stroke: #4fc3f7;
  stroke-width: 2.5;
}

.link.partitioned {
  stroke: #f44336;
  stroke-width: 2;
  stroke-dasharray: 6 4;
}

.node-group {
  cursor: grab;
  user-select: none;
}

.node-group:active {
  cursor: grabbing;
}
</style>
