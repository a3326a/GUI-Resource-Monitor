"""
Phase 1: Resource Data Collection Module
Collects real-time system resource metrics (CPU, memory, disk, network)
and stores them with timestamps in memory.
"""

import time
import threading
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import psutil


@dataclass
class ResourceMetrics:
    """Data class to store resource metrics at a specific timestamp."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    network_sent_mb: float
    network_recv_mb: float
    network_sent_rate_mbps: float
    network_recv_rate_mbps: float


class ResourceCollector:
    """
    Collects system resource metrics periodically and stores them in memory.
    """
    
    def __init__(self, collection_interval: float = 1.0):
        """
        Initialize the resource collector.
        
        Args:
            collection_interval: Time in seconds between each collection (default: 1.0)
        """
        self.collection_interval = collection_interval
        self.metrics_history: List[ResourceMetrics] = []
        self.is_collecting = False
        self.collection_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        
        # Network counters for rate calculation
        self.last_network_sent = 0.0
        self.last_network_recv = 0.0
        self.last_network_time = time.time()
    
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        return psutil.cpu_percent(interval=0.1)
    
    def _get_memory_usage(self) -> tuple[float, float, float]:
        """
        Get current memory usage.
        Returns: (percentage, used_mb, total_mb)
        """
        memory = psutil.virtual_memory()
        return (
            memory.percent,
            memory.used / (1024 * 1024),  # Convert to MB
            memory.total / (1024 * 1024)  # Convert to MB
        )
    
    def _get_disk_usage(self) -> tuple[float, float, float]:
        """
        Get current disk usage for the main partition.
        Returns: (percentage, used_gb, total_gb)
        """
        import os
        # Get the root directory (works on both Windows and Unix)
        root_path = os.path.abspath(os.sep)
        disk = psutil.disk_usage(root_path)
        return (
            disk.percent,
            disk.used / (1024 * 1024 * 1024),  # Convert to GB
            disk.total / (1024 * 1024 * 1024)  # Convert to GB
        )
    
    def _get_network_usage(self) -> tuple[float, float, float, float]:
        """
        Get current network usage.
        Returns: (sent_mb, recv_mb, sent_rate_mbps, recv_rate_mbps)
        """
        net_io = psutil.net_io_counters()
        current_time = time.time()
        
        # Convert bytes to MB
        sent_mb = net_io.bytes_sent / (1024 * 1024)
        recv_mb = net_io.bytes_recv / (1024 * 1024)
        
        # Calculate rates
        time_diff = current_time - self.last_network_time
        if time_diff > 0:
            sent_rate = (sent_mb - self.last_network_sent) / time_diff * 8  # Convert to Mbps
            recv_rate = (recv_mb - self.last_network_recv) / time_diff * 8  # Convert to Mbps
        else:
            sent_rate = 0.0
            recv_rate = 0.0
        
        # Update last values
        self.last_network_sent = sent_mb
        self.last_network_recv = recv_mb
        self.last_network_time = current_time
        
        return sent_mb, recv_mb, sent_rate, recv_rate
    
    def collect_metrics(self) -> ResourceMetrics:
        """
        Collect all current system resource metrics.
        
        Returns:
            ResourceMetrics object with current system state
        """
        timestamp = datetime.now()
        cpu_percent = self._get_cpu_usage()
        memory_percent, memory_used_mb, memory_total_mb = self._get_memory_usage()
        disk_percent, disk_used_gb, disk_total_gb = self._get_disk_usage()
        network_sent_mb, network_recv_mb, network_sent_rate, network_recv_rate = self._get_network_usage()
        
        return ResourceMetrics(
            timestamp=timestamp,
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used_mb=memory_used_mb,
            memory_total_mb=memory_total_mb,
            disk_percent=disk_percent,
            disk_used_gb=disk_used_gb,
            disk_total_gb=disk_total_gb,
            network_sent_mb=network_sent_mb,
            network_recv_mb=network_recv_mb,
            network_sent_rate_mbps=network_sent_rate,
            network_recv_rate_mbps=network_recv_rate
        )
    
    def _collection_loop(self):
        """Internal method that runs in a separate thread to collect metrics periodically."""
        while self.is_collecting:
            metrics = self.collect_metrics()
            
            with self.lock:
                self.metrics_history.append(metrics)
            
            time.sleep(self.collection_interval)
    
    def start_collection(self):
        """Start collecting metrics in a background thread."""
        if self.is_collecting:
            return
        
        self.is_collecting = True
        self.collection_thread = threading.Thread(target=self._collection_loop, daemon=True)
        self.collection_thread.start()
    
    def stop_collection(self):
        """Stop collecting metrics."""
        self.is_collecting = False
        if self.collection_thread:
            self.collection_thread.join(timeout=2.0)
    
    def get_latest_metrics(self) -> Optional[ResourceMetrics]:
        """Get the most recent collected metrics."""
        with self.lock:
            if self.metrics_history:
                return self.metrics_history[-1]
            return None
    
    def get_metrics_history(self) -> List[ResourceMetrics]:
        """Get all collected metrics history."""
        with self.lock:
            return self.metrics_history.copy()
    
    def clear_history(self):
        """Clear all stored metrics history."""
        with self.lock:
            self.metrics_history.clear()
    
    def get_history_count(self) -> int:
        """Get the number of collected metrics."""
        with self.lock:
            return len(self.metrics_history)


if __name__ == "__main__":
    # Test the resource collector
    print("Phase 1: Resource Data Collection - Test")
    print("=" * 50)
    
    collector = ResourceCollector(collection_interval=1.0)
    
    print("Starting collection for 10 seconds...")
    collector.start_collection()
    
    try:
        for i in range(10):
            time.sleep(1)
            latest = collector.get_latest_metrics()
            if latest:
                print(f"\n[{latest.timestamp.strftime('%H:%M:%S')}] "
                      f"CPU: {latest.cpu_percent:.1f}% | "
                      f"Memory: {latest.memory_percent:.1f}% | "
                      f"Disk: {latest.disk_percent:.1f}% | "
                      f"Network: ↑{latest.network_sent_rate_mbps:.2f} ↓{latest.network_recv_rate_mbps:.2f} Mbps")
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        collector.stop_collection()
        print(f"\nCollection stopped. Total metrics collected: {collector.get_history_count()}")

