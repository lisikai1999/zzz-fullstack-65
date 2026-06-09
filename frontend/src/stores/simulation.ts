import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'
import type { Session, ClusterSnapshot, SessionConfig } from '../types/raft'

export const useSimulationStore = defineStore('simulation', () => {
  const currentSession = ref<Session | null>(null)
  const snapshot = ref<ClusterSnapshot | null>(null)
  const sessions = ref<Session[]>([])
  const loading = ref(false)

  const leader = computed(() =>
    snapshot.value?.nodes.find(n => n.role === 'leader' && n.alive) ?? null
  )

  const tick = computed(() => snapshot.value?.tick ?? 0)
  const clockMode = computed(() => snapshot.value?.clock_mode ?? 'paused')

  async function fetchSessions() {
    const { data } = await axios.get<Session[]>('/api/sessions')
    sessions.value = data
  }

  async function createSession(name: string, config: Partial<SessionConfig>) {
    const { data } = await axios.post<Session>('/api/sessions', { name, config })
    currentSession.value = data
    sessions.value.unshift(data)
    return data
  }

  async function startSimulation(sessionId: string) {
    await axios.post(`/api/sessions/${sessionId}/start`)
  }

  async function step(count = 1) {
    if (!currentSession.value) return
    const { data } = await axios.post(`/api/sessions/${currentSession.value.id}/step`, { count })
    await refreshState()
    return data
  }

  async function play() {
    if (!currentSession.value) return
    await axios.post(`/api/sessions/${currentSession.value.id}/play`)
  }

  async function pause() {
    if (!currentSession.value) return
    await axios.post(`/api/sessions/${currentSession.value.id}/pause`)
    await refreshState()
  }

  async function setSpeed(speed: number) {
    if (!currentSession.value) return
    await axios.put(`/api/sessions/${currentSession.value.id}/speed`, { speed })
  }

  async function refreshState() {
    if (!currentSession.value) return
    const { data } = await axios.get(`/api/sessions/${currentSession.value.id}/state`)
    snapshot.value = data
  }

  async function killNode(nodeId: string) {
    if (!currentSession.value) return
    await axios.post(`/api/sessions/${currentSession.value.id}/nodes/${nodeId}/kill`)
    await refreshState()
  }

  async function restartNode(nodeId: string) {
    if (!currentSession.value) return
    await axios.post(`/api/sessions/${currentSession.value.id}/nodes/${nodeId}/restart`)
    await refreshState()
  }

  async function proposeCommand(nodeId: string, command: string) {
    if (!currentSession.value) return
    await axios.post(`/api/sessions/${currentSession.value.id}/nodes/${nodeId}/propose`, { command })
    await refreshState()
  }

  async function createPartition(groupA: string[], groupB: string[]) {
    if (!currentSession.value) return
    await axios.post(`/api/sessions/${currentSession.value.id}/network/partition`, {
      group_a: groupA,
      group_b: groupB,
    })
    await refreshState()
  }

  async function healPartition() {
    if (!currentSession.value) return
    await axios.post(`/api/sessions/${currentSession.value.id}/network/heal`)
    await refreshState()
  }

  async function healLink(nodeA: string, nodeB: string) {
    if (!currentSession.value) return
    await axios.post(`/api/sessions/${currentSession.value.id}/network/heal-link`, {
      node_a: nodeA,
      node_b: nodeB,
    })
    await refreshState()
  }

  async function dropMessage(fromNode: string, toNode: string) {
    if (!currentSession.value) return
    await axios.post(`/api/sessions/${currentSession.value.id}/fault/drop-message`, {
      from_node: fromNode,
      to_node: toNode,
    })
  }

  async function duplicateMessage(fromNode: string, toNode: string) {
    if (!currentSession.value) return
    await axios.post(`/api/sessions/${currentSession.value.id}/fault/duplicate-message`, {
      from_node: fromNode,
      to_node: toNode,
    })
  }

  async function updateNetworkConfig(config: { base_delay?: number; delay_jitter?: number; packet_loss_rate?: number }) {
    if (!currentSession.value) return
    await axios.put(`/api/sessions/${currentSession.value.id}/network/config`, config)
  }

  function updateSnapshot(s: ClusterSnapshot) {
    snapshot.value = s
  }

  return {
    currentSession, snapshot, sessions, loading,
    leader, tick, clockMode,
    fetchSessions, createSession, startSimulation,
    step, play, pause, setSpeed, refreshState,
    killNode, restartNode, proposeCommand,
    createPartition, healPartition, healLink,
    dropMessage, duplicateMessage,
    updateNetworkConfig, updateSnapshot,
  }
})
