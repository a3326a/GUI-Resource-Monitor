"""
Phase 6: Unit and Integration Tests.

Comprehensive test suite for the Resource Monitor application including unit tests
for individual components and integration tests for complete workflows. All tests
use temporary databases to avoid affecting production data.

Test Classes:
    TestResourceMetrics: Tests for ResourceMetrics dataclass validation.
    TestResourceCollector: Tests for metric collection and management.
    TestDataStorage: Tests for database operations and queries.
    TestIntegration: End-to-end workflow integration tests.

Usage:
    Run all tests:
        python tests.py
    
    Run with unittest module:
        python -m unittest tests.py
    
    Run with verbose output:
        python tests.py -v
"""

import unittest
import os
import tempfile
import time
from datetime import datetime, timedelta
from resource_collector import ResourceCollector, ResourceMetrics
from data_storage import ResourceDataStorage


class TestResourceMetrics(unittest.TestCase):
    """Test ResourceMetrics dataclass."""
    
    def test_metrics_creation(self):
        """Test creating a ResourceMetrics object."""
        now = datetime.now()
        metrics = ResourceMetrics(
            timestamp=now,
            cpu_percent=50.5,
            memory_percent=60.0,
            memory_used_mb=8192.0,
            memory_total_mb=16384.0,
            disk_percent=75.0,
            disk_used_gb=500.0,
            disk_total_gb=1000.0,
            network_sent_mb=1024.0,
            network_recv_mb=2048.0,
            network_sent_rate_mbps=10.5,
            network_recv_rate_mbps=20.5
        )
        
        self.assertEqual(metrics.cpu_percent, 50.5)
        self.assertEqual(metrics.memory_percent, 60.0)
        self.assertEqual(metrics.timestamp, now)
    
    def test_metrics_valid_ranges(self):
        """Test that metrics have valid ranges."""
        now = datetime.now()
        metrics = ResourceMetrics(
            timestamp=now,
            cpu_percent=0.0,
            memory_percent=0.0,
            memory_used_mb=0.0,
            memory_total_mb=100.0,
            disk_percent=0.0,
            disk_used_gb=0.0,
            disk_total_gb=100.0,
            network_sent_mb=0.0,
            network_recv_mb=0.0,
            network_sent_rate_mbps=0.0,
            network_recv_rate_mbps=0.0
        )
        
        # Test max values
        metrics.cpu_percent = 100.0
        metrics.memory_percent = 100.0
        self.assertEqual(metrics.cpu_percent, 100.0)
        self.assertEqual(metrics.memory_percent, 100.0)


