# grafana_logger.py - Updated with function-based sanitization
import json
import time
import aiohttp
import os
import base64
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import re


@dataclass
class LogEntry:
    timestamp: str
    method: str
    path: str
    headers: Dict[str, str]
    body: str
    status_code: int
    processing_time: float
    client_ip: str
    log_level: str
    environment: str
    user_id: Optional[str] = None
    error: Optional[str] = None
    # New error fields for better querying (fields only, not labels)
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    service: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert LogEntry to dictionary for JSON serialization - only detailed fields"""
        result = {
            "timestamp": int(self.timestamp),
            "headers": self.headers,
            "body": self.body,
            "processing_time": self.processing_time,
            "client_ip": self.client_ip,
        }
        if self.error:
            result["error"] = self.error
        if self.error_code:
            result["error_code"] = self.error_code
        if self.error_message:
            result["error_message"] = self.error_message
        if self.service:
            result["service"] = self.service

        return result

    def get_labels(self) -> Dict[str, str]:
        """Get Loki labels for this log entry - only fields needed for querying"""
        labels = {
            "job": f"zuum-{self.environment}",
            "method": self.method,
            "path": self._normalize_path(self.path),
            "status_code": str(self.status_code),
            "level": self.log_level,
        }

        labels["user_id"] = self.user_id or "null"
        labels["has_error"] = "true" if self.error else "false"

        return labels

    @classmethod
    def _extract_tracking_properties(
        cls,
        request,  # FastAPI Request
    ) -> Dict[str, Optional[str]]:
        """
        Extract tracking properties from request data.

        Returns:
            Dict with extracted values or None if not found
        """
        user_id = None

        # TODO: Uncomment this section and updated it to get the correct user_id
        # Whenever we get implemented directly from headers and not by requesting supabase auth everytime
        # if hasattr(request, "headers"):
        #     auth_header = request.headers.get("authorization", "")
        #     if auth_header and "Bearer" in auth_header:
        #         try:
        #             from services.auth_service import auth_service
        #             from fastapi.security import HTTPAuthorizationCredentials

        #             token = auth_header.replace("Bearer ", "").strip()
        #             if token:
        #                 credentials = HTTPAuthorizationCredentials(
        #                     scheme="Bearer", credentials=token
        #                 )
        #                 # Get the actual UUID user_id from auth service
        #                 user_id = await auth_service.get_user_id_from_auth(credentials)
        #         except Exception:
        #             pass

        return {
            "user_id": user_id,
        }

    def _normalize_path(self, path: str) -> str:
        """Normalize paths to reduce cardinality"""
        path = re.sub(r"/\d+", "/[id]", path)
        path = re.sub(r"/[a-f0-9-]{36}", "/[uuid]", path)
        return path

    @classmethod
    def _extract_error_fields(cls, response_body: str, status_code: int, body: str = "") -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Extract error_code, error_message, and service from error responses and application logs"""
        error_code = None
        error_message = None
        service = None

        # Try to extract from response_body first (HTTP API responses)
        if response_body and status_code >= 400:
            try:
                data = json.loads(response_body)
                if isinstance(data, dict):
                    error_code = data.get("code")
                    error_message = data.get("message") or data.get("detail")
                    if error_code or error_message:
                        return error_code, error_message, service
            except (json.JSONDecodeError, TypeError):
                pass

        # Try to extract from body (application logs)
        if body:
            try:
                data = json.loads(body)
                if isinstance(data, dict):
                    # Extract service
                    service = data.get("service")

                    # Direct message extraction
                    if data.get("message"):
                        error_message = data.get("message")

                    # Extract error_type as error_code from data field
                    error_data = data.get("data", {})
                    if isinstance(error_data, dict) and error_data.get("error_type"):
                        error_code = error_data.get("error_type")

                    return error_code, error_message, service
            except (json.JSONDecodeError, TypeError):
                pass

        return None, None, None

    @classmethod
    def _extract_error_details(cls, response_body: str, status_code: int) -> Optional[str]:
        """Extract error details from failed responses - optimized version"""
        if status_code < 400 or not response_body:
            return None

        # Early size check to avoid processing large responses
        if len(response_body) > 1000:  # 1KB limit for error details
            truncated_body = response_body[:1000]
            try:
                # Try to parse truncated JSON
                data = json.loads(truncated_body)
                return json.dumps(data, separators=(",", ":"))  # Compact JSON
            except (json.JSONDecodeError, TypeError):
                return truncated_body + "... [truncated]"

        try:
            # Single JSON parse operation with compact output
            data = json.loads(response_body)
            return json.dumps(data, separators=(",", ":"))  # Compact JSON, no spaces
        except (json.JSONDecodeError, TypeError):
            # Return raw response body, already size-limited
            return response_body

    def to_json(self) -> str:
        """Convert LogEntry directly to JSON string - optimized"""
        # Use compact JSON formatting to reduce payload size
        return json.dumps(self.to_dict(), separators=(",", ":"))


