import { ref, onUnmounted } from 'vue'
import type { ClusterSnapshot, WsMessage } from '../types/raft'

export function useWebSocket() {
  const connected = ref(false)
  const lastSnapshot = ref<ClusterSnapshot | null>(null)
  let ws: WebSocket | null = null
  let reconnectTimer: number | null = null
  let sessionId: string | null = null

  function connect(sid: string) {
    sessionId = sid
    if (ws) ws.close()

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${protocol}//${window.location.host}/ws/${sid}`
    ws = new WebSocket(url)

    ws.onopen = () => {
      connected.value = true
      if (reconnectTimer) {
        clearTimeout(reconnectTimer)
        reconnectTimer = null
      }
    }

    ws.onmessage = (event) => {
      const msg: WsMessage = JSON.parse(event.data)
      if (msg.type === 'state_snapshot') {
        lastSnapshot.value = msg.data
      }
    }

    ws.onclose = () => {
      connected.value = false
      if (sessionId) {
        reconnectTimer = window.setTimeout(() => connect(sessionId!), 2000)
      }
    }

    ws.onerror = () => {
      ws?.close()
    }
  }

  function disconnect() {
    sessionId = null
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (ws) {
      ws.close()
      ws = null
    }
    connected.value = false
  }

  onUnmounted(disconnect)

  return { connected, lastSnapshot, connect, disconnect }
}
