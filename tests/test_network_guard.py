"""
Tests for the network guard in tests/conftest.py.

None of these tests sends a packet off the machine: external targets are TEST-NET-1
(192.0.2.0/24, never routed) or names that the guard rejects before any DNS lookup.
"""

import asyncio
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

CONFTEST = Path(__file__).resolve().parent / "conftest.py"
REPO_ROOT = Path(__file__).resolve().parents[1]


def _assert_guard_active():
    assert getattr(socket.socket.connect, "network_guard", False), "network guard is not installed"


def _take_violations(request) -> list[str]:
    """Returns and clears the violations recorded for this test, so an expected block
    does not fail the test that provoked it on purpose."""
    violations = getattr(request.node, "network_violations", None)
    assert violations is not None, "network guard did not attach a violations list to the test"
    taken = list(violations)
    violations.clear()
    return taken


# =====================================================================
# EXTERNAL TARGETS ARE BLOCKED AND RECORDED
# =====================================================================

def test_guard_blocks_external_connect_immediately(request):
    _assert_guard_active()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    try:
        start = time.monotonic()
        with pytest.raises(OSError, match=r"192\.0\.2\.1:9"):
            sock.connect(("192.0.2.1", 9))
        with pytest.raises(OSError, match=r"192\.0\.2\.1:9"):
            sock.connect_ex(("192.0.2.1", 9))
        elapsed = time.monotonic() - start
    finally:
        sock.close()

    assert elapsed < 0.5
    assert _take_violations(request) == ["connect 192.0.2.1:9", "connect_ex 192.0.2.1:9"]


def test_guard_blocks_external_name_lookup_before_dns(request):
    _assert_guard_active()

    with pytest.raises(OSError, match=r"api\.todoist\.com:443"):
        socket.getaddrinfo("api.todoist.com", 443)
    with pytest.raises(OSError, match=r"plugvan-test\.invalid"):
        socket.gethostbyname("plugvan-test.invalid")

    assert _take_violations(request) == [
        "getaddrinfo api.todoist.com:443",
        "gethostbyname plugvan-test.invalid",
    ]


def test_swallowed_network_attempt_still_fails_the_test(tmp_path):
    """Application code may catch every Exception; the guard must still fail the test.

    Runs an inner pytest session in a subprocess with a copy of the real conftest, so the
    inner guard and its socket patches are fully isolated from this session."""
    _assert_guard_active()
    (tmp_path / "conftest.py").write_text(CONFTEST.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "test_inner.py").write_text(
        "import socket\n"
        "import urllib.request\n"
        "\n"
        "def test_swallowed_socket_connect():\n"
        "    try:\n"
        "        socket.create_connection(('192.0.2.1', 443), timeout=1)\n"
        "    except Exception:\n"
        "        pass\n"
        "\n"
        "def test_swallowed_http_request():\n"
        "    try:\n"
        "        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))\n"
        "        opener.open('http://192.0.2.1:80/api/v1/projects', timeout=1)\n"
        "    except Exception:\n"
        "        pass\n"
        "\n"
        "def test_no_network():\n"
        "    assert True\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-rf", str(tmp_path)],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )

    assert result.returncode == 1, result.stdout[-3000:]
    assert "2 failed, 1 passed" in result.stdout, result.stdout[-3000:]
    assert "FAILED test_inner.py::test_swallowed_socket_connect" in result.stdout
    assert "FAILED test_inner.py::test_swallowed_http_request" in result.stdout
    assert "192.0.2.1:443" in result.stdout
    assert "192.0.2.1:80" in result.stdout


# =====================================================================
# LOCAL TARGETS STAY ALLOWED
# =====================================================================

def _loopback_round_trip(family: int, host: str) -> bytes:
    with socket.socket(family, socket.SOCK_STREAM) as server:
        server.bind((host, 0))
        server.listen(1)
        port = server.getsockname()[1]
        with socket.socket(family, socket.SOCK_STREAM) as client:
            client.settimeout(5)
            client.connect((host, port))
            conn, _ = server.accept()
            with conn:
                client.sendall(b"ping")
                return conn.recv(4)


def test_loopback_ipv4_and_name_lookup_allowed(request):
    _assert_guard_active()

    assert _loopback_round_trip(socket.AF_INET, "127.0.0.1") == b"ping"
    assert socket.getaddrinfo("127.0.0.1", 80)
    assert socket.getaddrinfo("localhost", 80)
    assert _take_violations(request) == []


@pytest.mark.skipif(not socket.has_ipv6, reason="IPv6 is not available on this platform")
def test_loopback_ipv6_allowed(request):
    _assert_guard_active()

    assert _loopback_round_trip(socket.AF_INET6, "::1") == b"ping"
    assert _take_violations(request) == []


@pytest.mark.skipif(not hasattr(socket, "AF_UNIX"), reason="AF_UNIX is not available on this platform")
def test_unix_socket_allowed(request, tmp_path):
    _assert_guard_active()
    path = str(tmp_path / "s")

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(path)
        server.listen(1)
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.connect(path)
            conn, _ = server.accept()
            with conn:
                client.sendall(b"ping")
                assert conn.recv(4) == b"ping"
    assert _take_violations(request) == []


def test_socketpair_and_asyncio_loopback_allowed(request):
    """asyncio's self-pipe uses a loopback socketpair on Windows; it must keep working."""
    _assert_guard_active()

    left, right = socket.socketpair()
    with left, right:
        left.sendall(b"ping")
        assert right.recv(4) == b"ping"

    async def echo_round_trip() -> bytes:
        async def handle(reader, writer):
            writer.write(await reader.read(4))
            await writer.drain()
            writer.close()

        server = await asyncio.start_server(handle, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        async with server:
            reader, writer = await asyncio.open_connection("127.0.0.1", port)
            writer.write(b"ping")
            await writer.drain()
            data = await reader.read(4)
            writer.close()
            await writer.wait_closed()
            return data

    assert asyncio.run(echo_round_trip()) == b"ping"
    assert _take_violations(request) == []
