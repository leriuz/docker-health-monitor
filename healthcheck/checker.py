"""Health check runner — polls endpoints and records results."""

import argparse
import logging
import time

import requests

from config_loader import Config, Endpoint, load_config
from db import init_db, insert_result, get_consecutive_failures
from notifier import send_alert

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def check_endpoint(endpoint: Endpoint) -> dict:
    """Perform a single health check against an endpoint.

    Returns:
        Dict with keys: status, status_code, response_time_ms, error_message
    """
    try:
        response = requests.request(
            method=endpoint.method,
            url=endpoint.url,
            headers=endpoint.headers,
            json=endpoint.body if endpoint.body else None,
            timeout=endpoint.timeout,
        )

        response_time_ms = response.elapsed.total_seconds() * 1000

        if response.status_code == endpoint.expected_status:
            status = "UP"
        else:
            status = "DEGRADED"

        return {
            "status": status,
            "status_code": response.status_code,
            "response_time_ms": round(response_time_ms, 2),
            "error_message": None if status == "UP" else f"Expected {endpoint.expected_status}, got {response.status_code}",
        }

    except requests.Timeout:
        return {
            "status": "DOWN",
            "status_code": None,
            "response_time_ms": endpoint.timeout * 1000,
            "error_message": f"Timeout after {endpoint.timeout}s",
        }

    except requests.ConnectionError as exc:
        return {
            "status": "DOWN",
            "status_code": None,
            "response_time_ms": None,
            "error_message": f"Connection error: {str(exc)[:200]}",
        }

    except requests.RequestException as exc:
        return {
            "status": "DOWN",
            "status_code": None,
            "response_time_ms": None,
            "error_message": str(exc)[:200],
        }


def run_checks(config: Config) -> None:
    """Execute one round of health checks for all endpoints."""
    for endpoint in config.endpoints:
        result = check_endpoint(endpoint)
        status_icon = {"UP": "✅", "DEGRADED": "⚠️", "DOWN": "❌"}.get(result["status"], "?")

        logger.info(
            f"{status_icon} {endpoint.name:<25} "
            f"status={result['status']:<8} "
            f"code={result['status_code'] or '---':<4} "
            f"time={result['response_time_ms'] or '---'}ms"
        )

        insert_result(
            endpoint_name=endpoint.name,
            url=endpoint.url,
            status=result["status"],
            status_code=result["status_code"],
            response_time_ms=result["response_time_ms"],
            error_message=result["error_message"],
        )

        # Check if we need to alert
        if result["status"] != "UP" and config.alerts.webhook_url:
            failures = get_consecutive_failures(endpoint.name)
            if failures >= config.alerts.consecutive_failures:
                send_alert(
                    webhook_url=config.alerts.webhook_url,
                    endpoint_name=endpoint.name,
                    status=result["status"],
                    consecutive_failures=failures,
                    error_message=result["error_message"],
                )


def main() -> None:
    parser = argparse.ArgumentParser(description="Health Check Service")
    parser.add_argument("--config", default="/app/config.yaml", help="Path to config file")
    args = parser.parse_args()

    config = load_config(args.config)
    init_db()

    logger.info(f"Monitoring {len(config.endpoints)} endpoint(s) every {config.check_interval}s")

    while True:
        run_checks(config)
        time.sleep(config.check_interval)


if __name__ == "__main__":
    main()
