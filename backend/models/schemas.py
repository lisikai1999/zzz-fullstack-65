from pydantic import BaseModel, Field
from typing import Optional


class ClusterConfigSchema(BaseModel):
    node_count: int = Field(default=5, ge=3, le=9)
    base_delay: int = Field(default=15, ge=1, le=500)
    delay_jitter: int = Field(default=10, ge=0, le=200)
    packet_loss_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    election_timeout_min: int = Field(default=150, ge=50, le=1000)
    election_timeout_max: int = Field(default=300, ge=100, le=2000)
    heartbeat_interval: int = Field(default=50, ge=10, le=500)


class SessionCreate(BaseModel):
    name: str = Field(default="Untitled Session", max_length=100)
    config: ClusterConfigSchema = Field(default_factory=ClusterConfigSchema)


class SessionResponse(BaseModel):
    id: str
    name: str
    node_count: int
    config: ClusterConfigSchema
    created_at: str
    updated_at: str


class NetworkConfigUpdate(BaseModel):
    base_delay: Optional[int] = Field(default=None, ge=1, le=500)
    delay_jitter: Optional[int] = Field(default=None, ge=0, le=200)
    packet_loss_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class PartitionRequest(BaseModel):
    group_a: list[str]
    group_b: list[str]


class ProposeRequest(BaseModel):
    command: str = Field(max_length=200)


class FaultRequest(BaseModel):
    from_node: str
    to_node: str


class HealLinkRequest(BaseModel):
    node_a: str
    node_b: str


class StepRequest(BaseModel):
    count: int = Field(default=1, ge=1, le=10000)


class SpeedRequest(BaseModel):
    speed: float = Field(ge=0.1, le=100.0)
