import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from runtime_network_check import find_external_attempts  # noqa: E402


class FindExternalAttemptsTest(unittest.TestCase):
    def test_ipv4_connect_is_flagged(self):
        log = '812 connect(5, {sa_family=AF_INET, sin_port=htons(443), sin_addr=inet_addr("104.18.2.3")}, 16) = -1 ENETUNREACH (Network is unreachable)\n'
        self.assertEqual(find_external_attempts(log), ["104.18.2.3:443"])

    def test_ipv6_connect_is_flagged(self):
        log = '812 connect(7, {sa_family=AF_INET6, sin6_port=htons(443), sin6_flowinfo=htonl(0), inet_pton(AF_INET6, "2606:4700::1", &sin6_addr), sin6_scope_id=0}, 28) = -1 ENETUNREACH\n'
        self.assertEqual(find_external_attempts(log), ["[2606:4700::1]:443"])

    def test_udp_dns_sendto_is_flagged(self):
        log = '900 sendto(9, "\\x12\\x34", 32, MSG_NOSIGNAL, {sa_family=AF_INET, sin_port=htons(53), sin_addr=inet_addr("1.1.1.1")}, 16) = -1 ENETUNREACH\n'
        self.assertEqual(find_external_attempts(log), ["1.1.1.1:53"])

    def test_systemd_resolved_socket_is_flagged(self):
        log = '901 connect(4, {sa_family=AF_UNIX, sun_path="/run/systemd/resolve/io.systemd.Resolve"}, 42) = 0\n'
        self.assertEqual(
            find_external_attempts(log), ["dns:/run/systemd/resolve/io.systemd.Resolve"]
        )

    def test_loopback_and_unix_sockets_are_ignored(self):
        log = (
            '1 connect(3, {sa_family=AF_INET, sin_port=htons(8080), sin_addr=inet_addr("127.0.0.1")}, 16) = 0\n'
            '1 connect(3, {sa_family=AF_INET6, sin6_port=htons(80), sin6_flowinfo=htonl(0), inet_pton(AF_INET6, "::1", &sin6_addr), sin6_scope_id=0}, 28) = 0\n'
            '1 connect(3, {sa_family=AF_UNIX, sun_path="/tmp/.X11-unix/X99"}, 20) = 0\n'
            '1 connect(3, {sa_family=AF_UNSPEC, sa_data="\\0\\0"}, 16) = 0\n'
        )
        self.assertEqual(find_external_attempts(log), [])

    def test_duplicates_are_collapsed(self):
        line = '2 connect(5, {sa_family=AF_INET, sin_port=htons(443), sin_addr=inet_addr("9.9.9.9")}, 16) = -1 ENETUNREACH\n'
        self.assertEqual(find_external_attempts(line * 3), ["9.9.9.9:443"])


if __name__ == "__main__":
    unittest.main()
