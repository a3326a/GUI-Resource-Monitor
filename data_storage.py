"""
Phase 3: Data Storage and Historical Logging
Persists resource metrics to a local SQLite database for history tracking.
"""

import sqlite3
import threading
from datetime import datetime
from typing import List, Optional, Tuple
from contextlib import contextmanager
from resource_collector import ResourceMetrics


class ResourceDataStorage:
    """
    Handles persistent storage of resource metrics in SQLite database.
    Thread-safe and optimized for large datasets.
    """
    
    def __init__(self, db_path: str = "resource_monitor.db"):
        """
        Initialize the database storage.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.lock = threading.Lock()
        self._initialize_database()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections with thread safety."""
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
    
    def _initialize_database(self):
        """Create the database schema if it doesn't exist."""
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
        """
        Save a single metrics record to the database.
        
        Args:
            metrics: ResourceMetrics object to save
            
        Returns:
            True if successful, False otherwise
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
        """
        Save multiple metrics records in a single transaction (more efficient).
        
        Args:
            metrics_list: List of ResourceMetrics objects to save
            
        Returns:
            Number of records successfully saved
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
        """
        Retrieve metrics within a time range.
        
        Args:
            start_time: Start of time range (None for no lower limit)
            end_time: End of time range (None for no upper limit)
            limit: Maximum number of records to return (None for all)
            
        Returns:
            List of ResourceMetrics objects
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
        """
        Get the most recent metrics records.
        
        Args:
            count: Number of recent records to retrieve
            
        Returns:
            List of ResourceMetrics objects (most recent first)
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
        """Get the timestamp of the oldest stored metric."""
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
        """Get the timestamp of the newest stored metric."""
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
        """
        Delete metrics older than the specified date.
        Useful for managing database size.
        
        Args:
            before_date: Delete all metrics before this date
            
        Returns:
            Number of records deleted
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
        """
        Delete all stored metrics.
        
        Returns:
            Number of records deleted
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
        """
        Get statistics about stored data.
        
        Returns:
            Dictionary with statistics
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

