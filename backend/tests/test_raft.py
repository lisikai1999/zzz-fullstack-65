"""Tests for the Raft consensus implementation."""
import sys
import os
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.cluster import SimulationCluster, ClusterConfig


def test_leader_election():
    """A cluster should elect exactly one leader."""
    random.seed(42)
    sim = SimulationCluster(ClusterConfig(node_count=3))
    for _ in range(1000):
        sim.step()
    leaders = [n for n in sim.nodes.values() if n.role.value == 'leader']
    assert len(leaders) == 1, f"Expected 1 leader, got {len(leaders)}"
    print("PASS: test_leader_election")


def test_log_replication():
    """Proposed commands should replicate to a majority."""
    random.seed(42)
    sim = SimulationCluster(ClusterConfig(node_count=5))
    for _ in range(1000):
        sim.step()
    leader = next(n for n in sim.nodes.values() if n.role.value == 'leader')

    sim.propose_command(leader.node_id, 'x=1')
    sim.propose_command(leader.node_id, 'y=2')
    for _ in range(300):
        sim.step()

    committed = [n for n in sim.nodes.values() if n.commit_index >= 2]
    assert len(committed) >= 3, f"Expected majority committed, got {len(committed)}"
    assert leader.state_machine.get('x') == '1'
    assert leader.state_machine.get('y') == '2'
    print("PASS: test_log_replication")


def test_leader_failover():
    """Killing the leader should result in a new election."""
    random.seed(42)
    sim = SimulationCluster(ClusterConfig(node_count=3))
    for _ in range(1000):
        sim.step()
    leader = next(n for n in sim.nodes.values() if n.role.value == 'leader')

    sim.fault_injector.kill_node(leader.node_id)
    for _ in range(1500):
        sim.step()

    alive_leaders = [n for n in sim.nodes.values()
                     if n.role.value == 'leader' and n.node_id in sim.alive_nodes]
    assert len(alive_leaders) == 1
    assert alive_leaders[0].node_id != leader.node_id
    print("PASS: test_leader_failover")


def test_network_partition():
    """Majority partition should elect a new leader; minority should not."""
    random.seed(77)
    sim = SimulationCluster(ClusterConfig(node_count=5))
    for _ in range(1000):
        sim.step()
    leader = next(n for n in sim.nodes.values() if n.role.value == 'leader')

    minority = [leader.node_id]
    majority = [n for n in sim.nodes if n != leader.node_id]
    sim.fault_injector.partition(minority, majority)

    for _ in range(1500):
        sim.step()

    majority_leaders = [n for n in sim.nodes.values()
                        if n.role.value == 'leader' and n.node_id in majority]
    assert len(majority_leaders) == 1
    assert majority_leaders[0].current_term > leader.current_term
    print("PASS: test_network_partition")


def test_partition_healing():
    """After healing, cluster should converge to single leader."""
    random.seed(33)
    sim = SimulationCluster(ClusterConfig(node_count=5))
    for _ in range(1000):
        sim.step()
    leader = next(n for n in sim.nodes.values() if n.role.value == 'leader')

    minority = [leader.node_id]
    majority = [n for n in sim.nodes if n != leader.node_id]
    sim.fault_injector.partition(minority, majority)
    for _ in range(1500):
        sim.step()

    sim.fault_injector.heal_partition()
    for _ in range(1000):
        sim.step()

    all_leaders = [n for n in sim.nodes.values() if n.role.value == 'leader']
    assert len(all_leaders) == 1
    print("PASS: test_partition_healing")


def test_log_conflict_resolution():
    """Conflicting logs should be resolved after partition heals."""
    random.seed(55)
    sim = SimulationCluster(ClusterConfig(node_count=5))
    for _ in range(1000):
        sim.step()
    leader = next(n for n in sim.nodes.values() if n.role.value == 'leader')

    sim.propose_command(leader.node_id, 'x=before')
    for _ in range(300):
        sim.step()

    # Partition: isolate old leader
    minority = [leader.node_id]
    majority = [n for n in sim.nodes if n != leader.node_id]
    sim.fault_injector.partition(minority, majority)

    for _ in range(1500):
        sim.step()

    new_leader = next(n for n in sim.nodes.values()
                      if n.role.value == 'leader' and n.node_id in majority)
    sim.propose_command(new_leader.node_id, 'x=after')
    for _ in range(300):
        sim.step()

    # Heal
    sim.fault_injector.heal_partition()
    for _ in range(1500):
        sim.step()

    # All alive nodes should agree on state
    final_leaders = [n for n in sim.nodes.values() if n.role.value == 'leader']
    assert len(final_leaders) == 1
    final_leader = final_leaders[0]
    assert final_leader.state_machine.get('x') == 'after'
    print("PASS: test_log_conflict_resolution")


def test_node_restart_preserves_state():
    """Restarted node should retain its log."""
    random.seed(42)
    sim = SimulationCluster(ClusterConfig(node_count=3))
    for _ in range(1000):
        sim.step()
    leader = next(n for n in sim.nodes.values() if n.role.value == 'leader')

    sim.propose_command(leader.node_id, 'a=1')
    for _ in range(300):
        sim.step()

    # Pick a follower, kill and restart
    follower_id = next(n for n in sim.nodes if n != leader.node_id)
    log_before = sim.nodes[follower_id].log.last_index
    sim.fault_injector.kill_node(follower_id)
    sim.fault_injector.restart_node(follower_id)
    log_after = sim.nodes[follower_id].log.last_index

    assert log_after == log_before, "Log should be preserved across restart"
    print("PASS: test_node_restart_preserves_state")


if __name__ == '__main__':
    test_leader_election()
    test_log_replication()
    test_leader_failover()
    test_network_partition()
    test_partition_healing()
    test_log_conflict_resolution()
    test_node_restart_preserves_state()
    print("\n=== ALL TESTS PASSED ===")
