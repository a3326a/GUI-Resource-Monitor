# GUI Resource Monitor

A comprehensive system resource monitoring application with real-time visualization, historical data analysis, and export capabilities. Built with Python, Tkinter, and Matplotlib.

## Features

### Phase 1: Resource Data Collection
- Real-time collection of CPU, memory, disk, and network metrics
- Thread-safe metric collection at configurable intervals
- In-memory storage with optional database persistence
- Automatic rate calculation for network and disk I/O

### Phase 2: GUI Design and Real-Time Display
- Live updating graphs for all resource types
- Real-time statistics display with detailed information
- Responsive UI with tabbed interface
- Performance-optimized rendering with configurable update intervals

### Phase 3: Data Storage and Historical Logging
- SQLite database for persistent storage
- Thread-safe database operations
- Efficient batch insert operations
- Automatic schema creation and indexing

### Phase 4: Historical Data Visualization
- Time range selection with quick presets (Last Hour, 6 Hours, 24 Hours, All Data)
- Interactive graphs with zoom and pan capabilities
- Statistical summaries for selected time ranges
- Efficient data sampling for large datasets

### Phase 5: Exporting Graphs and Reports
- Export individual graphs as JPEG files
- Export all graphs as PDF reports
- Automatic metadata inclusion (timestamps, data ranges)
- Historical PDF exports include statistics pages

### Phase 6: Testing, Performance Optimization, and Refinement
- Comprehensive unit and integration tests
- Memory management optimizations
- Performance improvements with efficient graph updates
- Robust error handling and user feedback
- Complete test coverage

## Installation

### Requirements

- Python 3.7 or higher
- Required packages:
  ```
  psutil
  matplotlib
  tkinter (usually included with Python)
  ```

### Install Dependencies

```bash
pip install psutil matplotlib
```

## Usage

### Running the Application

```bash
python gui_monitor.py
```

### Basic Workflow

1. **Real-Time Monitoring**: The application automatically starts collecting and displaying real-time metrics.

2. **View Current Statistics**: Switch to the "Current Statistics" tab to see detailed information about current resource usage.

3. **Historical Data Analysis**:
   - Go to the "Historical Data" tab
   - Select a time range (or use quick select buttons)
   - Click "Load Historical Data"
   - View graphs and statistics for the selected period

4. **Export Data**:
   - **Real-Time Graphs**: Use export buttons in the "Real-Time Graphs" tab
   - **Historical Graphs**: Load historical data first, then use export buttons in the "Historical Data" tab

## Project Structure

```
GUI-Resource-Monitor/
├── gui_monitor.py          # Main GUI application (Phase 2, 4, 5, 6)
├── resource_collector.py   # Data collection module (Phase 1)
├── data_storage.py         # Database storage module (Phase 3)
├── tests.py                # Unit and integration tests (Phase 6)
├── resource_monitor.db     # SQLite database (auto-generated)
└── README.md              # This file
```

## API Documentation

### ResourceCollector

Main class for collecting system resource metrics.

```python
from resource_collector import ResourceCollector

# Initialize collector with 1 second interval and database storage
collector = ResourceCollector(
    collection_interval=1.0,
    enable_database_storage=True,
    db_path="resource_monitor.db"
)

# Start collecting
collector.start_collection()

# Get latest metrics
latest = collector.get_latest_metrics()

# Stop collecting
collector.stop_collection()
```

### ResourceDataStorage

Class for managing persistent storage of metrics.

```python
from data_storage import ResourceDataStorage
from datetime import datetime, timedelta

# Initialize storage
storage = ResourceDataStorage("resource_monitor.db")

# Save metrics
storage.save_metrics(metrics)

# Query by time range
start = datetime.now() - timedelta(hours=24)
end = datetime.now()
metrics = storage.get_metrics_by_time_range(start, end)

# Get statistics
stats = storage.get_statistics()
```

### ResourceMonitorGUI

Main GUI application class.

```python
import tkinter as tk
from resource_collector import ResourceCollector
from gui_monitor import ResourceMonitorGUI

# Setup collector
collector = ResourceCollector(enable_database_storage=True)
collector.start_collection()

# Create GUI
root = tk.Tk()
app = ResourceMonitorGUI(root, collector, update_interval=1000)
root.mainloop()
```

## Testing

Run the test suite:

```bash
python tests.py
```

The test suite includes:
- Unit tests for ResourceMetrics
- Unit tests for ResourceCollector
- Unit tests for ResourceDataStorage
- Integration tests for complete workflows

## Performance Considerations

- **Memory Management**: Real-time graphs are limited to 60 data points. Historical data in memory is limited to 10,000 records.
- **Database Optimization**: Batch inserts are used (every 10 records) to minimize database overhead.
- **Graph Rendering**: Uses `draw_idle()` for efficient updates and samples large datasets for display.
- **Query Performance**: Database includes indexed timestamp column for fast time-range queries.

## Configuration

### Collection Interval

Adjust the collection interval in `main()`:

```python
collector = ResourceCollector(collection_interval=1.0)  # seconds
```

### GUI Update Interval

Adjust GUI refresh rate:

```python
app = ResourceMonitorGUI(root, collector, update_interval=1000)  # milliseconds
```

### Memory Limits

Adjust limits in `ResourceMonitorGUI.__init__()`:

```python
self.max_data_points = 60  # Real-time graph points
self.max_historical_in_memory = 10000  # Historical records limit
```

## License

This project is provided as-is for educational and demonstration purposes.

## Author

GUI Resource Monitor - Complete implementation of all 6 phases.
