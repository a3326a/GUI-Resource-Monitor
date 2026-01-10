"""
Phase 2, 4, 5 & 6: Complete GUI Resource Monitor Application.

A comprehensive resource monitoring application with real-time visualization,
historical data analysis, and export capabilities. This application provides
a user-friendly interface for monitoring system resources including CPU, memory,
disk, and network usage.

Features:
    - Real-time resource monitoring with live updating graphs
    - Historical data visualization with time range selection and filtering
    - Export graphs as JPEG or PDF files with metadata
    - Optimized performance with memory management and efficient rendering
    - Comprehensive error handling and user feedback
    - Thread-safe operations for data collection and storage

Classes:
    ResourceMonitorGUI: Main GUI application class managing the interface.

Example:
    >>> from resource_collector import ResourceCollector
    >>> collector = ResourceCollector(collection_interval=1.0, enable_database_storage=True)
    >>> collector.start_collection()
    >>> root = tk.Tk()
    >>> app = ResourceMonitorGUI(root, collector)
    >>> root.mainloop()
"""

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, filedialog
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.animation import FuncAnimation
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
from datetime import datetime, timedelta
from typing import List, Optional
import os
from resource_collector import ResourceCollector, ResourceMetrics
from data_storage import ResourceDataStorage


class ResourceMonitorGUI:
    """GUI application for real-time resource monitoring with live graphs.
    
    This class manages the complete graphical user interface for the resource
    monitor application. It handles real-time graph updates, historical data
    visualization, data export, and user interactions.
    
    The GUI consists of three main tabs:
        - Real-Time Graphs: Live updating graphs of current resource usage
        - Current Statistics: Detailed statistics for current system state
        - Historical Data: Time-range selection and historical data visualization
    
    Attributes:
        root (tk.Tk): The main Tkinter root window.
        collector (ResourceCollector): Resource collector instance providing metrics.
        db_storage (ResourceDataStorage): Database storage for historical data.
        max_data_points (int): Maximum number of data points in real-time graphs (60).
        max_historical_in_memory (int): Maximum historical metrics kept in memory (10000).
    
    Example:
        >>> collector = ResourceCollector(enable_database_storage=True)
        >>> collector.start_collection()
        >>> root = tk.Tk()
        >>> app = ResourceMonitorGUI(root, collector, update_interval=1000)
        >>> root.mainloop()
    """
    
    def __init__(
        self,
        root: tk.Tk,
        collector: ResourceCollector,
        update_interval: int = 1000,
        db_path: str = "resource_monitor.db"
    ) -> None:
        """Initialize the GUI application.
        
        Sets up the main window, creates all GUI components, initializes data
        structures, and starts the periodic update loop.
        
        Args:
            root: Tkinter root window instance.
            collector: ResourceCollector instance that provides system metrics.
            update_interval: GUI update interval in milliseconds. Default is 1000ms
                (1 second). Lower values provide more responsive updates but may
                impact performance.
            db_path: Path to SQLite database file for historical data storage.
                Default is "resource_monitor.db".
        """
        self.root = root
        self.collector = collector
        self.update_interval = update_interval
        
        # Database storage for historical data
        self.db_storage = ResourceDataStorage(db_path)
        
        # Configure window
        self.root.title("GUI Resource Monitor")
        self.root.geometry("1400x900")
        self.root.configure(bg='#f0f0f0')
        
        # Data storage for graphs (keep last 60 data points)
        self.max_data_points = 60
        self.time_data: List[datetime] = []
        self.cpu_data: List[float] = []
        self.memory_data: List[float] = []
        self.disk_data: List[float] = []
        self.network_sent_data: List[float] = []
        self.network_recv_data: List[float] = []
        
        # Historical data storage (limit in memory to prevent excessive usage)
        self.historical_metrics: List[ResourceMetrics] = []
        self.max_historical_in_memory = 10000  # Limit historical data kept in memory
        
        # Performance optimization: batch canvas updates
        self._pending_graph_update = False
        self._pending_stats_update = False
        
        # Create GUI components
        self._create_widgets()
        
        # Start GUI updates
        self._update_gui()
    
    def _create_widgets(self):
        """Create and layout all GUI widgets."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        # Configure rows: row 0 (title) - no weight, row 1 (notebook) - expand, row 2 (status) - no weight
        main_frame.rowconfigure(0, weight=0)
        main_frame.rowconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=0)
        
        # Title
        title_label = tk.Label(
            main_frame,
            text="System Resource Monitor",
            font=("Arial", 18, "bold"),
            bg='#f0f0f0'
        )
        title_label.grid(row=0, column=0, pady=(0, 10), sticky=(tk.W, tk.E))
        
        # Create notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Tab 1: Graphs
        graphs_frame = ttk.Frame(notebook, padding="10")
        notebook.add(graphs_frame, text="Real-Time Graphs")
        self._create_graphs_tab(graphs_frame)
        
        # Tab 2: Statistics
        stats_frame = ttk.Frame(notebook, padding="10")
        notebook.add(stats_frame, text="Current Statistics")
        self._create_stats_tab(stats_frame)
        
        # Tab 3: Historical Data
        historical_frame = ttk.Frame(notebook, padding="10")
        notebook.add(historical_frame, text="Historical Data")
        self._create_historical_tab(historical_frame)
        
        # Status bar - make it more visible with a border/background
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        status_frame.columnconfigure(0, weight=1)
        
        self.status_label = tk.Label(
            status_frame,
            text="Status: Initializing...",
            font=("Arial", 9),
            bg='#e0e0e0',  # Slightly darker background for visibility
            fg='#000000',
            anchor=tk.W,
            relief=tk.SUNKEN,  # Give it a sunken border to look like a status bar
            borderwidth=1,
            padx=5,
            pady=2
        )
        self.status_label.grid(row=0, column=0, sticky=(tk.W, tk.E))
    
    def _create_graphs_tab(self, parent):
        """Create the graphs tab with real-time charts."""
        # Configure grid
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        parent.rowconfigure(2, weight=0)  # Export buttons row
        
        # CPU Graph
        self.cpu_fig = Figure(figsize=(5, 3), dpi=100, facecolor='white')
        self.cpu_ax = self.cpu_fig.add_subplot(111)
        self.cpu_ax.set_title("CPU Usage (%)", fontsize=12, fontweight='bold')
        self.cpu_ax.set_ylim(0, 100)
        self.cpu_ax.set_xlabel("Time")
        self.cpu_ax.set_ylabel("Percentage (%)")
        self.cpu_ax.grid(True, alpha=0.3)
        self.cpu_line, = self.cpu_ax.plot([], [], 'b-', linewidth=2, label='CPU')
        self.cpu_ax.legend()
        self.cpu_canvas = FigureCanvasTkAgg(self.cpu_fig, parent)
        self.cpu_canvas.get_tk_widget().grid(row=0, column=0, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Memory Graph
        self.memory_fig = Figure(figsize=(5, 3), dpi=100, facecolor='white')
        self.memory_ax = self.memory_fig.add_subplot(111)
        self.memory_ax.set_title("Memory Usage (%)", fontsize=12, fontweight='bold')
        self.memory_ax.set_ylim(0, 100)
        self.memory_ax.set_xlabel("Time")
        self.memory_ax.set_ylabel("Percentage (%)")
        self.memory_ax.grid(True, alpha=0.3)
        self.memory_line, = self.memory_ax.plot([], [], 'g-', linewidth=2, label='Memory')
        self.memory_ax.legend()
        self.memory_canvas = FigureCanvasTkAgg(self.memory_fig, parent)
        self.memory_canvas.get_tk_widget().grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Disk Graph
        self.disk_fig = Figure(figsize=(5, 3), dpi=100, facecolor='white')
        self.disk_ax = self.disk_fig.add_subplot(111)
        self.disk_ax.set_title("Disk Usage (%)", fontsize=12, fontweight='bold')
        self.disk_ax.set_ylim(0, 100)
        self.disk_ax.set_xlabel("Time")
        self.disk_ax.set_ylabel("Percentage (%)")
        self.disk_ax.grid(True, alpha=0.3)
        self.disk_line, = self.disk_ax.plot([], [], 'r-', linewidth=2, label='Disk')
        self.disk_ax.legend()
        self.disk_canvas = FigureCanvasTkAgg(self.disk_fig, parent)
        self.disk_canvas.get_tk_widget().grid(row=1, column=0, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Network Graph
        self.network_fig = Figure(figsize=(5, 3), dpi=100, facecolor='white')
        self.network_ax = self.network_fig.add_subplot(111)
        self.network_ax.set_title("Network Usage (Mbps)", fontsize=12, fontweight='bold')
        self.network_ax.set_xlabel("Time")
        self.network_ax.set_ylabel("Rate (Mbps)")
        self.network_ax.grid(True, alpha=0.3)
        self.network_sent_line, = self.network_ax.plot([], [], 'c-', linewidth=2, label='Sent')
        self.network_recv_line, = self.network_ax.plot([], [], 'm-', linewidth=2, label='Received')
        self.network_ax.legend()
        self.network_canvas = FigureCanvasTkAgg(self.network_fig, parent)
        self.network_canvas.get_tk_widget().grid(row=1, column=1, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Export buttons frame
        export_frame = ttk.LabelFrame(parent, text="Export Real-Time Graphs", padding="10")
        export_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        ttk.Button(export_frame, text="Export All Graphs as PDF", command=self._export_realtime_all_pdf).pack(side=tk.LEFT, padx=5)
        # Real-time graphs are always available (is_historical=False)
        ttk.Button(export_frame, text="Export CPU as JPEG", command=lambda: self._export_single_graph(self.cpu_fig, "CPU_Usage", "JPEG", is_historical=False)).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_frame, text="Export Memory as JPEG", command=lambda: self._export_single_graph(self.memory_fig, "Memory_Usage", "JPEG", is_historical=False)).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_frame, text="Export Disk as JPEG", command=lambda: self._export_single_graph(self.disk_fig, "Disk_Usage", "JPEG", is_historical=False)).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_frame, text="Export Network as JPEG", command=lambda: self._export_single_graph(self.network_fig, "Network_Usage", "JPEG", is_historical=False)).pack(side=tk.LEFT, padx=5)
    
    def _create_stats_tab(self, parent):
        """Create the statistics tab with current values."""
        # Main stats frame
        stats_container = ttk.Frame(parent)
        stats_container.pack(fill=tk.BOTH, expand=True)
        
        # CPU Stats
        cpu_frame = ttk.LabelFrame(stats_container, text="CPU", padding="15")
        cpu_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.cpu_percent_label = tk.Label(
            cpu_frame,
            text="Usage: 0.0%",
            font=("Arial", 14, "bold"),
            fg='blue'
        )
        self.cpu_percent_label.pack(anchor=tk.W)
        
        # Memory Stats
        memory_frame = ttk.LabelFrame(stats_container, text="Memory", padding="15")
        memory_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.memory_percent_label = tk.Label(
            memory_frame,
            text="Usage: 0.0%",
            font=("Arial", 14, "bold"),
            fg='green'
        )
        self.memory_percent_label.pack(anchor=tk.W)
        
        self.memory_details_label = tk.Label(
            memory_frame,
            text="Used: 0 MB / Total: 0 MB",
            font=("Arial", 11)
        )
        self.memory_details_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Disk Stats
        disk_frame = ttk.LabelFrame(stats_container, text="Disk", padding="15")
        disk_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.disk_percent_label = tk.Label(
            disk_frame,
            text="Usage: 0.0%",
            font=("Arial", 14, "bold"),
            fg='red'
        )
        self.disk_percent_label.pack(anchor=tk.W)
        
        self.disk_details_label = tk.Label(
            disk_frame,
            text="Used: 0.00 GB / Total: 0.00 GB",
            font=("Arial", 11)
        )
        self.disk_details_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Network Stats
        network_frame = ttk.LabelFrame(stats_container, text="Network", padding="15")
        network_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.network_sent_label = tk.Label(
            network_frame,
            text="Sent: 0.00 MB (Rate: 0.00 Mbps)",
            font=("Arial", 11),
            fg='cyan'
        )
        self.network_sent_label.pack(anchor=tk.W)
        
        self.network_recv_label = tk.Label(
            network_frame,
            text="Received: 0.00 MB (Rate: 0.00 Mbps)",
            font=("Arial", 11),
            fg='magenta'
        )
        self.network_recv_label.pack(anchor=tk.W, pady=(5, 0))
        
        # Timestamp
        self.timestamp_label = tk.Label(
            stats_container,
            text="Last Update: --",
            font=("Arial", 9),
            fg='gray'
        )
        self.timestamp_label.pack(side=tk.BOTTOM, pady=10)
    
    def _create_historical_tab(self, parent):
        """Create the historical data visualization tab."""
        # Top control panel
        control_frame = ttk.LabelFrame(parent, text="Time Range Selection", padding="10")
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Start time
        ttk.Label(control_frame, text="Start Time:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.hist_start_date = tk.StringVar(value=(datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d"))
        self.hist_start_time = tk.StringVar(value=(datetime.now() - timedelta(hours=1)).strftime("%H:%M:%S"))
        ttk.Entry(control_frame, textvariable=self.hist_start_date, width=12).grid(row=0, column=1, padx=2)
        ttk.Entry(control_frame, textvariable=self.hist_start_time, width=10).grid(row=0, column=2, padx=2)
        
        # End time
        ttk.Label(control_frame, text="End Time:").grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        self.hist_end_date = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self.hist_end_time = tk.StringVar(value=datetime.now().strftime("%H:%M:%S"))
        ttk.Entry(control_frame, textvariable=self.hist_end_date, width=12).grid(row=0, column=4, padx=2)
        ttk.Entry(control_frame, textvariable=self.hist_end_time, width=10).grid(row=0, column=5, padx=2)
        
        # Quick select buttons
        quick_frame = ttk.Frame(control_frame)
        quick_frame.grid(row=0, column=6, padx=10)
        ttk.Button(quick_frame, text="Last Hour", command=lambda: self._set_time_range(1)).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_frame, text="Last 6 Hours", command=lambda: self._set_time_range(6)).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_frame, text="Last 24 Hours", command=lambda: self._set_time_range(24)).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_frame, text="All Data", command=self._set_time_range_all).pack(side=tk.LEFT, padx=2)
        
        # Load button
        ttk.Button(control_frame, text="Load Historical Data", command=self._load_historical_data).grid(row=0, column=7, padx=10)
        
        # Info label
        self.hist_info_label = tk.Label(
            control_frame,
            text="Select time range and click 'Load Historical Data'",
            font=("Arial", 9),
            fg='gray'
        )
        self.hist_info_label.grid(row=1, column=0, columnspan=8, pady=5)
        
        # Export buttons frame for historical data - PLACED RIGHT AFTER CONTROL PANEL for visibility
        hist_export_frame = ttk.LabelFrame(parent, text="Export Historical Graphs", padding="10")
        hist_export_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # First row of export buttons
        export_row1 = ttk.Frame(hist_export_frame)
        export_row1.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(export_row1, text="Export All as PDF", command=self._export_historical_all_pdf).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_row1, text="Export CPU as JPEG", command=lambda: self._export_single_graph(self.hist_cpu_fig, "Historical_CPU_Usage", "JPEG", is_historical=True)).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_row1, text="Export Memory as JPEG", command=lambda: self._export_single_graph(self.hist_memory_fig, "Historical_Memory_Usage", "JPEG", is_historical=True)).pack(side=tk.LEFT, padx=5)
        
        # Second row of export buttons
        export_row2 = ttk.Frame(hist_export_frame)
        export_row2.pack(fill=tk.X)
        ttk.Button(export_row2, text="Export Disk as JPEG", command=lambda: self._export_single_graph(self.hist_disk_fig, "Historical_Disk_Usage", "JPEG", is_historical=True)).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_row2, text="Export Network as JPEG", command=lambda: self._export_single_graph(self.hist_network_fig, "Historical_Network_Usage", "JPEG", is_historical=True)).pack(side=tk.LEFT, padx=5)
        
        # Graphs container - now it won't hide the export buttons
        graphs_container = ttk.Frame(parent)
        graphs_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        graphs_container.columnconfigure(0, weight=1)
        graphs_container.columnconfigure(1, weight=1)
        graphs_container.rowconfigure(0, weight=1)
        graphs_container.rowconfigure(1, weight=1)
        
        # Historical CPU Graph
        cpu_frame = ttk.Frame(graphs_container)
        cpu_frame.grid(row=0, column=0, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        cpu_frame.columnconfigure(0, weight=1)
        cpu_frame.rowconfigure(0, weight=1)
        cpu_frame.rowconfigure(1, weight=0)  # Toolbar row
        self.hist_cpu_fig = Figure(figsize=(6, 4), dpi=100, facecolor='white')
        self.hist_cpu_ax = self.hist_cpu_fig.add_subplot(111)
        self.hist_cpu_ax.set_title("Historical CPU Usage (%)", fontsize=12, fontweight='bold')
        self.hist_cpu_ax.set_ylabel("Percentage (%)")
        self.hist_cpu_ax.grid(True, alpha=0.3)
        self.hist_cpu_canvas = FigureCanvasTkAgg(self.hist_cpu_fig, cpu_frame)
        self.hist_cpu_canvas.get_tk_widget().grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        # Toolbar in separate frame that uses pack
        cpu_toolbar_frame = tk.Frame(cpu_frame)
        cpu_toolbar_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        hist_cpu_toolbar = NavigationToolbar2Tk(self.hist_cpu_canvas, cpu_toolbar_frame)
        hist_cpu_toolbar.update()
        
        # Historical Memory Graph
        memory_frame = ttk.Frame(graphs_container)
        memory_frame.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        memory_frame.columnconfigure(0, weight=1)
        memory_frame.rowconfigure(0, weight=1)
        memory_frame.rowconfigure(1, weight=0)  # Toolbar row
        self.hist_memory_fig = Figure(figsize=(6, 4), dpi=100, facecolor='white')
        self.hist_memory_ax = self.hist_memory_fig.add_subplot(111)
        self.hist_memory_ax.set_title("Historical Memory Usage (%)", fontsize=12, fontweight='bold')
        self.hist_memory_ax.set_ylabel("Percentage (%)")
        self.hist_memory_ax.grid(True, alpha=0.3)
        self.hist_memory_canvas = FigureCanvasTkAgg(self.hist_memory_fig, memory_frame)
        self.hist_memory_canvas.get_tk_widget().grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        # Toolbar in separate frame that uses pack
        memory_toolbar_frame = tk.Frame(memory_frame)
        memory_toolbar_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        hist_memory_toolbar = NavigationToolbar2Tk(self.hist_memory_canvas, memory_toolbar_frame)
        hist_memory_toolbar.update()
        
        # Historical Disk Graph
        disk_frame = ttk.Frame(graphs_container)
        disk_frame.grid(row=1, column=0, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        disk_frame.columnconfigure(0, weight=1)
        disk_frame.rowconfigure(0, weight=1)
        disk_frame.rowconfigure(1, weight=0)  # Toolbar row
        self.hist_disk_fig = Figure(figsize=(6, 4), dpi=100, facecolor='white')
        self.hist_disk_ax = self.hist_disk_fig.add_subplot(111)
        self.hist_disk_ax.set_title("Historical Disk Usage (%)", fontsize=12, fontweight='bold')
        self.hist_disk_ax.set_ylabel("Percentage (%)")
        self.hist_disk_ax.grid(True, alpha=0.3)
        self.hist_disk_canvas = FigureCanvasTkAgg(self.hist_disk_fig, disk_frame)
        self.hist_disk_canvas.get_tk_widget().grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        # Toolbar in separate frame that uses pack
        disk_toolbar_frame = tk.Frame(disk_frame)
        disk_toolbar_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        hist_disk_toolbar = NavigationToolbar2Tk(self.hist_disk_canvas, disk_toolbar_frame)
        hist_disk_toolbar.update()
        
        # Historical Network Graph
        network_frame = ttk.Frame(graphs_container)
        network_frame.grid(row=1, column=1, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        network_frame.columnconfigure(0, weight=1)
        network_frame.rowconfigure(0, weight=1)
        network_frame.rowconfigure(1, weight=0)  # Toolbar row
        self.hist_network_fig = Figure(figsize=(6, 4), dpi=100, facecolor='white')
        self.hist_network_ax = self.hist_network_fig.add_subplot(111)
        self.hist_network_ax.set_title("Historical Network Usage (Mbps)", fontsize=12, fontweight='bold')
        self.hist_network_ax.set_ylabel("Rate (Mbps)")
        self.hist_network_ax.grid(True, alpha=0.3)
        self.hist_network_canvas = FigureCanvasTkAgg(self.hist_network_fig, network_frame)
        self.hist_network_canvas.get_tk_widget().grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        # Toolbar in separate frame that uses pack
        network_toolbar_frame = tk.Frame(network_frame)
        network_toolbar_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        hist_network_toolbar = NavigationToolbar2Tk(self.hist_network_canvas, network_toolbar_frame)
        hist_network_toolbar.update()
        
        # Statistics panel - placed after graphs
        stats_panel = ttk.LabelFrame(parent, text="Statistics for Selected Range", padding="10")
        stats_panel.pack(fill=tk.X, padx=5, pady=5)
        
        self.hist_stats_label = tk.Label(
            stats_panel,
            text="Load data to see statistics",
            font=("Arial", 10),
            justify=tk.LEFT
        )
        self.hist_stats_label.pack(anchor=tk.W)
    
    def _set_time_range(self, hours: int):
        """Set time range to last N hours."""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        self.hist_start_date.set(start_time.strftime("%Y-%m-%d"))
        self.hist_start_time.set(start_time.strftime("%H:%M:%S"))
        self.hist_end_date.set(end_time.strftime("%Y-%m-%d"))
        self.hist_end_time.set(end_time.strftime("%H:%M:%S"))
    
    def _set_time_range_all(self):
        """Set time range to all available data."""
        stats = self.db_storage.get_statistics()
        if stats.get('oldest_timestamp') and stats.get('newest_timestamp'):
            self.hist_start_date.set(stats['oldest_timestamp'].strftime("%Y-%m-%d"))
            self.hist_start_time.set(stats['oldest_timestamp'].strftime("%H:%M:%S"))
            self.hist_end_date.set(stats['newest_timestamp'].strftime("%Y-%m-%d"))
            self.hist_end_time.set(stats['newest_timestamp'].strftime("%H:%M:%S"))
        else:
            messagebox.showinfo("Info", "No historical data available yet.")
    
    def _load_historical_data(self):
        """Load historical data from database for selected time range."""
        try:
            # Parse start and end times with validation
            start_str = f"{self.hist_start_date.get()} {self.hist_start_time.get()}"
            end_str = f"{self.hist_end_date.get()} {self.hist_end_time.get()}"
            
            try:
                start_time = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
                end_time = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")
            except ValueError as ve:
                messagebox.showerror("Error", f"Invalid date/time format.\n\nExpected format: YYYY-MM-DD HH:MM:SS\nExample: 2026-01-09 14:30:00\n\nError: {ve}")
                return
            
            if start_time >= end_time:
                messagebox.showerror("Error", "Start time must be before end time!")
                return
            
            # Check for reasonable time range (warn if > 30 days)
            time_diff = (end_time - start_time).total_seconds()
            if time_diff > 30 * 24 * 3600:  # 30 days
                response = messagebox.askyesno(
                    "Large Time Range",
                    f"The selected time range is {time_diff/(24*3600):.1f} days.\n"
                    f"This may take a while to load and display.\n\n"
                    f"Do you want to continue?"
                )
                if not response:
                    return
            
            # Load data from database with progress indication
            self.hist_info_label.config(text="Loading data from database... Please wait.")
            self.root.update()
            
            # Load in a separate thread to avoid blocking UI
            def load_data():
                try:
                    metrics = self.db_storage.get_metrics_by_time_range(start_time, end_time)
                    
                    # Limit stored metrics in memory
                    if len(metrics) > self.max_historical_in_memory:
                        # Keep only most recent N metrics
                        metrics = metrics[-self.max_historical_in_memory:]
                        self.hist_info_label.config(
                            text=f"Warning: Only showing last {self.max_historical_in_memory:,} of {len(metrics):,} records for performance."
                        )
                    
                    self.historical_metrics = metrics
                    
                    # Update graphs and statistics on main thread
                    self.root.after(0, self._update_after_load, start_time, end_time)
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror("Error", f"Error loading data: {e}"))
                    self.root.after(0, lambda: self.hist_info_label.config(text="Error loading data"))
            
            # Start loading in background
            import threading
            thread = threading.Thread(target=load_data, daemon=True)
            thread.start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error: {e}")
            self.hist_info_label.config(text="Error loading data")
    
    def _update_after_load(self, start_time: datetime, end_time: datetime):
        """Update graphs and statistics after data is loaded."""
        if not self.historical_metrics:
            messagebox.showinfo("Info", "No data found for the selected time range.")
            self.hist_info_label.config(text="No data found for selected range")
            return
        
        # Update graphs
        self._update_historical_graphs()
        
        # Update statistics
        self._update_historical_statistics()
        
        # Update info
        total_records = len(self.historical_metrics)
        if total_records > self.max_historical_in_memory:
            self.hist_info_label.config(
                text=f"Loaded {total_records:,} records (showing last {self.max_historical_in_memory:,}) from {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}"
            )
        else:
            self.hist_info_label.config(
                text=f"Loaded {total_records:,} records from {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}"
            )
    
    def _update_historical_graphs(self):
        """Update historical graphs with loaded data."""
        if not self.historical_metrics:
            return
        
        # Limit data points if too many for better performance
        # Sample data if more than threshold to avoid slow rendering
        max_points_for_display = 5000
        if len(self.historical_metrics) > max_points_for_display:
            # Sample every Nth point for display
            step = len(self.historical_metrics) // max_points_for_display
            sampled_metrics = self.historical_metrics[::step]
        else:
            sampled_metrics = self.historical_metrics
        
        # Extract data from sampled metrics
        timestamps = [m.timestamp for m in sampled_metrics]
        cpu_values = [m.cpu_percent for m in sampled_metrics]
        memory_values = [m.memory_percent for m in sampled_metrics]
        disk_values = [m.disk_percent for m in sampled_metrics]
        network_sent = [m.network_sent_rate_mbps for m in sampled_metrics]
        network_recv = [m.network_recv_rate_mbps for m in sampled_metrics]
        
        # Determine time range to format X-axis appropriately
        if timestamps:
            time_span = (timestamps[-1] - timestamps[0]).total_seconds()
            if time_span > 86400:  # More than 1 day
                date_format = '%Y-%m-%d\n%H:%M'
            elif time_span > 3600:  # More than 1 hour
                date_format = '%m-%d %H:%M'
            else:  # Less than 1 hour
                date_format = '%H:%M:%S'
        else:
            date_format = '%H:%M:%S'
        
        # Update CPU graph
        self.hist_cpu_ax.clear()
        self.hist_cpu_ax.plot(timestamps, cpu_values, 'b-', linewidth=1.5, label='CPU')
        self.hist_cpu_ax.set_title("Historical CPU Usage (%)", fontsize=12, fontweight='bold')
        self.hist_cpu_ax.set_xlabel("Time")
        self.hist_cpu_ax.set_ylabel("Percentage (%)")
        self.hist_cpu_ax.set_ylim(0, 100)
        if timestamps:
            self.hist_cpu_ax.set_xlim(timestamps[0], timestamps[-1])
        self.hist_cpu_ax.grid(True, alpha=0.3)
        self.hist_cpu_ax.legend()
        self.hist_cpu_ax.xaxis.set_major_formatter(DateFormatter(date_format))
        self.hist_cpu_fig.autofmt_xdate()
        self.hist_cpu_canvas.draw()
        
        # Update Memory graph
        self.hist_memory_ax.clear()
        self.hist_memory_ax.plot(timestamps, memory_values, 'g-', linewidth=1.5, label='Memory')
        self.hist_memory_ax.set_title("Historical Memory Usage (%)", fontsize=12, fontweight='bold')
        self.hist_memory_ax.set_xlabel("Time")
        self.hist_memory_ax.set_ylabel("Percentage (%)")
        self.hist_memory_ax.set_ylim(0, 100)
        if timestamps:
            self.hist_memory_ax.set_xlim(timestamps[0], timestamps[-1])
        self.hist_memory_ax.grid(True, alpha=0.3)
        self.hist_memory_ax.legend()
        self.hist_memory_ax.xaxis.set_major_formatter(DateFormatter(date_format))
        self.hist_memory_fig.autofmt_xdate()
        self.hist_memory_canvas.draw()
        
        # Update Disk graph
        self.hist_disk_ax.clear()
        self.hist_disk_ax.plot(timestamps, disk_values, 'r-', linewidth=1.5, label='Disk')
        self.hist_disk_ax.set_title("Historical Disk Usage (%)", fontsize=12, fontweight='bold')
        self.hist_disk_ax.set_xlabel("Time")
        self.hist_disk_ax.set_ylabel("Percentage (%)")
        max_disk = max(disk_values) if disk_values else 100
        self.hist_disk_ax.set_ylim(0, max(max_disk * 1.1, 10))
        if timestamps:
            self.hist_disk_ax.set_xlim(timestamps[0], timestamps[-1])
        self.hist_disk_ax.grid(True, alpha=0.3)
        self.hist_disk_ax.legend()
        self.hist_disk_ax.xaxis.set_major_formatter(DateFormatter(date_format))
        self.hist_disk_fig.autofmt_xdate()
        self.hist_disk_canvas.draw()
        
        # Update Network graph
        self.hist_network_ax.clear()
        self.hist_network_ax.plot(timestamps, network_sent, 'c-', linewidth=1.5, label='Sent')
        self.hist_network_ax.plot(timestamps, network_recv, 'm-', linewidth=1.5, label='Received')
        self.hist_network_ax.set_title("Historical Network Usage (Mbps)", fontsize=12, fontweight='bold')
        self.hist_network_ax.set_xlabel("Time")
        self.hist_network_ax.set_ylabel("Rate (Mbps)")
        max_network = max(max(network_sent) if network_sent else 0, max(network_recv) if network_recv else 0, 1)
        self.hist_network_ax.set_ylim(0, max_network * 1.1)
        if timestamps:
            self.hist_network_ax.set_xlim(timestamps[0], timestamps[-1])
        self.hist_network_ax.grid(True, alpha=0.3)
        self.hist_network_ax.legend()
        self.hist_network_ax.xaxis.set_major_formatter(DateFormatter(date_format))
        self.hist_network_fig.autofmt_xdate()
        self.hist_network_canvas.draw()
    
    def _update_historical_statistics(self):
        """Update statistics panel with data for selected range."""
        if not self.historical_metrics:
            return
        
        # Calculate statistics
        cpu_values = [m.cpu_percent for m in self.historical_metrics]
        memory_values = [m.memory_percent for m in self.historical_metrics]
        disk_values = [m.disk_percent for m in self.historical_metrics]
        network_sent = [m.network_sent_rate_mbps for m in self.historical_metrics]
        network_recv = [m.network_recv_rate_mbps for m in self.historical_metrics]
        
        stats_text = f"Records: {len(self.historical_metrics)}\n\n"
        stats_text += f"CPU - Avg: {sum(cpu_values)/len(cpu_values):.2f}%, "
        stats_text += f"Min: {min(cpu_values):.2f}%, Max: {max(cpu_values):.2f}%\n"
        stats_text += f"Memory - Avg: {sum(memory_values)/len(memory_values):.2f}%, "
        stats_text += f"Min: {min(memory_values):.2f}%, Max: {max(memory_values):.2f}%\n"
        stats_text += f"Disk - Avg: {sum(disk_values)/len(disk_values):.2f}%, "
        stats_text += f"Min: {min(disk_values):.2f}%, Max: {max(disk_values):.2f}%\n"
        stats_text += f"Network Sent - Avg: {sum(network_sent)/len(network_sent):.2f} Mbps, "
        stats_text += f"Max: {max(network_sent):.2f} Mbps\n"
        stats_text += f"Network Received - Avg: {sum(network_recv)/len(network_recv):.2f} Mbps, "
        stats_text += f"Max: {max(network_recv):.2f} Mbps"
        
        self.hist_stats_label.config(text=stats_text)
    
    def _export_single_graph(self, figure: Figure, default_name: str, file_format: str, is_historical: bool = False):
        """
        Export a single graph to JPEG or PDF file.
        
        Args:
            figure: Matplotlib Figure object to export
            default_name: Default filename (without extension)
            file_format: File format ('JPEG' or 'PDF')
            is_historical: If True, check if historical data is loaded before exporting
        """
        try:
            # Validate inputs
            if figure is None or len(figure.axes) == 0:
                messagebox.showerror("Error", "Cannot export: Graph figure is empty or invalid.")
                return
            
            # For historical graphs, check if data is loaded
            if is_historical:
                if not self.historical_metrics:
                    messagebox.showwarning(
                        "No Data Loaded",
                        "No historical data is currently loaded.\n\n"
                        "Please:\n"
                        "1. Select a time range (or use 'All Data')\n"
                        "2. Click 'Load Historical Data'\n"
                        "3. Then try exporting again."
                    )
                    return
                
                # Check if graph actually has data (has plotted lines)
                ax = figure.axes[0]
                if not ax.lines or len(ax.lines) == 0:
                    messagebox.showwarning(
                        "Empty Graph",
                        "The historical graph is empty (no data to display).\n\n"
                        "Please load historical data first."
                    )
                    return
            
            # Generate default filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Sanitize filename (remove invalid characters)
            safe_name = "".join(c for c in default_name if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_name = safe_name.replace(' ', '_')
            default_filename = f"{safe_name}_{timestamp}"
            
            # Determine file extension and file type filter
            file_format_upper = file_format.upper()
            if file_format_upper == "JPEG" or file_format_upper == "JPG":
                file_ext = ".jpg"
                filetypes = [("JPEG files", "*.jpg"), ("JPEG files", "*.jpeg"), ("All files", "*.*")]
                format_name = "jpeg"
            elif file_format_upper == "PDF":
                file_ext = ".pdf"
                filetypes = [("PDF files", "*.pdf"), ("All files", "*.*")]
                format_name = "pdf"
            else:
                messagebox.showerror("Error", f"Unsupported file format: {file_format}\nSupported formats: JPEG, PDF")
                return
            
            # Ask user for save location
            filename = filedialog.asksaveasfilename(
                defaultextension=file_ext,
                filetypes=filetypes,
                initialfile=default_filename
            )
            
            if not filename:
                return  # User cancelled
            
            # Validate path is writable
            try:
                directory = os.path.dirname(filename) or os.getcwd()
                if not os.access(directory, os.W_OK):
                    messagebox.showerror("Error", f"Cannot write to directory:\n{directory}\n\nPlease select a writable location.")
                    return
            except Exception as e:
                messagebox.showerror("Error", f"Invalid file path: {e}")
                return
            
            # Add timestamp to figure title if not already present
            current_title = figure.axes[0].get_title()
            timestamp_str = f" - Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            title_changed = timestamp_str not in current_title
            if title_changed:
                figure.axes[0].set_title(current_title + timestamp_str, fontsize=10)
            
            # Save the figure with error handling
            try:
                figure.savefig(filename, format=format_name, dpi=300, bbox_inches='tight')
            except Exception as save_error:
                if title_changed:
                    figure.axes[0].set_title(current_title)  # Restore title even on error
                raise save_error
            
            # Restore original title
            if title_changed:
                figure.axes[0].set_title(current_title)
            
            # Verify file was created
            if os.path.exists(filename):
                file_size = os.path.getsize(filename) / 1024  # Size in KB
                messagebox.showinfo(
                    "Success",
                    f"Graph exported successfully!\n\n"
                    f"File: {os.path.basename(filename)}\n"
                    f"Location: {os.path.dirname(filename)}\n"
                    f"Size: {file_size:.1f} KB"
                )
            else:
                messagebox.showwarning("Warning", "Export completed, but file could not be verified.")
            
        except PermissionError:
            messagebox.showerror("Error", f"Permission denied. Cannot write to:\n{filename}\n\nFile may be open in another application.")
        except OSError as e:
            messagebox.showerror("Error", f"File system error:\n{e}\n\nPlease check disk space and permissions.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export graph:\n{str(e)}\n\nPlease try again or select a different location.")
    
    def _export_realtime_all_pdf(self):
        """Export all real-time graphs to a single PDF file."""
        try:
            # Generate default filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"RealTime_Graphs_All_{timestamp}.pdf"
            
            # Ask user for save location
            filename = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
                initialfile=default_filename
            )
            
            if not filename:
                return  # User cancelled
            
            # Create a new figure with all graphs
            with PdfPages(filename) as pdf:
                # Save each graph
                graphs = [
                    (self.cpu_fig, "CPU Usage"),
                    (self.memory_fig, "Memory Usage"),
                    (self.disk_fig, "Disk Usage"),
                    (self.network_fig, "Network Usage")
                ]
                
                for fig, name in graphs:
                    # Add export timestamp to title
                    original_title = fig.axes[0].get_title()
                    export_title = f"{original_title} - Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    fig.axes[0].set_title(export_title, fontsize=10)
                    
                    # Save to PDF
                    pdf.savefig(fig, bbox_inches='tight', dpi=300)
                    
                    # Restore original title
                    fig.axes[0].set_title(original_title)
                
                # Add metadata
                d = pdf.infodict()
                d['Title'] = 'Resource Monitor - Real-Time Graphs'
                d['Author'] = 'GUI Resource Monitor'
                d['Subject'] = 'System resource usage graphs'
                d['Keywords'] = 'CPU, Memory, Disk, Network, Monitoring'
                d['CreationDate'] = datetime.now()
            
            messagebox.showinfo("Success", f"All real-time graphs exported successfully to:\n{filename}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export graphs:\n{str(e)}")
    
    def _export_historical_all_pdf(self):
        """Export all historical graphs to a single PDF file."""
        try:
            # Check if historical data is loaded
            if not self.historical_metrics:
                messagebox.showwarning("Warning", "No historical data loaded. Please load data first.")
                return
            
            # Generate default filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"Historical_Graphs_All_{timestamp}.pdf"
            
            # Ask user for save location
            filename = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
                initialfile=default_filename
            )
            
            if not filename:
                return  # User cancelled
            
            # Create a new figure with all graphs
            with PdfPages(filename) as pdf:
                # Save each graph
                graphs = [
                    (self.hist_cpu_fig, "Historical CPU Usage"),
                    (self.hist_memory_fig, "Historical Memory Usage"),
                    (self.hist_disk_fig, "Historical Disk Usage"),
                    (self.hist_network_fig, "Historical Network Usage")
                ]
                
                # Get time range for metadata
                if self.historical_metrics:
                    start_time = self.historical_metrics[0].timestamp
                    end_time = self.historical_metrics[-1].timestamp
                    time_range_str = f"{start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}"
                else:
                    time_range_str = "N/A"
                
                for fig, name in graphs:
                    # Add export timestamp and time range to title
                    original_title = fig.axes[0].get_title()
                    export_title = f"{original_title}\nTime Range: {time_range_str}\nExported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    fig.axes[0].set_title(export_title, fontsize=9)
                    
                    # Save to PDF
                    pdf.savefig(fig, bbox_inches='tight', dpi=300)
                    
                    # Restore original title
                    fig.axes[0].set_title(original_title)
                
                # Add statistics page if available
                if self.historical_metrics:
                    stats_fig = Figure(figsize=(8, 6), dpi=100)
                    stats_ax = stats_fig.add_subplot(111)
                    stats_ax.axis('off')
                    
                    # Calculate statistics
                    cpu_values = [m.cpu_percent for m in self.historical_metrics]
                    memory_values = [m.memory_percent for m in self.historical_metrics]
                    disk_values = [m.disk_percent for m in self.historical_metrics]
                    network_sent = [m.network_sent_rate_mbps for m in self.historical_metrics]
                    network_recv = [m.network_recv_rate_mbps for m in self.historical_metrics]
                    
                    stats_text = f"Resource Monitor - Historical Data Statistics\n"
                    stats_text += f"{'='*60}\n\n"
                    stats_text += f"Time Range: {time_range_str}\n"
                    stats_text += f"Total Records: {len(self.historical_metrics)}\n"
                    stats_text += f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    stats_text += f"{'='*60}\n\n"
                    stats_text += f"CPU Statistics:\n"
                    stats_text += f"  Average: {sum(cpu_values)/len(cpu_values):.2f}%\n"
                    stats_text += f"  Minimum: {min(cpu_values):.2f}%\n"
                    stats_text += f"  Maximum: {max(cpu_values):.2f}%\n\n"
                    stats_text += f"Memory Statistics:\n"
                    stats_text += f"  Average: {sum(memory_values)/len(memory_values):.2f}%\n"
                    stats_text += f"  Minimum: {min(memory_values):.2f}%\n"
                    stats_text += f"  Maximum: {max(memory_values):.2f}%\n\n"
                    stats_text += f"Disk Statistics:\n"
                    stats_text += f"  Average: {sum(disk_values)/len(disk_values):.2f}%\n"
                    stats_text += f"  Minimum: {min(disk_values):.2f}%\n"
                    stats_text += f"  Maximum: {max(disk_values):.2f}%\n\n"
                    stats_text += f"Network Statistics:\n"
                    stats_text += f"  Sent - Average: {sum(network_sent)/len(network_sent):.2f} Mbps, Max: {max(network_sent):.2f} Mbps\n"
                    stats_text += f"  Received - Average: {sum(network_recv)/len(network_recv):.2f} Mbps, Max: {max(network_recv):.2f} Mbps\n"
                    
                    stats_ax.text(0.1, 0.9, stats_text, transform=stats_ax.transAxes,
                                 fontsize=10, verticalalignment='top', fontfamily='monospace',
                                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
                    
                    pdf.savefig(stats_fig, bbox_inches='tight')
                
                # Add metadata
                d = pdf.infodict()
                d['Title'] = 'Resource Monitor - Historical Graphs'
                d['Author'] = 'GUI Resource Monitor'
                d['Subject'] = 'Historical system resource usage graphs'
                d['Keywords'] = 'CPU, Memory, Disk, Network, Historical Data, Monitoring'
                d['CreationDate'] = datetime.now()
            
            messagebox.showinfo("Success", f"All historical graphs exported successfully to:\n{filename}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export graphs:\n{str(e)}")
    
    def _update_graphs(self, metrics: ResourceMetrics):
        """Update all graphs with new data - optimized to avoid unnecessary redraws."""
        try:
            # Add new data point
            self.time_data.append(metrics.timestamp)
            self.cpu_data.append(metrics.cpu_percent)
            self.memory_data.append(metrics.memory_percent)
            self.disk_data.append(metrics.disk_percent)
            self.network_sent_data.append(metrics.network_sent_rate_mbps)
            self.network_recv_data.append(metrics.network_recv_rate_mbps)
            
            # Keep only last N data points (use deque-like approach for better performance)
            if len(self.time_data) > self.max_data_points:
                self.time_data = self.time_data[-self.max_data_points:]
                self.cpu_data = self.cpu_data[-self.max_data_points:]
                self.memory_data = self.memory_data[-self.max_data_points:]
                self.disk_data = self.disk_data[-self.max_data_points:]
                self.network_sent_data = self.network_sent_data[-self.max_data_points:]
                self.network_recv_data = self.network_recv_data[-self.max_data_points:]
            
            # Only update labels periodically to reduce overhead
            data_length = len(self.time_data)
            if data_length == 0:
                return
            
            # Format time labels only when needed (every 5 updates or when length changes significantly)
            update_labels = (data_length % 5 == 0) or (data_length < 10)
            if update_labels:
                time_labels = [t.strftime('%H:%M:%S') for t in self.time_data]
                step = max(1, len(time_labels) // 10)
            
            # Update CPU graph
            indices = list(range(data_length))
            self.cpu_line.set_data(indices, self.cpu_data)
            self.cpu_ax.set_xlim(-0.5, data_length - 0.5 if data_length > 1 else 1.5)
            if update_labels and data_length > 0:
                self.cpu_ax.set_xticks(indices[::step] if step > 0 else indices)
                self.cpu_ax.set_xticklabels([time_labels[i] for i in indices[::step] if i < len(time_labels)], rotation=45)
            self.cpu_canvas.draw_idle()  # Use draw_idle instead of draw for better performance
            
            # Update Memory graph
            self.memory_line.set_data(indices, self.memory_data)
            self.memory_ax.set_xlim(-0.5, data_length - 0.5 if data_length > 1 else 1.5)
            if update_labels and data_length > 0:
                self.memory_ax.set_xticks(indices[::step] if step > 0 else indices)
                self.memory_ax.set_xticklabels([time_labels[i] for i in indices[::step] if i < len(time_labels)], rotation=45)
            self.memory_canvas.draw_idle()
            
            # Update Disk graph
            self.disk_line.set_data(indices, self.disk_data)
            self.disk_ax.set_xlim(-0.5, data_length - 0.5 if data_length > 1 else 1.5)
            if update_labels and data_length > 0:
                self.disk_ax.set_xticks(indices[::step] if step > 0 else indices)
                self.disk_ax.set_xticklabels([time_labels[i] for i in indices[::step] if i < len(time_labels)], rotation=45)
            self.disk_canvas.draw_idle()
            
            # Update Network graph
            max_network = max(
                max(self.network_sent_data) if self.network_sent_data else 0,
                max(self.network_recv_data) if self.network_recv_data else 0,
                1
            )
            # Only update ylim if it changed significantly (avoid unnecessary updates)
            current_ylim = self.network_ax.get_ylim()
            new_ylim = (0, max_network * 1.1)
            if abs(current_ylim[1] - new_ylim[1]) > new_ylim[1] * 0.1:  # 10% change threshold
                self.network_ax.set_ylim(new_ylim)
            
            self.network_sent_line.set_data(indices, self.network_sent_data)
            self.network_recv_line.set_data(indices, self.network_recv_data)
            self.network_ax.set_xlim(-0.5, data_length - 0.5 if data_length > 1 else 1.5)
            if update_labels and data_length > 0:
                self.network_ax.set_xticks(indices[::step] if step > 0 else indices)
                self.network_ax.set_xticklabels([time_labels[i] for i in indices[::step] if i < len(time_labels)], rotation=45)
            self.network_canvas.draw_idle()
            
        except Exception as e:
            # Log error but don't crash - just update status
            self.status_label.config(text=f"Status: Error updating graphs - {str(e)[:50]}")
    
    def _update_statistics(self, metrics: ResourceMetrics):
        """Update statistics display with current values."""
        # CPU
        self.cpu_percent_label.config(text=f"Usage: {metrics.cpu_percent:.2f}%")
        
        # Memory
        self.memory_percent_label.config(text=f"Usage: {metrics.memory_percent:.2f}%")
        self.memory_details_label.config(
            text=f"Used: {metrics.memory_used_mb:.0f} MB / Total: {metrics.memory_total_mb:.0f} MB"
        )
        
        # Disk
        self.disk_percent_label.config(text=f"Usage: {metrics.disk_percent:.2f}%")
        self.disk_details_label.config(
            text=f"Used: {metrics.disk_used_gb:.2f} GB / Total: {metrics.disk_total_gb:.2f} GB"
        )
        
        # Network
        self.network_sent_label.config(
            text=f"Sent: {metrics.network_sent_mb:.2f} MB (Rate: {metrics.network_sent_rate_mbps:.2f} Mbps)"
        )
        self.network_recv_label.config(
            text=f"Received: {metrics.network_recv_mb:.2f} MB (Rate: {metrics.network_recv_rate_mbps:.2f} Mbps)"
        )
        
        # Timestamp
        self.timestamp_label.config(
            text=f"Last Update: {metrics.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        )
    
    def _update_gui(self):
        """Main GUI update loop - called periodically."""
        try:
            latest_metrics = self.collector.get_latest_metrics()
            
            if latest_metrics:
                # Update graphs
                self._update_graphs(latest_metrics)
                
                # Update statistics
                self._update_statistics(latest_metrics)
                
                # Update status with performance info
                total_metrics = self.collector.get_history_count()
                db_stats = self.db_storage.get_statistics()
                db_count = db_stats.get('total_records', 0)
                
                self.status_label.config(
                    text=f"Status: Running | Memory Metrics: {total_metrics} | "
                         f"DB Records: {db_count:,} | Graph Points: {len(self.time_data)}/{self.max_data_points}"
                )
            else:
                self.status_label.config(text="Status: Waiting for data...")
        except Exception as e:
            self.status_label.config(text=f"Status: Error - {str(e)[:50]}")
        
        # Schedule next update
        self.root.after(self.update_interval, self._update_gui)
    
    def on_closing(self):
        """Handle window closing event."""
        self.collector.stop_collection()
        self.root.destroy()


def main():
    """Main entry point for Phase 2 GUI application with Phase 3 database storage."""
    # Create resource collector with database storage enabled
    collector = ResourceCollector(
        collection_interval=1.0,
        enable_database_storage=True,  # Enable automatic database storage
        db_path="resource_monitor.db"
    )
    
    # Start collecting
    collector.start_collection()
    
    # Create GUI
    root = tk.Tk()
    app = ResourceMonitorGUI(root, collector, update_interval=1000, db_path="resource_monitor.db")
    
    # Handle window closing
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # Start GUI main loop
    root.mainloop()


if __name__ == "__main__":
    main()

