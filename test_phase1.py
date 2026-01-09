"""
Test script for Phase 1: Resource Data Collection
Demonstrates the functionality of collecting system resource metrics.
"""

import time
from resource_collector import ResourceCollector


def main():
    print("=" * 60)
    print("GUI Resource Monitor - Phase 1: Resource Data Collection")
    print("=" * 60)
    print("\nThis script demonstrates real-time system resource monitoring.")
    print("Metrics are collected every second and stored in memory.\n")
    
    # Create collector with 1 second interval
    collector = ResourceCollector(collection_interval=1.0)
    
    print("Starting resource collection...")
    print("Press Ctrl+C to stop\n")
    print("-" * 60)
    
    collector.start_collection()
    
    try:
        # Display metrics for 30 seconds or until interrupted
        start_time = time.time()
        while time.time() - start_time < 30:
            time.sleep(1)
            latest = collector.get_latest_metrics()
            
            if latest:
                print(f"\nTimestamp: {latest.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"  CPU Usage:        {latest.cpu_percent:6.2f}%")
                print(f"  Memory Usage:     {latest.memory_percent:6.2f}% "
                      f"({latest.memory_used_mb:.0f} MB / {latest.memory_total_mb:.0f} MB)")
                print(f"  Disk Usage:       {latest.disk_percent:6.2f}% "
                      f"({latest.disk_used_gb:.2f} GB / {latest.disk_total_gb:.2f} GB)")
                print(f"  Network Sent:     {latest.network_sent_mb:.2f} MB "
                      f"(Rate: {latest.network_sent_rate_mbps:.2f} Mbps)")
                print(f"  Network Received: {latest.network_recv_mb:.2f} MB "
                      f"(Rate: {latest.network_recv_rate_mbps:.2f} Mbps)")
                print("-" * 60)
    
    except KeyboardInterrupt:
        print("\n\nCollection interrupted by user")
    
    finally:
        collector.stop_collection()
        
        # Display summary
        total_metrics = collector.get_history_count()
        print(f"\n{'=' * 60}")
        print(f"Collection Summary:")
        print(f"  Total metrics collected: {total_metrics}")
        
        if total_metrics > 0:
            history = collector.get_metrics_history()
            print(f"  First timestamp: {history[0].timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  Last timestamp:  {history[-1].timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Calculate averages
            avg_cpu = sum(m.cpu_percent for m in history) / len(history)
            avg_memory = sum(m.memory_percent for m in history) / len(history)
            avg_disk = sum(m.disk_percent for m in history) / len(history)
            
            print(f"\n  Average CPU Usage:    {avg_cpu:.2f}%")
            print(f"  Average Memory Usage: {avg_memory:.2f}%")
            print(f"  Average Disk Usage:   {avg_disk:.2f}%")
        
        print(f"{'=' * 60}")
        print("\nPhase 1 implementation complete!")
        print("All metrics are stored in memory and ready for Phase 2 (GUI Display).")


if __name__ == "__main__":
    main()