# Sanitization functions
SENSITIVE_KEYWORDS = {"password", "token", "secret", "key", "auth"}


def _sanitize_recursive(data: Any) -> Any:
    """Recursively sanitize data"""
    if isinstance(data, dict):
        return {key: "[REDACTED]" if any(kw in key.lower() for kw in SENSITIVE_KEYWORDS) else _sanitize_recursive(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [_sanitize_recursive(item) for item in data]
    else:
        return data


def sanitize_json(body: str) -> str:
    """Sanitize JSON body - optimized version"""
    try:
        data = json.loads(body)
        sanitized = _sanitize_recursive(data)
        # Use compact JSON to reduce memory usage
        return json.dumps(sanitized, separators=(",", ":"))
    except (json.JSONDecodeError, TypeError):
        return body


def sanitize_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Sanitize sensitive headers"""
    sanitized = {}
    for key, value in headers.items():
        if any(kw in key.lower() for kw in SENSITIVE_KEYWORDS):
            sanitized[key] = "[REDACTED]"
        else:
            sanitized[key] = value
    return sanitized


class GrafanaCloudLogger:
    def __init__(
        self,
        loki_url: str,
        username: str,
        api_key: str,
        environment: str,
        batch_size: int = 100,
        flush_interval: int = 5,
    ):
        if not loki_url or not username or not api_key or not environment:
            raise Exception("Missing required environment variables for Grafana Cloud Logger")

        self.loki_url = loki_url
        self.username = username
        self.api_key = api_key
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.environment = environment

        # Setup Python logger
        self.logger = logging.getLogger("grafana_logger")

        # Create auth header
        credentials = f"{username}:{api_key}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        self.headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json",
        }

        # Batch storage
        self.log_batch: List[LogEntry] = []
        self.last_flush = time.time()
        self._session = None

    def get_log_level(self, status_code: int) -> str:
        """Determine log level based on HTTP status code"""
        if 200 <= status_code <= 399:
            return "info"  # 2xx, 3xx = Success/Redirection
        elif 400 <= status_code <= 499:
            return "warning"  # 4xx = Client errors
        else:  # 500+
            return "error"  # 5xx = Server errors

    async def get_session(self):
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def add_log(self, log_entry: LogEntry):
        """Add log entry to batch and log locally"""

        # Log to Python logger based on level
        log_message = f"{log_entry.method} {log_entry.path} - {log_entry.status_code} ({log_entry.processing_time:.3f}s)"

        if log_entry.log_level == "info":
            self.logger.info(log_message)
        elif log_entry.log_level == "warning":
            self.logger.warning(log_message)
        elif log_entry.log_level == "error":
            self.logger.error(log_message)

        # Add to batch for Grafana
        self.log_batch.append(log_entry)

        # Check if we should flush
        if len(self.log_batch) >= self.batch_size or time.time() - self.last_flush > self.flush_interval:
            await self.flush_logs()

    async def flush_logs(self):
        """Send batched logs to Grafana Cloud"""
        if not self.log_batch:
            return

        try:
            # Prepare Loki format
            streams = self._prepare_loki_payload()
            payload = {"streams": streams}

            session = await self.get_session()
            async with session.post(self.loki_url, json=payload, headers=self.headers) as response:
                if response.status != 204:
                    self.logger.error(f"Failed to send logs to Grafana: {response.status} - {await response.text()}")
                else:
                    self.logger.debug(f"Successfully sent {len(self.log_batch)} logs to Grafana Cloud")

            # Clear batch after successful send
            self.log_batch.clear()
            self.last_flush = time.time()

        except Exception as e:
            self.logger.error(f"Error sending logs to Grafana: {e}")

    def _prepare_loki_payload(self) -> List[Dict]:
        """Convert log entries to Loki stream format - eliminates duplication"""
        streams = []

        for log_entry in self.log_batch:
            # log_entry.timestamp is in milliseconds since epoch
            timestamp_ns = str(int(int(log_entry.timestamp) * 1_000_000))

            streams.append(
                {
                    "stream": log_entry.get_labels(),
                    "values": [[timestamp_ns, log_entry.to_json()]],
                }
            )

        return streams

    async def close(self):
        """Cleanup - flush remaining logs and close session"""
        await self.flush_logs()
        if self._session:
            await self._session.close()

    async def log_app_event(
        self,
        service: str,
        operation: str,
        message: str,
        level: str = "info",
        user_id: str = None,
        data: dict = None,
        error: Exception = None,
        duration_ms: float = None,
    ):
        """
        Simple method to log application events using existing LogEntry structure
        """
        # Create a LogEntry that looks like an app event
        timestamp = str(int(time.time() * 1000) / 1000)

        # Format the body as JSON with app-specific data
        body_data = {
            "service": service,
            "operation": operation,
            "message": message,
        }

        if data:
            body_data["data"] = _sanitize_recursive(data)
        if error:
            body_data["error"] = str(error)
        if duration_ms:
            body_data["duration_ms"] = duration_ms

        body = json.dumps(body_data, separators=(",", ":"))

        # Extract error fields using the same function as HTTP requests
        error_code, error_message, extracted_service = LogEntry._extract_error_fields("", 200, body)

        # Create LogEntry with simplified fields for app logs
        log_entry = LogEntry(
            timestamp=timestamp,
            method="APP",  # Indicate this is an app log
            path=f"/{service}/{operation}",
            headers={"log_type": "application"},  # Mark as app log
            body=body,
            status_code=200,
            processing_time=0.0,
            client_ip="app",
            log_level=level,
            environment=self.environment,
            user_id=user_id,
            error=str(error) if error else None,
            error_code=error_code,
            error_message=error_message,
            service=extracted_service,
        )

        # Use existing add_log method - reuses all batching logic!
        await self.add_log(log_entry)

    async def log_info(self, service: str, operation: str, message: str, **kwargs):
        """Log info level application event"""
        await self.log_app_event(service, operation, message, "info", **kwargs)

    async def log_warning(self, service: str, operation: str, message: str, **kwargs):
        """Log warning level application event"""
        await self.log_app_event(service, operation, message, "warning", **kwargs)

    async def log_error(self, service: str, operation: str, message: str, **kwargs):
        """Log error level application event"""
        await self.log_app_event(service, operation, message, "error", **kwargs)


loki_url = os.getenv("GRAFANA_LOKI_URL")
username = os.getenv("GRAFANA_USERNAME")
api_key = os.getenv("GRAFANA_API_KEY")
environment = os.getenv("ENVIRONMENT")

grafana_logger = GrafanaCloudLogger(
    loki_url=loki_url,
    username=username,
    api_key=api_key,
    environment=environment,
    batch_size=50,
    flush_interval=10,
)
