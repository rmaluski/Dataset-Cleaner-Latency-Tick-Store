"""
Metrics collection component for the data lake.
"""

import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Summary,
    generate_latest,
    start_http_server,
)

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Metrics collection component for the data lake.
    
    This class provides:
    - Prometheus metrics for monitoring
    - Performance tracking
    - Error rate monitoring
    - Throughput metrics
    - Query latency tracking
    """
    
    def __init__(self, port: int = 8000):
        """
        Initialize metrics collector.
        
        Args:
            port: Port for Prometheus metrics server
        """
        self.port = port
        
        # Initialize Prometheus metrics
        self._init_prometheus_metrics()
        
        # Start metrics server
        try:
            start_http_server(port)
            logger.info(f"Prometheus metrics server started on port {port}")
        except Exception as e:
            logger.warning(f"Failed to start metrics server: {e}")
        
        # In-memory metrics for quick access
        self._metrics = defaultdict(dict)
        self._start_time = datetime.now()
        
        logger.info("Metrics collector initialized")
    
    def _init_prometheus_metrics(self) -> None:
        """Initialize Prometheus metrics."""
        
        # Counters
        self.ingest_total = Counter(
            "tickdb_ingest_total",
            "Total number of ingest operations",
            ["source_id", "schema_id", "status"]
        )
        
        self.ingest_bytes_total = Counter(
            "tickdb_ingest_bytes_total",
            "Total bytes ingested",
            ["source_id", "schema_id"]
        )
        
        self.ingest_rows_total = Counter(
            "tickdb_ingest_rows_total",
            "Total rows ingested",
            ["source_id", "schema_id", "status"]
        )
        
        self.query_total = Counter(
            "tickdb_query_total",
            "Total number of queries",
            ["schema_id", "status"]
        )
        
        self.query_rows_total = Counter(
            "tickdb_query_rows_total",
            "Total rows returned by queries",
            ["schema_id"]
        )
        
        self.validation_errors_total = Counter(
            "tickdb_validation_errors_total",
            "Total validation errors",
            ["schema_id", "error_type"]
        )
        
        # Gauges
        self.active_connections = Gauge(
            "tickdb_active_connections",
            "Number of active database connections"
        )
        
        self.data_lake_size_bytes = Gauge(
            "tickdb_data_lake_size_bytes",
            "Total size of data lake in bytes",
            ["schema_id"]
        )
        
        self.data_lake_files = Gauge(
            "tickdb_data_lake_files",
            "Number of files in data lake",
            ["schema_id"]
        )
        
        self.quarantine_size_bytes = Gauge(
            "tickdb_quarantine_size_bytes",
            "Total size of quarantine in bytes"
        )
        
        self.quarantine_files = Gauge(
            "tickdb_quarantine_files",
            "Number of files in quarantine"
        )
        
        # Histograms
        self.ingest_duration_seconds = Histogram(
            "tickdb_ingest_duration_seconds",
            "Time spent on ingest operations",
            ["source_id", "schema_id"],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
        )
        
        self.query_duration_seconds = Histogram(
            "tickdb_query_duration_seconds",
            "Time spent on query operations",
            ["schema_id"],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
        )
        
        self.validation_duration_seconds = Histogram(
            "tickdb_validation_duration_seconds",
            "Time spent on validation operations",
            ["schema_id"],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
        )
        
        # Summaries
        self.ingest_throughput_mbps = Summary(
            "tickdb_ingest_throughput_mbps",
            "Ingest throughput in MB/s",
            ["source_id", "schema_id"]
        )
        
        self.query_latency_ms = Summary(
            "tickdb_query_latency_ms",
            "Query latency in milliseconds",
            ["schema_id"]
        )
    
    def record_ingest(
        self,
        source_id: str,
        bytes_processed: int,
        rows_processed: int,
        rows_failed: int,
        schema_id: str = "unknown",
        duration_seconds: Optional[float] = None
    ) -> None:
        """
        Record ingest metrics.
        
        Args:
            source_id: Data source identifier
            bytes_processed: Number of bytes processed
            rows_processed: Number of rows processed successfully
            rows_failed: Number of rows that failed
            schema_id: Schema identifier
            duration_seconds: Duration of ingest operation
        """
        # Update Prometheus metrics
        self.ingest_total.labels(
            source_id=source_id,
            schema_id=schema_id,
            status="success"
        ).inc()
        
        if rows_failed > 0:
            self.ingest_total.labels(
                source_id=source_id,
                schema_id=schema_id,
                status="failed"
            ).inc(rows_failed)
        
        self.ingest_bytes_total.labels(
            source_id=source_id,
            schema_id=schema_id
        ).inc(bytes_processed)
        
        self.ingest_rows_total.labels(
            source_id=source_id,
            schema_id=schema_id,
            status="success"
        ).inc(rows_processed)
        
        if rows_failed > 0:
            self.ingest_rows_total.labels(
                source_id=source_id,
                schema_id=schema_id,
                status="failed"
            ).inc(rows_failed)
        
        if duration_seconds:
            self.ingest_duration_seconds.labels(
                source_id=source_id,
                schema_id=schema_id
            ).observe(duration_seconds)
            
            # Calculate throughput
            throughput_mbps = (bytes_processed / (1024 * 1024)) / duration_seconds
            self.ingest_throughput_mbps.labels(
                source_id=source_id,
                schema_id=schema_id
            ).observe(throughput_mbps)
        
        # Update in-memory metrics
        key = f"ingest_{source_id}_{schema_id}"
        if key not in self._metrics:
            self._metrics[key] = {
                "total_bytes": 0,
                "total_rows": 0,
                "failed_rows": 0,
                "total_duration": 0.0,
                "count": 0
            }
        
        self._metrics[key]["total_bytes"] += bytes_processed
        self._metrics[key]["total_rows"] += rows_processed
        self._metrics[key]["failed_rows"] += rows_failed
        if duration_seconds:
            self._metrics[key]["total_duration"] += duration_seconds
        self._metrics[key]["count"] += 1
        
        logger.debug("Recorded ingest metrics", extra={
            "source_id": source_id,
            "schema_id": schema_id,
            "bytes_processed": bytes_processed,
            "rows_processed": rows_processed,
            "rows_failed": rows_failed,
            "duration_seconds": duration_seconds
        })
    
    def record_append(
        self,
        schema_id: str,
        rows_processed: int,
        rows_failed: int,
        duration_seconds: Optional[float] = None
    ) -> None:
        """
        Record append metrics.
        
        Args:
            schema_id: Schema identifier
            rows_processed: Number of rows processed successfully
            rows_failed: Number of rows that failed
            duration_seconds: Duration of append operation
        """
        # Update Prometheus metrics
        self.ingest_total.labels(
            source_id="append",
            schema_id=schema_id,
            status="success"
        ).inc()
        
        if rows_failed > 0:
            self.ingest_total.labels(
                source_id="append",
                schema_id=schema_id,
                status="failed"
            ).inc(rows_failed)
        
        self.ingest_rows_total.labels(
            source_id="append",
            schema_id=schema_id,
            status="success"
        ).inc(rows_processed)
        
        if rows_failed > 0:
            self.ingest_rows_total.labels(
                source_id="append",
                schema_id=schema_id,
                status="failed"
            ).inc(rows_failed)
        
        if duration_seconds:
            self.ingest_duration_seconds.labels(
                source_id="append",
                schema_id=schema_id
            ).observe(duration_seconds)
        
        logger.debug("Recorded append metrics", extra={
            "schema_id": schema_id,
            "rows_processed": rows_processed,
            "rows_failed": rows_failed,
            "duration_seconds": duration_seconds
        })
    
    def record_query(
        self,
        query_time_ms: float,
        rows_returned: int,
        schema_id: str = "unknown",
        status: str = "success"
    ) -> None:
        """
        Record query metrics.
        
        Args:
            query_time_ms: Query execution time in milliseconds
            rows_returned: Number of rows returned
            schema_id: Schema identifier
            status: Query status (success/failed)
        """
        # Update Prometheus metrics
        self.query_total.labels(
            schema_id=schema_id,
            status=status
        ).inc()
        
        if status == "success":
            self.query_rows_total.labels(
                schema_id=schema_id
            ).inc(rows_returned)
        
        self.query_duration_seconds.labels(
            schema_id=schema_id
        ).observe(query_time_ms / 1000.0)
        
        self.query_latency_ms.labels(
            schema_id=schema_id
        ).observe(query_time_ms)
        
        # Update in-memory metrics
        key = f"query_{schema_id}"
        if key not in self._metrics:
            self._metrics[key] = {
                "total_queries": 0,
                "total_rows": 0,
                "total_time_ms": 0.0,
                "avg_latency_ms": 0.0
            }
        
        self._metrics[key]["total_queries"] += 1
        self._metrics[key]["total_rows"] += rows_returned
        self._metrics[key]["total_time_ms"] += query_time_ms
        self._metrics[key]["avg_latency_ms"] = (
            self._metrics[key]["total_time_ms"] / self._metrics[key]["total_queries"]
        )
        
        logger.debug("Recorded query metrics", extra={
            "schema_id": schema_id,
            "query_time_ms": query_time_ms,
            "rows_returned": rows_returned,
            "status": status
        })
    
    def record_validation(
        self,
        schema_id: str,
        rows_checked: int,
        rows_failed: int,
        validation_time_ms: float,
        error_types: Optional[List[str]] = None
    ) -> None:
        """
        Record validation metrics.
        
        Args:
            schema_id: Schema identifier
            rows_checked: Number of rows checked
            rows_failed: Number of rows that failed validation
            validation_time_ms: Validation time in milliseconds
            error_types: List of error types encountered
        """
        # Update Prometheus metrics
        self.validation_duration_seconds.labels(
            schema_id=schema_id
        ).observe(validation_time_ms / 1000.0)
        
        if error_types:
            for error_type in error_types:
                self.validation_errors_total.labels(
                    schema_id=schema_id,
                    error_type=error_type
                ).inc()
        
        # Update in-memory metrics
        key = f"validation_{schema_id}"
        if key not in self._metrics:
            self._metrics[key] = {
                "total_rows_checked": 0,
                "total_rows_failed": 0,
                "total_time_ms": 0.0,
                "error_types": defaultdict(int)
            }
        
        self._metrics[key]["total_rows_checked"] += rows_checked
        self._metrics[key]["total_rows_failed"] += rows_failed
        self._metrics[key]["total_time_ms"] += validation_time_ms
        
        if error_types:
            for error_type in error_types:
                self._metrics[key]["error_types"][error_type] += 1
        
        logger.debug("Recorded validation metrics", extra={
            "schema_id": schema_id,
            "rows_checked": rows_checked,
            "rows_failed": rows_failed,
            "validation_time_ms": validation_time_ms,
            "error_types": error_types
        })
    
    def update_data_lake_metrics(
        self,
        schema_id: str,
        total_size_bytes: int,
        file_count: int
    ) -> None:
        """
        Update data lake size metrics.
        
        Args:
            schema_id: Schema identifier
            total_size_bytes: Total size in bytes
            file_count: Number of files
        """
        self.data_lake_size_bytes.labels(
            schema_id=schema_id
        ).set(total_size_bytes)
        
        self.data_lake_files.labels(
            schema_id=schema_id
        ).set(file_count)
        
        logger.debug("Updated data lake metrics", extra={
            "schema_id": schema_id,
            "total_size_bytes": total_size_bytes,
            "file_count": file_count
        })
    
    def update_quarantine_metrics(
        self,
        total_size_bytes: int,
        file_count: int
    ) -> None:
        """
        Update quarantine metrics.
        
        Args:
            total_size_bytes: Total size in bytes
            file_count: Number of files
        """
        self.quarantine_size_bytes.set(total_size_bytes)
        self.quarantine_files.set(file_count)
        
        logger.debug("Updated quarantine metrics", extra={
            "total_size_bytes": total_size_bytes,
            "file_count": file_count
        })
    
    def set_active_connections(self, count: int) -> None:
        """Set number of active connections."""
        self.active_connections.set(count)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics summary."""
        uptime = datetime.now() - self._start_time
        
        summary = {
            "uptime_seconds": uptime.total_seconds(),
            "start_time": self._start_time.isoformat(),
            "prometheus_endpoint": f"http://localhost:{self.port}/metrics",
            "metrics": dict(self._metrics)
        }
        
        # Calculate aggregate statistics
        total_ingest_bytes = 0
        total_ingest_rows = 0
        total_queries = 0
        total_query_rows = 0
        
        for key, metrics in self._metrics.items():
            if key.startswith("ingest_"):
                total_ingest_bytes += metrics.get("total_bytes", 0)
                total_ingest_rows += metrics.get("total_rows", 0)
            elif key.startswith("query_"):
                total_queries += metrics.get("total_queries", 0)
                total_query_rows += metrics.get("total_rows", 0)
        
        summary["aggregates"] = {
            "total_ingest_bytes": total_ingest_bytes,
            "total_ingest_rows": total_ingest_rows,
            "total_queries": total_queries,
            "total_query_rows": total_query_rows,
            "avg_ingest_throughput_mbps": (
                (total_ingest_bytes / (1024 * 1024)) / uptime.total_seconds()
                if uptime.total_seconds() > 0 else 0
            )
        }
        
        return summary
    
    def get_prometheus_metrics(self) -> str:
        """Get Prometheus metrics as string."""
        return generate_latest().decode("utf-8")
    
    def reset_metrics(self) -> None:
        """Reset all metrics."""
        self._metrics.clear()
        self._start_time = datetime.now()
        logger.info("Metrics reset") 