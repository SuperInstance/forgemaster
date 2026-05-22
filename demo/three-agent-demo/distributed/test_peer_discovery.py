"""Tests for UDP peer discovery."""

import socket
import struct
import time
from fractions import Fraction

import pytest

from .fleet_protocol import encode_beacon, encode_leave, now_ms
from .peer_discovery import PeerDiscovery, PeerInfo


THETA = {
    "T": Fraction(1, 2),
    "phi0": 1234567890,
    "epsilon": Fraction(1, 1000),
    "delta": Fraction(1, 100),
}


# ------------------------------------------------------------------
# Unit tests (no real network)
# ------------------------------------------------------------------

def test_peer_table_add_and_get():
    pd = PeerDiscovery(node_id=1, theta=THETA)
    pd._handle_beacon(
        sender=2,
        addr=("127.0.0.1", 9999),
        msg={
            "payload": {
                "uptime_ms": 1000,
                "theta": THETA,
                "known_peers": {3},
            }
        },
    )
    assert pd.peer_count() == 1
    p = pd.get_peer(2)
    assert p is not None
    assert p.node_id == 2
    assert p.uptime_ms == 1000
    assert p.known_peers == {3}


def test_peer_table_ignore_self():
    pd = PeerDiscovery(node_id=1, theta=THETA)
    pd._handle_beacon(
        sender=1,
        addr=("127.0.0.1", 9999),
        msg={"payload": {"uptime_ms": 0, "theta": THETA, "known_peers": set()}},
    )
    assert pd.peer_count() == 0


def test_peer_leave():
    pd = PeerDiscovery(node_id=1, theta=THETA)
    pd._handle_beacon(
        sender=2,
        addr=("127.0.0.1", 9999),
        msg={"payload": {"uptime_ms": 0, "theta": THETA, "known_peers": set()}},
    )
    assert pd.peer_count() == 1
    pd._handle_leave(2, {"payload": {"node_id": 2}})
    assert pd.peer_count() == 0


def test_peer_timeout():
    pd = PeerDiscovery(node_id=1, theta=THETA)
    # Inject a stale peer directly
    stale = PeerInfo(
        node_id=2,
        last_seen=time.monotonic() - 100,  # very old
        uptime_ms=0,
        theta=THETA,
        addr=("127.0.0.1", 9999),
    )
    pd._peers[2] = stale
    assert pd.peer_count() == 1
    # Run janitor logic manually
    now = time.monotonic()
    timed_out = []
    with pd._lock:
        for pid, info in list(pd._peers.items()):
            if now - info.last_seen > pd.PEER_TIMEOUT:
                timed_out.append(pid)
                del pd._peers[pid]
    assert timed_out == [2]
    assert pd.peer_count() == 0


def test_merge_callback():
    merge_called = []

    def on_merge(foreign):
        merge_called.append(foreign)

    pd = PeerDiscovery(node_id=1, theta=THETA, on_merge=on_merge)
    # We know peer 2
    pd._peers[2] = PeerInfo(
        node_id=2,
        last_seen=time.monotonic(),
        uptime_ms=0,
        theta=THETA,
        addr=("127.0.0.1", 9999),
    )
    # Peer 3 arrives and claims to know peer 4 (unknown to us)
    pd._handle_beacon(
        sender=3,
        addr=("127.0.0.1", 9998),
        msg={"payload": {"uptime_ms": 0, "theta": THETA, "known_peers": {4, 5}}},
    )
    assert len(merge_called) == 1
    assert merge_called[0] == {4, 5}


def test_peer_join_leave_callbacks():
    events = []

    pd = PeerDiscovery(
        node_id=1,
        theta=THETA,
        on_peer_join=lambda p: events.append(("join", p.node_id)),
        on_peer_leave=lambda nid: events.append(("leave", nid)),
    )
    pd._handle_beacon(
        sender=7,
        addr=("127.0.0.1", 9997),
        msg={"payload": {"uptime_ms": 0, "theta": THETA, "known_peers": set()}},
    )
    assert events == [("join", 7)]
    pd._handle_leave(7, {"payload": {"node_id": 7}})
    assert events == [("join", 7), ("leave", 7)]


def test_known_peers_for_beacon():
    pd = PeerDiscovery(node_id=1, theta=THETA)
    pd._peers[2] = PeerInfo(2, time.monotonic(), 0, THETA, ("127.0.0.1", 0))
    pd._peers[3] = PeerInfo(3, time.monotonic(), 0, THETA, ("127.0.0.1", 0))
    assert pd.known_peers_for_beacon() == {2, 3}


# ------------------------------------------------------------------
# Integration tests with real UDP sockets
# ------------------------------------------------------------------

def test_udp_beacon_reception():
    """A plain UDP socket sends a BEACON to a PeerDiscovery instance."""
    pd = PeerDiscovery(node_id=1, theta=THETA, bind_addr="127.0.0.1", port=0)
    pd.start()
    try:
        ip, port = pd.local_addr
        # Build a BEACON from node 42
        pkt = encode_beacon(
            sender_id=42,
            timestamp_ms=now_ms(),
            uptime_ms=1234,
            theta=THETA,
            known_peers={99},
        )
        # Send unicast directly to the bound address
        sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sender.sendto(pkt, (ip, port))
        sender.close()

        # Wait for the listener thread to process
        time.sleep(0.5)

        assert pd.peer_count() == 1
        p = pd.get_peer(42)
        assert p is not None
        assert p.uptime_ms == 1234
        assert p.known_peers == {99}
    finally:
        pd.stop()


def test_udp_leave_reception():
    """A LEAVE message removes a peer."""
    pd = PeerDiscovery(node_id=1, theta=THETA, bind_addr="127.0.0.1", port=0)
    pd.start()
    try:
        ip, port = pd.local_addr
        # First add peer 7
        beacon = encode_beacon(
            sender_id=7,
            timestamp_ms=now_ms(),
            uptime_ms=0,
            theta=THETA,
            known_peers=set(),
        )
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.sendto(beacon, (ip, port))
        time.sleep(0.3)
        assert pd.get_peer(7) is not None

        # Now send LEAVE
        leave_pkt = encode_leave(
            sender_id=7,
            timestamp_ms=now_ms(),
            node_id=7,
        )
        s.sendto(leave_pkt, (ip, port))
        s.close()
        time.sleep(0.3)
        assert pd.get_peer(7) is None
    finally:
        pd.stop()


def test_two_instances_discovery():
    """Two PeerDiscovery instances on the same port with SO_REUSEADDR."""
    port = 54321
    theta_a = dict(THETA, phi0=1000)
    theta_b = dict(THETA, phi0=2000)

    # Use a multicast group that works on loopback
    group = "224.0.0.1"

    pd_a = PeerDiscovery(
        node_id=10,
        theta=theta_a,
        bind_addr="127.0.0.1",
        multicast_group=group,
        port=port,
    )
    pd_b = PeerDiscovery(
        node_id=20,
        theta=theta_b,
        bind_addr="127.0.0.1",
        multicast_group=group,
        port=port,
    )

    pd_a.start()
    pd_b.start()
    try:
        # Wait for beacons to be exchanged
        time.sleep(1.5)

        # Both should see each other
        assert 20 in pd_a.peer_ids()
        assert 10 in pd_b.peer_ids()

        a_views_b = pd_a.get_peer(20)
        assert a_views_b is not None
        assert a_views_b.theta["phi0"] == 2000
    finally:
        pd_a.stop()
        pd_b.stop()
