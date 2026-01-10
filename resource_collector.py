"""
Phase 1: Resource Data Collection Module.

This module provides functionality for collecting real-time system resource metrics
including CPU usage, memory usage, disk I/O, and network activity. Metrics are
collected periodically and stored in memory with timestamps. Optional database
storage is supported for persistent historical tracking.

Classes:
    ResourceMetrics: Data class representing a single resource metrics snapshot.
    ResourceCollector: Main class for collecting and managing resource metrics.

Example:
    >>> collector = ResourceCollector(collection_interval=1.0)
    >>> collector.start_collection()
    >>> # Wait for metrics to be collected
    >>> latest = collector.get_latest_metrics()
    >>> collector.stop_collection()
"""

import time
import threading
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import psutil


@dataclass
class ResourceMetrics:
    """Data class representing a snapshot of system resource metrics.
    
    Attributes:
        timestamp (datetime): When the metrics were collected.
        cpu_percent (float): CPU usage percentage (0-100).
        memory_percent (float): Memory usage percentage (0-100).
        memory_used_mb (float): Memory used in megabytes.
        memory_total_mb (float): Total memory available in megabytes.
        disk_percent (float): Disk I/O activity percentage (0-100).
        disk_used_gb (float): Disk space used in gigabytes.
        disk_total_gb (float): Total disk space in gigabytes.
        network_sent_mb (float): Total network data sent in megabytes.
        network_recv_mb (float): Total network data received in megabytes.
        network_sent_rate_mbps (float): Current network send rate in Mbps.
        network_recv_rate_mbps (float): Current network receive rate in Mbps.
    """
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
    """Collects system resource metrics periodically and manages storage.
    
    This class provides thread-safe collection of system resource metrics including
    CPU, memory, disk, and network usage. Metrics are collected at regular intervals
    in a background thread and stored in memory. Optional automatic database storage
    is supported with batch operations for efficiency.
    
    Attributes:
        collection_interval (float): Time in seconds between metric collections.
        metrics_history (List[ResourceMetrics]): In-memory storage of collected metrics.
        is_collecting (bool): Flag indicating if collection is active.
    
    Example:
        >>> collector = ResourceCollector(collection_interval=1.0, enable_database_storage=True)
        >>> collector.start_collection()
        >>> # Metrics are collected automatically in background
        >>> latest = collector.get_latest_metrics()
        >>> collector.stop_collection()
    """
    
    def __init__(
        self,
        collection_interval: float = 1.0,
        enable_database_storage: bool = False,
        db_path: str = "resource_monitor.db"
    ) -> None:
        """Initialize the resource collector.
        
        Args:
            collection_interval: Time in seconds between each metric collection.
                Default is 1.0 second.
            enable_database_storage: If True, automatically saves metrics to database
                using batch operations. Default is False.
            db_path: Path to SQLite database file. Only used if enable_database_storage
                is True. Default is "resource_monitor.db".
        
        Note:
            Database storage uses batch operations (saves every 10 metrics) to avoid
            blocking the collection thread.
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
        
        # Disk I/O counters for rate calculation
        self.last_disk_read = 0.0
        self.last_disk_write = 0.0
        self.last_disk_time = time.time()
        
        # Database storage (optional)
        self.enable_database_storage = enable_database_storage
        self.db_storage = None
        if enable_database_storage:
            from data_storage import ResourceDataStorage
            self.db_storage = ResourceDataStorage(db_path)
            # Batch save settings - save to DB every N metrics to avoid blocking
            self.db_batch_size = 10
            self.db_batch_buffer: List[ResourceMetrics] = []
    
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage.
        
        Returns:
            float: CPU usage percentage (0-100). The measurement uses a 0.1 second
                interval to balance accuracy and performance.
        """
        return psutil.cpu_percent(interval=0.1)
    
    def _get_memory_usage(self) -> tuple[float, float, float]:
        """Get current memory usage statistics.
        
        Returns:
            tuple[float, float, float]: A tuple containing:
                - percentage: Memory usage percentage (0-100)
                - used_mb: Memory used in megabytes
                - total_mb: Total memory available in megabytes
        """
        memory = psutil.virtual_memory()
        return (
            memory.percent,
            memory.used / (1024 * 1024),  # Convert to MB
            memory.total / (1024 * 1024)  # Convert to MB
        )
    
    def _get_disk_usage(self) -> tuple[float, float, float]:
        """
        Get current disk usage - I/O activity percentage (like Task Manager).
        Returns: (percentage, used_gb, total_gb)
        Note: percentage is I/O activity, not space usage
        """
        import os
        import platform
        
        # Get disk I/O counters
        try:
            disk_io = psutil.disk_io_counters()
            if disk_io is None:
                # Fallback to space usage if I/O counters not available
                return self._get_disk_space_usage()
            
            current_time = time.time()
            time_diff = current_time - self.last_disk_time
            
            if time_diff > 0:
                # Calculate I/O rates in MB/s
                read_rate = (disk_io.read_bytes - self.last_disk_read) / (1024 * 1024) / time_diff
                write_rate = (disk_io.write_bytes - self.last_disk_write) / (1024 * 1024) / time_diff
                
                # Total I/O rate
                total_io_rate = read_rate + write_rate
                
                # Normalize to percentage (assuming max 100 MB/s = 100%)
                # This is a reasonable assumption for most modern drives
                # You can adjust this value based on your drive's capabilities
                max_io_rate = 100.0  # MB/s
                io_percent = min(100.0, (total_io_rate / max_io_rate) * 100.0)
                
                # Update last values
                self.last_disk_read = disk_io.read_bytes
                self.last_disk_write = disk_io.write_bytes
                self.last_disk_time = current_time
            else:
                io_percent = 0.0
                # Initialize counters on first call
                self.last_disk_read = disk_io.read_bytes
                self.last_disk_write = disk_io.write_bytes
                self.last_disk_time = current_time
            
            # Also get disk space for display purposes
            space_used_gb, space_total_gb = self._get_disk_space_info()
            
            return (io_percent, space_used_gb, space_total_gb)
            
        except (AttributeError, OSError):
            # Fallback to space usage if I/O counters fail
            return self._get_disk_space_usage()
    
    def _get_disk_space_info(self) -> tuple[float, float]:
        """Get disk space information (used and total in GB)."""
        import os
        import platform
        
        # Get the correct disk path based on OS
        if platform.system() == 'Windows':
            partitions = psutil.disk_partitions()
            main_disk = None
            max_size = 0
            
            for partition in partitions:
                try:
                    if 'cdrom' in partition.opts or 'network' in partition.opts:
                        continue
                    usage = psutil.disk_usage(partition.mountpoint)
                    if usage.total > max_size:
                        max_size = usage.total
                        main_disk = partition.mountpoint
                except (PermissionError, OSError):
                    continue
            
            if main_disk is None:
                main_disk = 'C:\\'
            root_path = main_disk
        else:
            root_path = '/'
        
        disk = psutil.disk_usage(root_path)
        return (
            disk.used / (1024 * 1024 * 1024),  # Convert to GB
            disk.total / (1024 * 1024 * 1024)  # Convert to GB
        )
    
    def _get_disk_space_usage(self) -> tuple[float, float, float]:
        """Fallback method to get disk space usage percentage."""
        used_gb, total_gb = self._get_disk_space_info()
        percent = (used_gb / total_gb * 100) if total_gb > 0 else 0.0
        return (percent, used_gb, total_gb)
    
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
        """Collect all current system resource metrics.
        
        This method gathers metrics for CPU, memory, disk, and network usage,
        calculates rates where applicable, and returns a ResourceMetrics object
        with the current system state.
        
        Returns:
            ResourceMetrics: A dataclass instance containing all collected metrics
                with the current timestamp.
        
        Note:
            Network and disk rates are calculated based on time differences from
            previous measurements.
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
    
    def _collection_loop(self) -> None:
        """Internal method that runs in a separate thread to collect metrics periodically.
        
        This method runs continuously while is_collecting is True, collecting metrics
        at the specified interval. It handles batch database saves automatically if
        database storage is enabled. The loop sleeps for collection_interval seconds
        between collections.
        
        Note:
            This is an internal method and should not be called directly. Use
            start_collection() to begin metric collection.
        """
        while self.is_collecting:
            metrics = self.collect_metrics()
            
            with self.lock:
                self.metrics_history.append(metrics)
                
                # Save to database if enabled (batch mode for efficiency)
                if self.enable_database_storage and self.db_storage:
                    self.db_batch_buffer.append(metrics)
                    if len(self.db_batch_buffer) >= self.db_batch_size:
                        # Save batch without blocking collection
                        batch_to_save = self.db_batch_buffer.copy()
                        self.db_batch_buffer.clear()
                        # Save in background to avoid blocking
                        threading.Thread(
                            target=self.db_storage.save_metrics_batch,
                            args=(batch_to_save,),
                            daemon=True
                        ).start()
            
            time.sleep(self.collection_interval)
    
    def start_collection(self) -> None:
        """Start collecting metrics in a background thread.
        
        Creates and starts a daemon thread that periodically collects metrics
        according to the collection_interval. If collection is already active,
        this method does nothing.
        
        Note:
            The collection thread is a daemon thread, so it will automatically
            terminate when the main program exits.
        """
        if self.is_collecting:
            return
        
        self.is_collecting = True
        self.collection_thread = threading.Thread(target=self._collection_loop, daemon=True)
        self.collection_thread.start()
    
    def stop_collection(self) -> None:
        """Stop collecting metrics and save any pending data.
        
        Stops the background collection thread and waits for it to finish
        (with a 2 second timeout). If database storage is enabled, any remaining
        buffered metrics are saved before stopping.
        """
        self.is_collecting = False
        if self.collection_thread:
            self.collection_thread.join(timeout=2.0)
        
        # Save any remaining buffered metrics to database
        if self.enable_database_storage and self.db_storage and self.db_batch_buffer:
            self.db_storage.save_metrics_batch(self.db_batch_buffer)
            self.db_batch_buffer.clear()
    
    def save_current_history_to_database(self, db_path: str = "resource_monitor.db") -> int:
        """Save current in-memory history to database.
        
        Useful for one-time saves when database storage wasn't enabled during
        initialization, or for saving accumulated metrics before clearing history.
        
        Args:
            db_path: Path to the SQLite database file. If the file doesn't exist,
                it will be created. Default is "resource_monitor.db".
        
        Returns:
            int: Number of records successfully saved to the database. Returns 0
                if no metrics are in memory or if an error occurs.
        
        Note:
            This method uses batch insert for efficiency. All metrics in the
            current history are saved in a single transaction.
        
        Example:
            >>> collector = ResourceCollector()
            >>> collector.start_collection()
            >>> # ... collect some metrics ...
            >>> collector.stop_collection()
            >>> saved = collector.save_current_history_to_database("backup.db")
        """
        from data_storage import ResourceDataStorage
        storage = ResourceDataStorage(db_path)
        
        with self.lock:
            metrics_to_save = self.metrics_history.copy()
        
        if metrics_to_save:
            return storage.save_metrics_batch(metrics_to_save)
        return 0
    
    def get_latest_metrics(self) -> Optional[ResourceMetrics]:
        """Get the most recent collected metrics.
        
        Returns:
            Optional[ResourceMetrics]: The most recent metrics snapshot, or None
                if no metrics have been collected yet.
        
        Note:
            This method is thread-safe and returns a reference to the actual
            metrics object. If you need to modify it, make a copy first.
        """
        with self.lock:
            if self.metrics_history:
                return self.metrics_history[-1]
            return None
    
    def get_metrics_history(self) -> List[ResourceMetrics]:
        """Get a copy of all collected metrics history.
        
        Returns:
            List[ResourceMetrics]: A list containing all collected metrics in
                chronological order (oldest first). The returned list is a copy,
                so modifications to it won't affect the internal history.
        """
        with self.lock:
            return self.metrics_history.copy()
    
    def clear_history(self) -> None:
        """Clear all stored metrics history from memory.
        
        This removes all metrics from the in-memory history but does not affect
        any metrics that have been saved to the database (if database storage
        is enabled).
        """
        with self.lock:
            self.metrics_history.clear()
    
    def get_history_count(self) -> int:
        """Get the number of metrics currently stored in memory.
        
        Returns:
            int: The number of metrics in the in-memory history. Note that this
                does not include metrics that have been saved to the database
                (if database storage is enabled).
        """
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

