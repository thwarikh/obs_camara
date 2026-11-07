"""
System monitor service for collecting host CPU, RAM, and network throughput metrics.
"""
import psutil
import time
from typing import Dict, Any

class SystemMonitor:
    def __init__(self):
        self._last_net = psutil.net_io_counters()
        self._last_time = time.time()

    def get_metrics(self) -> Dict[str, Any]:
        current_time = time.time()
        current_net = psutil.net_io_counters()
        time_delta = max(current_time - self._last_time, 0.001)

        bytes_recv = current_net.bytes_recv - self._last_net.bytes_recv
        bytes_sent = current_net.bytes_sent - self._last_net.bytes_sent

        recv_mbps = (bytes_recv * 8) / (time_delta * 1_000_000)
        sent_mbps = (bytes_sent * 8) / (time_delta * 1_000_000)

        self._last_net = current_net
        self._last_time = current_time

        cpu_percent = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()

        return {
            "cpu_percent": round(cpu_percent, 1),
            "memory_percent": round(mem.percent, 1),
            "memory_used_mb": round(mem.used / (1024 * 1024), 1),
            "memory_total_mb": round(mem.total / (1024 * 1024), 1),
            "net_ingress_mbps": round(recv_mbps, 2),
            "net_egress_mbps": round(sent_mbps, 2),
            "timestamp": int(current_time * 1000)
        }

system_monitor = SystemMonitor()

