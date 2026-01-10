"""
Phase 3: Data Storage and Historical Logging.

This module provides persistent storage for resource metrics using SQLite database.
It supports thread-safe operations, batch inserts for efficiency, and flexible
querying capabilities for historical data retrieval.

Classes:
    ResourceDataStorage: Main class for database operations and data persistence.

Example:
    >>> storage = ResourceDataStorage("monitor.db")
    >>> metrics = ResourceMetrics(...)
    >>> storage.save_metrics(metrics)
    >>> all_metrics = storage.get_metrics_by_time_range(start_time, end_time)
"""

import sqlite3
import threading
from datetime import datetime
from typing import List, Optional, Tuple
from contextlib import contextmanager
from resource_collector import ResourceMetrics


class ResourceDataStorage:
    """Handles persistent storage of resource metrics in SQLite database.
    
    This class provides thread-safe database operations for storing and retrieving
    resource metrics. It uses SQLite for lightweight, file-based storage with
    automatic schema creation and indexing for optimal query performance.
    
    Attributes:
        db_path (str): Path to the SQLite database file.
        lock (threading.Lock): Thread lock for ensuring thread-safe operations.
    
    Example:
        >>> storage = ResourceDataStorage("metrics.db")
        >>> metrics = ResourceMetrics(...)
        >>> storage.save_metrics(metrics)
        >>> # Or batch save for efficiency
        >>> storage.save_metrics_batch([metrics1, metrics2, ...])
        >>> # Query data
        >>> results = storage.get_metrics_by_time_range(start, end)
    """
    
    def __init__(self, db_path: str = "resource_monitor.db") -> None:
        """Initialize the database storage.
        
        Creates or connects to an SQLite database file and initializes the schema
        if it doesn't already exist. An index on the timestamp column is created
        automatically for faster time-range queries.
        
        Args:
            db_path: Path to the SQLite database file. If the file doesn't exist,
                it will be created. Default is "resource_monitor.db".
        
        Raises:
            sqlite3.Error: If database initialization fails.
        """
        self.db_path = db_path
        self.lock = threading.Lock()
        self._initialize_database()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for thread-safe database connections.
        
        Yields a database connection with automatic transaction management.
        Commits on successful completion, rolls back on exception, and always
        closes the connection.
        
        Yields:
            sqlite3.Connection: A database connection with Row factory enabled.
        
        Raises:
            sqlite3.Error: If connection or transaction operations fail.
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
    
    def _initialize_database(self) -> None:
        """Create the database schema and indexes if they don't exist.
        
        Creates the resource_metrics table with all required columns and an
        index on the timestamp column for optimized time-range queries.
        
        Raises:
            sqlite3.Error: If schema creation fails.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS resource_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    cpu_percent REAL NOT NULL,
                    memory_percent REAL NOT NULL,
                    memory_used_mb REAL NOT NULL,
                    memory_total_mb REAL NOT NULL,
                    disk_percent REAL NOT NULL,
                    disk_used_gb REAL NOT NULL,
                    disk_total_gb REAL NOT NULL,
                    network_sent_mb REAL NOT NULL,
                    network_recv_mb REAL NOT NULL,
                    network_sent_rate_mbps REAL NOT NULL,
                    network_recv_rate_mbps REAL NOT NULL
                )
            """)
            
            # Create index on timestamp for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON resource_metrics(timestamp)
            """)
            
            conn.commit()
    
    def save_metrics(self, metrics: ResourceMetrics) -> bool:
        """Save a single metrics record to the database.
        
        Inserts a single ResourceMetrics object into the database. This method
        is thread-safe and uses a transaction for atomicity.
        
        Args:
            metrics: ResourceMetrics object containing the metrics data to save.
        
        Returns:
            bool: True if the save operation was successful, False otherwise.
        
        Note:
            For saving multiple metrics, use save_metrics_batch() which is more
            efficient as it uses a single transaction for all records.
        
        Example:
            >>> metrics = ResourceMetrics(timestamp=datetime.now(), ...)
            >>> success = storage.save_metrics(metrics)
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO resource_metrics (
                        timestamp, cpu_percent, memory_percent,
                        memory_used_mb, memory_total_mb,
                        disk_percent, disk_used_gb, disk_total_gb,
                        network_sent_mb, network_recv_mb,
                        network_sent_rate_mbps, network_recv_rate_mbps
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metrics.timestamp.isoformat(),
                    metrics.cpu_percent,
                    metrics.memory_percent,
                    metrics.memory_used_mb,
                    metrics.memory_total_mb,
                    metrics.disk_percent,
                    metrics.disk_used_gb,
                    metrics.disk_total_gb,
                    metrics.network_sent_mb,
                    metrics.network_recv_mb,
                    metrics.network_sent_rate_mbps,
                    metrics.network_recv_rate_mbps
                ))
            return True
        except Exception as e:
            print(f"Error saving metrics: {e}")
            return False
    
    def save_metrics_batch(self, metrics_list: List[ResourceMetrics]) -> int:
        """Save multiple metrics records in a single transaction.
        
        This method is more efficient than saving records individually as it uses
        a single database transaction for all records. All records are saved
        atomically - either all succeed or all fail.
        
        Args:
            metrics_list: List of ResourceMetrics objects to save. If empty,
                the method returns 0 without performing any database operations.
        
        Returns:
            int: Number of records successfully saved. If an error occurs,
                returns 0 (no records saved due to transaction rollback).
        
        Note:
            This method is preferred for bulk operations as it's significantly
            faster than calling save_metrics() multiple times.
        
        Example:
            >>> metrics_list = [metrics1, metrics2, metrics3]
            >>> saved_count = storage.save_metrics_batch(metrics_list)
        """
        if not metrics_list:
            return 0
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                data = [
                    (
                        m.timestamp.isoformat(),
                        m.cpu_percent,
                        m.memory_percent,
                        m.memory_used_mb,
                        m.memory_total_mb,
                        m.disk_percent,
                        m.disk_used_gb,
                        m.disk_total_gb,
                        m.network_sent_mb,
                        m.network_recv_mb,
                        m.network_sent_rate_mbps,
                        m.network_recv_rate_mbps
                    )
                    for m in metrics_list
                ]
                cursor.executemany("""
                    INSERT INTO resource_metrics (
                        timestamp, cpu_percent, memory_percent,
                        memory_used_mb, memory_total_mb,
                        disk_percent, disk_used_gb, disk_total_gb,
                        network_sent_mb, network_recv_mb,
                        network_sent_rate_mbps, network_recv_rate_mbps
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, data)
            return len(metrics_list)
        except Exception as e:
            print(f"Error saving metrics batch: {e}")
            return 0
    
    def get_metrics_by_time_range(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[ResourceMetrics]:
        """Retrieve metrics within a specified time range.
        
        Queries the database for metrics records falling within the specified
        time range. The results are returned in chronological order (oldest first).
        
        Args:
            start_time: Start of the time range (inclusive). If None, no lower
                limit is applied (retrieve from beginning of database).
            end_time: End of the time range (inclusive). If None, no upper limit
                is applied (retrieve until end of database).
            limit: Maximum number of records to return. If None, all matching
                records are returned. Useful for limiting large result sets.
        
        Returns:
            List[ResourceMetrics]: List of metrics objects matching the criteria,
                ordered chronologically (oldest first). Returns empty list if no
                records match or if an error occurs.
        
        Example:
            >>> from datetime import datetime, timedelta
            >>> end = datetime.now()
            >>> start = end - timedelta(hours=24)
            >>> metrics = storage.get_metrics_by_time_range(start, end)
            >>> # Get only first 100 records
            >>> recent = storage.get_metrics_by_time_range(start, end, limit=100)
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM resource_metrics WHERE 1=1"
                params = []
                
                if start_time:
                    query += " AND timestamp >= ?"
                    params.append(start_time.isoformat())
                
                if end_time:
                    query += " AND timestamp <= ?"
                    params.append(end_time.isoformat())
                
                query += " ORDER BY timestamp ASC"
                
                if limit:
                    query += " LIMIT ?"
                    params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                return [self._row_to_metrics(row) for row in rows]
        except Exception as e:
            print(f"Error retrieving metrics: {e}")
            return []
    
    def get_latest_metrics(self, count: int = 1) -> List[ResourceMetrics]:
        """Get the most recent metrics records from the database.
        
        Retrieves the N most recent records ordered chronologically (oldest first
        in the returned list, even though they're the most recent in the database).
        
        Args:
            count: Number of recent records to retrieve. Default is 1. Must be
                a positive integer.
        
        Returns:
            List[ResourceMetrics]: List of metrics objects in chronological order
                (oldest of the selected records first). Returns empty list if no
                records exist or if an error occurs.
        
        Example:
            >>> # Get the single most recent metric
            >>> latest = storage.get_latest_metrics(1)
            >>> # Get the 10 most recent metrics
            >>> recent = storage.get_latest_metrics(10)
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM resource_metrics
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (count,))
                rows = cursor.fetchall()
                
                # Reverse to get chronological order
                return [self._row_to_metrics(row) for row in reversed(rows)]
        except Exception as e:
            print(f"Error retrieving latest metrics: {e}")
            return []
    
    def get_all_metrics(self) -> List[ResourceMetrics]:
        """Get all stored metrics."""
        return self.get_metrics_by_time_range()
    
    def get_metrics_count(self) -> int:
        """Get the total number of stored metrics."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM resource_metrics")
                return cursor.fetchone()[0]
        except Exception as e:
            print(f"Error counting metrics: {e}")
            return 0
    
    def get_oldest_timestamp(self) -> Optional[datetime]:
        """Get the timestamp of the oldest stored metric.
        
        Returns:
            Optional[datetime]: The timestamp of the oldest metric record in the
                database, or None if no records exist or if an error occurs.
        
        Example:
            >>> oldest = storage.get_oldest_timestamp()
            >>> if oldest:
            ...     print(f"Oldest record: {oldest}")
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT MIN(timestamp) FROM resource_metrics")
                result = cursor.fetchone()[0]
                if result:
                    return datetime.fromisoformat(result)
                return None
        except Exception as e:
            print(f"Error getting oldest timestamp: {e}")
            return None
    
    def get_newest_timestamp(self) -> Optional[datetime]:
        """Get the timestamp of the newest stored metric.
        
        Returns:
            Optional[datetime]: The timestamp of the newest metric record in the
                database, or None if no records exist or if an error occurs.
        
        Example:
            >>> newest = storage.get_newest_timestamp()
            >>> if newest:
            ...     print(f"Newest record: {newest}")
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT MAX(timestamp) FROM resource_metrics")
                result = cursor.fetchone()[0]
                if result:
                    return datetime.fromisoformat(result)
                return None
        except Exception as e:
            print(f"Error getting newest timestamp: {e}")
            return None
    
    def delete_old_metrics(self, before_date: datetime) -> int:
        """Delete metrics older than the specified date.
        
        Removes all metric records with timestamps before the specified date.
        This is useful for managing database size by removing old data. After
        deletion, the database is vacuumed to reclaim disk space.
        
        Args:
            before_date: Delete all metrics with timestamps strictly before
                this date/time.
        
        Returns:
            int: Number of records deleted. Returns 0 if no records match or
                if an error occurs.
        
        Warning:
            This operation permanently deletes data and cannot be undone.
            Consider backing up important data before deletion.
        
        Example:
            >>> from datetime import datetime, timedelta
            >>> cutoff = datetime.now() - timedelta(days=30)
            >>> deleted = storage.delete_old_metrics(cutoff)
            >>> print(f"Deleted {deleted} old records")
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM resource_metrics WHERE timestamp < ?",
                    (before_date.isoformat(),)
                )
                deleted_count = cursor.rowcount
                # Vacuum database to reclaim space
                cursor.execute("VACUUM")
                return deleted_count
        except Exception as e:
            print(f"Error deleting old metrics: {e}")
            return 0
    
    def delete_all_metrics(self) -> int:
        """Delete all stored metrics from the database.
        
        Removes all metric records from the database and vacuums the database
        to reclaim disk space. This effectively resets the database to an
        empty state while preserving the schema.
        
        Returns:
            int: Number of records deleted. Returns 0 if database was already
                empty or if an error occurs.
        
        Warning:
            This operation permanently deletes ALL data and cannot be undone.
            Use with extreme caution!
        
        Example:
            >>> # Backup data first!
            >>> deleted = storage.delete_all_metrics()
            >>> print(f"Deleted {deleted} records")
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM resource_metrics")
                deleted_count = cursor.rowcount
                cursor.execute("VACUUM")
                return deleted_count
        except Exception as e:
            print(f"Error deleting all metrics: {e}")
            return 0
    
    def _row_to_metrics(self, row: sqlite3.Row) -> ResourceMetrics:
        """Convert a database row to a ResourceMetrics object."""
        return ResourceMetrics(
            timestamp=datetime.fromisoformat(row['timestamp']),
            cpu_percent=row['cpu_percent'],
            memory_percent=row['memory_percent'],
            memory_used_mb=row['memory_used_mb'],
            memory_total_mb=row['memory_total_mb'],
            disk_percent=row['disk_percent'],
            disk_used_gb=row['disk_used_gb'],
            disk_total_gb=row['disk_total_gb'],
            network_sent_mb=row['network_sent_mb'],
            network_recv_mb=row['network_recv_mb'],
            network_sent_rate_mbps=row['network_sent_rate_mbps'],
            network_recv_rate_mbps=row['network_recv_rate_mbps']
        )
    
    def get_statistics(self) -> dict:
        """Get statistics about the stored data in the database.
        
        Retrieves summary statistics including total record count, time range
        of stored data, and approximate database size.
        
        Returns:
            dict: A dictionary containing:
                - 'total_records' (int): Total number of metric records stored.
                - 'oldest_timestamp' (datetime, optional): Timestamp of the oldest
                  record, or None if no records exist.
                - 'newest_timestamp' (datetime, optional): Timestamp of the newest
                  record, or None if no records exist.
                - 'database_size_mb' (float): Approximate database file size in MB.
            
            Returns an empty dictionary if an error occurs.
        
        Example:
            >>> stats = storage.get_statistics()
            >>> print(f"Total records: {stats['total_records']}")
            >>> if stats['oldest_timestamp']:
            ...     print(f"Oldest: {stats['oldest_timestamp']}")
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Total count
                cursor.execute("SELECT COUNT(*) FROM resource_metrics")
                stats['total_records'] = cursor.fetchone()[0]
                
                # Time range
                cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM resource_metrics")
                result = cursor.fetchone()
                if result[0] and result[1]:
                    stats['oldest_timestamp'] = datetime.fromisoformat(result[0])
                    stats['newest_timestamp'] = datetime.fromisoformat(result[1])
                else:
                    stats['oldest_timestamp'] = None
                    stats['newest_timestamp'] = None
                
                # Database size (approximate)
                cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
                result = cursor.fetchone()
                stats['database_size_mb'] = result[0] / (1024 * 1024) if result else 0
                
                return stats
        except Exception as e:
            print(f"Error getting statistics: {e}")
            return {}


if __name__ == "__main__":
    # Test the data storage
    print("Phase 3: Data Storage - Test")
    print("=" * 50)
    
    from resource_collector import ResourceCollector
    import time
    
    storage = ResourceDataStorage("test_monitor.db")
    
    # Create a collector and collect some metrics
    collector = ResourceCollector(collection_interval=0.5)
    collector.start_collection()
    
    print("Collecting metrics for 5 seconds...")
    time.sleep(5)
    collector.stop_collection()
    
    # Save metrics to database
    metrics_history = collector.get_metrics_history()
    print(f"\nSaving {len(metrics_history)} metrics to database...")
    saved = storage.save_metrics_batch(metrics_history)
    print(f"Saved {saved} metrics")
    
    # Retrieve and display statistics
    stats = storage.get_statistics()
    print(f"\nDatabase Statistics:")
    print(f"  Total records: {stats.get('total_records', 0)}")
    if stats.get('oldest_timestamp'):
        print(f"  Oldest: {stats['oldest_timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
    if stats.get('newest_timestamp'):
        print(f"  Newest: {stats['newest_timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Database size: {stats.get('database_size_mb', 0):.2f} MB")
    
    # Test retrieval
    print(f"\nRetrieving latest 5 metrics:")
    latest = storage.get_latest_metrics(5)
    for m in latest:
        print(f"  {m.timestamp.strftime('%H:%M:%S')} - CPU: {m.cpu_percent:.1f}%, Memory: {m.memory_percent:.1f}%")
    
    print("\nPhase 3 test complete!")

