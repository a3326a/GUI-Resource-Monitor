"""
Phase 2: GUI Design and Real-Time Display
Creates a GUI to display live resource usage with graphs and statistics.
"""

import tkinter as tk
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import List
from resource_collector import ResourceCollector, ResourceMetrics


class ResourceMonitorGUI:
    """
    GUI application for real-time resource monitoring with live graphs.
    """
    
    def __init__(self, root: tk.Tk, collector: ResourceCollector, update_interval: int = 1000):
        """
        Initialize the GUI.
        
        Args:
            root: Tkinter root window
            collector: ResourceCollector instance
            update_interval: GUI update interval in milliseconds (default: 1000ms = 1 second)
        """
        self.root = root
        self.collector = collector
        self.update_interval = update_interval
        
        # Configure window
        self.root.title("GUI Resource Monitor - Real-Time Display")
        self.root.geometry("1200x800")
        self.root.configure(bg='#f0f0f0')
        
        # Data storage for graphs (keep last 60 data points)
        self.max_data_points = 60
        self.time_data: List[datetime] = []
        self.cpu_data: List[float] = []
        self.memory_data: List[float] = []
        self.disk_data: List[float] = []
        self.network_sent_data: List[float] = []
        self.network_recv_data: List[float] = []
        
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
        main_frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = tk.Label(
            main_frame,
            text="System Resource Monitor",
            font=("Arial", 18, "bold"),
            bg='#f0f0f0'
        )
        title_label.grid(row=0, column=0, pady=(0, 10))
        
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
        
        # Status bar
        self.status_label = tk.Label(
            main_frame,
            text="Status: Initializing...",
            font=("Arial", 9),
            bg='#f0f0f0',
            anchor=tk.W
        )
        self.status_label.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
    
    def _create_graphs_tab(self, parent):
        """Create the graphs tab with real-time charts."""
        # Configure grid
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        
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
    
    def _update_graphs(self, metrics: ResourceMetrics):
        """Update all graphs with new data."""
        # Add new data point
        self.time_data.append(metrics.timestamp)
        self.cpu_data.append(metrics.cpu_percent)
        self.memory_data.append(metrics.memory_percent)
        self.disk_data.append(metrics.disk_percent)
        self.network_sent_data.append(metrics.network_sent_rate_mbps)
        self.network_recv_data.append(metrics.network_recv_rate_mbps)
        
        # Keep only last N data points
        if len(self.time_data) > self.max_data_points:
            self.time_data.pop(0)
            self.cpu_data.pop(0)
            self.memory_data.pop(0)
            self.disk_data.pop(0)
            self.network_sent_data.pop(0)
            self.network_recv_data.pop(0)
        
        # Format time labels (show only time, not date)
        time_labels = [t.strftime('%H:%M:%S') for t in self.time_data]
        
        # Update CPU graph
        self.cpu_line.set_data(range(len(self.cpu_data)), self.cpu_data)
        self.cpu_ax.set_xlim(0, len(self.cpu_data) - 1 if len(self.cpu_data) > 1 else 1)
        if len(self.time_data) > 0:
            # Show only some labels to avoid crowding
            step = max(1, len(time_labels) // 10)
            self.cpu_ax.set_xticks(range(0, len(time_labels), step))
            self.cpu_ax.set_xticklabels([time_labels[i] for i in range(0, len(time_labels), step)], rotation=45)
        self.cpu_canvas.draw()
        
        # Update Memory graph
        self.memory_line.set_data(range(len(self.memory_data)), self.memory_data)
        self.memory_ax.set_xlim(0, len(self.memory_data) - 1 if len(self.memory_data) > 1 else 1)
        if len(self.time_data) > 0:
            step = max(1, len(time_labels) // 10)
            self.memory_ax.set_xticks(range(0, len(time_labels), step))
            self.memory_ax.set_xticklabels([time_labels[i] for i in range(0, len(time_labels), step)], rotation=45)
        self.memory_canvas.draw()
        
        # Update Disk graph
        self.disk_line.set_data(range(len(self.disk_data)), self.disk_data)
        self.disk_ax.set_xlim(0, len(self.disk_data) - 1 if len(self.disk_data) > 1 else 1)
        if len(self.time_data) > 0:
            step = max(1, len(time_labels) // 10)
            self.disk_ax.set_xticks(range(0, len(time_labels), step))
            self.disk_ax.set_xticklabels([time_labels[i] for i in range(0, len(time_labels), step)], rotation=45)
        self.disk_canvas.draw()
        
        # Update Network graph
        max_network = max(max(self.network_sent_data) if self.network_sent_data else 0,
                         max(self.network_recv_data) if self.network_recv_data else 0, 1)
        self.network_ax.set_ylim(0, max_network * 1.1)
        self.network_sent_line.set_data(range(len(self.network_sent_data)), self.network_sent_data)
        self.network_recv_line.set_data(range(len(self.network_recv_data)), self.network_recv_data)
        self.network_ax.set_xlim(0, len(self.network_sent_data) - 1 if len(self.network_sent_data) > 1 else 1)
        if len(self.time_data) > 0:
            step = max(1, len(time_labels) // 10)
            self.network_ax.set_xticks(range(0, len(time_labels), step))
            self.network_ax.set_xticklabels([time_labels[i] for i in range(0, len(time_labels), step)], rotation=45)
        self.network_canvas.draw()
    
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
        latest_metrics = self.collector.get_latest_metrics()
        
        if latest_metrics:
            # Update graphs
            self._update_graphs(latest_metrics)
            
            # Update statistics
            self._update_statistics(latest_metrics)
            
            # Update status
            total_metrics = self.collector.get_history_count()
            self.status_label.config(
                text=f"Status: Running | Metrics Collected: {total_metrics} | "
                     f"Data Points in Graphs: {len(self.time_data)}"
            )
        else:
            self.status_label.config(text="Status: Waiting for data...")
        
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
    app = ResourceMonitorGUI(root, collector, update_interval=1000)
    
    # Handle window closing
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # Start GUI main loop
    root.mainloop()


if __name__ == "__main__":
    main()

