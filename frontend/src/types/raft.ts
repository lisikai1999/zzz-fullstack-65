export interface LogEntry {
  term: number
  index: number
  command: string
}

export interface NodeSnapshot {
  id: string
  role: 'follower' | 'candidate' | 'leader'
  alive: boolean
  current_term: number
  voted_for: string | null
  log: LogEntry[]
  log_length: number
  commit_index: number
  last_applied: number
  leader_id: string | null
  next_index: Record<string, number> | null
  match_index: Record<string, number> | null
  snapshot_index: number | null
  snapshot_term: number | null
}

export interface InFlightMessage {
  id: string
  from: string
  to: string
  message_type: string
  send_tick: number
  deliver_tick: number
}

export interface SimulationEvent {
  tick: number
  event_type: string
  source_node: string | null
  target_node: string | null
  description: string
  payload: Record<string, any>
}

export interface ClusterSnapshot {
  tick: number
  clock_mode: 'paused' | 'playing' | 'stepping'
  speed: number
  nodes: NodeSnapshot[]
  in_flight_messages: InFlightMessage[]
  partitions: string[][]
  events_recent: SimulationEvent[]
}

export interface SessionConfig {
  node_count: number
  base_delay: number
  delay_jitter: number
  packet_loss_rate: number
  election_timeout_min: number
  election_timeout_max: number
  heartbeat_interval: number
}

export interface Session {
  id: string
  name: string
  node_count: number
  config: SessionConfig
  created_at: string
  updated_at: string
}

export type WsMessage =
  | { type: 'state_snapshot'; data: ClusterSnapshot }
  | { type: 'event'; data: SimulationEvent }
  | { type: 'pong' }
  | { type: 'error'; message: string }
