"""Monitoring and metrics for medical chatbot"""

import time
from collections import defaultdict
from datetime import datetime
from typing import Dict, Optional

from loguru import logger


class MetricsCollector:
    """Collect and track metrics for the chatbot"""

    def __init__(self):
        """Initialize metrics collector"""
        self.request_count = 0
        self.error_count = 0
        self.total_response_time = 0.0
        self.start_time = datetime.now()
        self.response_times = []
        self.endpoint_metrics = defaultdict(lambda: {"count": 0, "errors": 0, "total_time": 0.0})

    def record_request(self, endpoint: str, response_time: float, error: bool = False):
        """Record a request metric

        Args:
            endpoint: API endpoint name
            response_time: Time taken to process request in seconds
            error: Whether the request resulted in an error
        """
        self.request_count += 1
        self.total_response_time += response_time
        self.response_times.append(response_time)

        if error:
            self.error_count += 1
            self.endpoint_metrics[endpoint]["errors"] += 1

        self.endpoint_metrics[endpoint]["count"] += 1
        self.endpoint_metrics[endpoint]["total_time"] += response_time

        # Keep only last 1000 response times to avoid memory bloat
        if len(self.response_times) > 1000:
            self.response_times = self.response_times[-1000:]

    def get_metrics(self) -> Dict:
        """Get current metrics

        Returns:
            Dictionary of metrics
        """
        uptime = (datetime.now() - self.start_time).total_seconds()
        avg_response_time = (
            self.total_response_time / self.request_count if self.request_count > 0 else 0
        )

        metrics = {
            "uptime_seconds": uptime,
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate": self.error_count / self.request_count if self.request_count > 0 else 0,
            "avg_response_time": avg_response_time,
            "requests_per_second": self.request_count / uptime if uptime > 0 else 0,
            "endpoint_metrics": dict(self.endpoint_metrics),
        }

        # Calculate percentiles if we have data
        if self.response_times:
            sorted_times = sorted(self.response_times)
            n = len(sorted_times)
            metrics["p50_response_time"] = sorted_times[int(n * 0.5)]
            metrics["p95_response_time"] = sorted_times[int(n * 0.95)]
            metrics["p99_response_time"] = sorted_times[int(n * 0.99)]

        return metrics

    def log_metrics(self):
        """Log current metrics"""
        metrics = self.get_metrics()
        logger.info(
            f"Metrics - Requests: {metrics['total_requests']}, "
            f"Errors: {metrics['total_errors']}, "
            f"Avg Response Time: {metrics['avg_response_time']:.3f}s, "
            f"Error Rate: {metrics['error_rate']:.2%}"
        )


# Global metrics collector instance
metrics_collector = MetricsCollector()


class RequestTimer:
    """Context manager for timing requests"""

    def __init__(self, endpoint: str, metrics: Optional[MetricsCollector] = None):
        """Initialize request timer

        Args:
            endpoint: Name of the endpoint being timed
            metrics: Metrics collector to use (defaults to global)
        """
        self.endpoint = endpoint
        self.metrics = metrics or metrics_collector
        self.start_time = None
        self.error = False

    def __enter__(self):
        """Start timer"""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timer and record metrics"""
        if self.start_time:
            elapsed = time.time() - self.start_time
            self.error = exc_type is not None
            self.metrics.record_request(self.endpoint, elapsed, self.error)

        return False  # Don't suppress exceptions


def get_health_status() -> Dict:
    """Get health status of the service

    Returns:
        Dictionary with health status information
    """
    metrics = metrics_collector.get_metrics()

    # Determine health status
    is_healthy = True
    warnings = []

    # Check error rate
    if metrics.get("error_rate", 0) > 0.1:  # More than 10% errors
        is_healthy = False
        warnings.append("High error rate")

    # Check response time
    if metrics.get("avg_response_time", 0) > 10.0:  # More than 10 seconds
        warnings.append("Slow response times")

    status = {
        "healthy": is_healthy,
        "status": "healthy" if is_healthy else "degraded",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": metrics.get("uptime_seconds", 0),
        "total_requests": metrics.get("total_requests", 0),
        "warnings": warnings,
    }

    return status