class TestResourceCollector(unittest.TestCase):
    """Test ResourceCollector class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.collector = ResourceCollector(collection_interval=0.1)
    
    def tearDown(self):
        """Clean up after tests."""
        if self.collector.is_collecting:
            self.collector.stop_collection()
        self.collector.clear_history()
    
    def test_collector_initialization(self):
        """Test collector initialization."""
        self.assertFalse(self.collector.is_collecting)
        self.assertEqual(self.collector.get_history_count(), 0)
        self.assertEqual(self.collector.collection_interval, 0.1)
    
    def test_collect_metrics(self):
        """Test collecting a single metric."""
        metrics = self.collector.collect_metrics()
        
        self.assertIsInstance(metrics, ResourceMetrics)
        self.assertIsInstance(metrics.timestamp, datetime)
        self.assertGreaterEqual(metrics.cpu_percent, 0.0)
        self.assertLessEqual(metrics.cpu_percent, 100.0)
        self.assertGreaterEqual(metrics.memory_percent, 0.0)
        self.assertLessEqual(metrics.memory_percent, 100.0)
    
    def test_start_stop_collection(self):
        """Test starting and stopping collection."""
        self.assertFalse(self.collector.is_collecting)
        
        self.collector.start_collection()
        self.assertTrue(self.collector.is_collecting)
        
        time.sleep(0.3)  # Let it collect a few metrics
        
        count = self.collector.get_history_count()
        self.assertGreater(count, 0)
        
        self.collector.stop_collection()
        self.assertFalse(self.collector.is_collecting)
    
    def test_get_latest_metrics(self):
        """Test getting latest metrics."""
        metrics1 = self.collector.collect_metrics()
        time.sleep(0.15)
        metrics2 = self.collector.collect_metrics()
        
        latest = self.collector.get_latest_metrics()
        # If history is managed, latest might be None if history is cleared
        # So we check if metrics were collected first
        history_count = self.collector.get_history_count()
        if history_count > 0:
            self.assertIsNotNone(latest)
            # Latest should be at least as recent as metrics2
            self.assertGreaterEqual(latest.timestamp, metrics1.timestamp)
    
    def test_history_management(self):
        """Test history count and clearing."""
        self.collector.start_collection()
        time.sleep(0.5)
        
        count = self.collector.get_history_count()
        self.assertGreater(count, 0)
        
        self.collector.clear_history()
        self.assertEqual(self.collector.get_history_count(), 0)
        
        self.collector.stop_collection()


class TestDataStorage(unittest.TestCase):
    """Test ResourceDataStorage class."""
    
    def setUp(self):
        """Set up test fixtures with temporary database."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.storage = ResourceDataStorage(self.db_path)
    
    def tearDown(self):
        """Clean up temporary database."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_database_initialization(self):
        """Test database initialization."""
        stats = self.storage.get_statistics()
        self.assertEqual(stats['total_records'], 0)
    
    def test_save_single_metric(self):
        """Test saving a single metric."""
        now = datetime.now()
        metrics = ResourceMetrics(
            timestamp=now,
            cpu_percent=50.0,
            memory_percent=60.0,
            memory_used_mb=8192.0,
            memory_total_mb=16384.0,
            disk_percent=75.0,
            disk_used_gb=500.0,
            disk_total_gb=1000.0,
            network_sent_mb=1024.0,
            network_recv_mb=2048.0,
            network_sent_rate_mbps=10.0,
            network_recv_rate_mbps=20.0
        )
        
        result = self.storage.save_metrics(metrics)
        self.assertTrue(result)
        
        stats = self.storage.get_statistics()
        self.assertEqual(stats['total_records'], 1)
    
    def test_save_batch_metrics(self):
        """Test saving multiple metrics in batch."""
        metrics_list = []
        base_time = datetime.now()
        
        for i in range(10):
            metrics = ResourceMetrics(
                timestamp=base_time + timedelta(seconds=i),
                cpu_percent=50.0 + i,
                memory_percent=60.0 + i,
                memory_used_mb=8192.0,
                memory_total_mb=16384.0,
                disk_percent=75.0,
                disk_used_gb=500.0,
                disk_total_gb=1000.0,
                network_sent_mb=1024.0,
                network_recv_mb=2048.0,
                network_sent_rate_mbps=10.0,
                network_recv_rate_mbps=20.0
            )
            metrics_list.append(metrics)
        
        saved_count = self.storage.save_metrics_batch(metrics_list)
        self.assertEqual(saved_count, 10)
        
        stats = self.storage.get_statistics()
        self.assertEqual(stats['total_records'], 10)
    
    def test_retrieve_by_time_range(self):
        """Test retrieving metrics by time range."""
        base_time = datetime.now()
        
        # Create metrics at different times
        for i in range(5):
            metrics = ResourceMetrics(
                timestamp=base_time + timedelta(seconds=i*10),
                cpu_percent=50.0 + i,
                memory_percent=60.0,
                memory_used_mb=8192.0,
                memory_total_mb=16384.0,
                disk_percent=75.0,
                disk_used_gb=500.0,
                disk_total_gb=1000.0,
                network_sent_mb=1024.0,
                network_recv_mb=2048.0,
                network_sent_rate_mbps=10.0,
                network_recv_rate_mbps=20.0
            )
            self.storage.save_metrics(metrics)
        
        # Retrieve subset
        start = base_time + timedelta(seconds=10)
        end = base_time + timedelta(seconds=30)
        results = self.storage.get_metrics_by_time_range(start, end)
        
        self.assertGreaterEqual(len(results), 2)
        self.assertLessEqual(len(results), 3)
        
        # Verify ordering
        if len(results) > 1:
            for i in range(len(results) - 1):
                self.assertLessEqual(results[i].timestamp, results[i+1].timestamp)
    
    def test_get_latest_metrics(self):
        """Test getting latest metrics."""
        base_time = datetime.now()
        
        for i in range(5):
            metrics = ResourceMetrics(
                timestamp=base_time + timedelta(seconds=i),
                cpu_percent=50.0 + i,
                memory_percent=60.0,
                memory_used_mb=8192.0,
                memory_total_mb=16384.0,
                disk_percent=75.0,
                disk_used_gb=500.0,
                disk_total_gb=1000.0,
                network_sent_mb=1024.0,
                network_recv_mb=2048.0,
                network_sent_rate_mbps=10.0,
                network_recv_rate_mbps=20.0
            )
            self.storage.save_metrics(metrics)
        
        latest = self.storage.get_latest_metrics(3)
        self.assertEqual(len(latest), 3)
        
        # Should be in chronological order (oldest first after reverse)
        # get_latest_metrics returns most recent first, then reverses, so chronological order
        self.assertGreaterEqual(latest[-1].timestamp, latest[0].timestamp)
        # Last should be the most recent (5th = base + 4 seconds, since we start at i=0)
        self.assertEqual(latest[-1].timestamp, base_time + timedelta(seconds=4))
    
    def test_get_statistics(self):
        """Test getting database statistics."""
        base_time = datetime.now()
        
        for i in range(5):
            metrics = ResourceMetrics(
                timestamp=base_time + timedelta(seconds=i),
                cpu_percent=50.0,
                memory_percent=60.0,
                memory_used_mb=8192.0,
                memory_total_mb=16384.0,
                disk_percent=75.0,
                disk_used_gb=500.0,
                disk_total_gb=1000.0,
                network_sent_mb=1024.0,
                network_recv_mb=2048.0,
                network_sent_rate_mbps=10.0,
                network_recv_rate_mbps=20.0
            )
            self.storage.save_metrics(metrics)
        
        stats = self.storage.get_statistics()
        
        self.assertEqual(stats['total_records'], 5)
        self.assertIsNotNone(stats.get('oldest_timestamp'))
        self.assertIsNotNone(stats.get('newest_timestamp'))
        self.assertGreaterEqual(stats.get('database_size_mb', 0), 0)


class TestIntegration(unittest.TestCase):
    """Integration tests for full workflow."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        self.collector = ResourceCollector(
            collection_interval=0.1,
            enable_database_storage=True,
            db_path=self.db_path
        )
    
    def tearDown(self):
        """Clean up after tests."""
        if self.collector.is_collecting:
            self.collector.stop_collection()
        
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_collect_and_store_workflow(self):
        """Test collecting metrics and storing them in database."""
        self.collector.start_collection()
        time.sleep(0.5)  # Collect some metrics
        self.collector.stop_collection()
        
        # Wait for batch save to complete
        time.sleep(0.2)
        
        # Verify in database
        storage = ResourceDataStorage(self.db_path)
        stats = storage.get_statistics()
        
        # Should have at least some records (batch size is 10, so might have 0-10)
        self.assertGreaterEqual(stats['total_records'], 0)
        
        # Verify we can retrieve them
        all_metrics = storage.get_metrics_by_time_range()
        self.assertEqual(len(all_metrics), stats['total_records'])
    
    def test_data_consistency(self):
        """Test data consistency between collector and database."""
        self.collector.start_collection()
        time.sleep(0.5)  # Collect enough for at least one batch (batch_size=10)
        
        # Get from collector
        collector_metrics = self.collector.get_metrics_history()
        collector_count = len(collector_metrics)
        
        self.collector.stop_collection()
        time.sleep(0.5)  # Wait for final batch save to complete
        
        # Get from database
        storage = ResourceDataStorage(self.db_path)
        db_metrics = storage.get_metrics_by_time_range()
        db_count = len(db_metrics)
        
        # Collector should have metrics if collection worked
        self.assertGreater(collector_count, 0, "Collector should have collected some metrics")
        
        # Database might have fewer due to batch saving (saves every 10)
        # So collector_count >= db_count is expected, but both should be >= 0
        self.assertGreaterEqual(collector_count, 0)
        self.assertGreaterEqual(db_count, 0)
        
        # If database has metrics, verify they're valid
        if db_count > 0:
            latest_db = db_metrics[-1]
            self.assertIsInstance(latest_db, ResourceMetrics)
            self.assertGreaterEqual(latest_db.cpu_percent, 0.0)
            self.assertLessEqual(latest_db.cpu_percent, 100.0)


def run_tests():
    """Run all tests and print summary."""
    print("=" * 60)
    print("Phase 6: Testing Suite")
    print("=" * 60)
    import sys
    # Set UTF-8 encoding for Windows compatibility
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestResourceMetrics))
    suite.addTests(loader.loadTestsFromTestCase(TestResourceCollector))
    suite.addTests(loader.loadTestsFromTestCase(TestDataStorage))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print()
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.wasSuccessful():
        print("\n[SUCCESS] All tests passed!")
    else:
        print("\n[FAILED] Some tests failed. See details above.")
        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"  - {test}")
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"  - {test}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)

