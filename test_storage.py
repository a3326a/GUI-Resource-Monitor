"""
Quick test script to verify database storage is working
"""
import time
from data_storage import ResourceDataStorage

# Wait a bit for data to be collected
print("Waiting 5 seconds for data collection...")
time.sleep(5)

# Check database
storage = ResourceDataStorage("resource_monitor.db")
stats = storage.get_statistics()

print("\n" + "=" * 50)
print("Database Storage Test Results")
print("=" * 50)
print(f"Total records stored: {stats.get('total_records', 0)}")

if stats.get('oldest_timestamp'):
    print(f"Oldest record: {stats['oldest_timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
if stats.get('newest_timestamp'):
    print(f"Newest record: {stats['newest_timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")

print(f"Database size: {stats.get('database_size_mb', 0):.2f} MB")

# Get latest 5 records
print("\nLatest 5 records:")
latest = storage.get_latest_metrics(5)
for i, m in enumerate(latest, 1):
    print(f"  {i}. {m.timestamp.strftime('%H:%M:%S')} - "
          f"CPU: {m.cpu_percent:.1f}%, "
          f"Memory: {m.memory_percent:.1f}%, "
          f"Disk: {m.disk_percent:.1f}%")

print("\n" + "=" * 50)
if stats.get('total_records', 0) > 0:
    print("Database storage is working correctly!")
else:
    print("No records found yet. Wait a bit longer and run again.")
print("=" * 50)

