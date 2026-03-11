"""Dashboard web application for viewing health check results."""

import os
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify

app = Flask(__name__)

DB_PATH = os.environ.get("DB_PATH", "/data/checks.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    """Return current status of all endpoints."""
    conn = get_db()
    try:
        # Latest result per endpoint
        latest = conn.execute("""
            SELECT * FROM check_results
            WHERE id IN (
                SELECT MAX(id) FROM check_results GROUP BY endpoint_name
            )
            ORDER BY endpoint_name
        """).fetchall()

        endpoints = []
        for row in latest:
            name = row["endpoint_name"]

            # Uptime (24h)
            cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()
            stats = conn.execute(
                """SELECT COUNT(*) as total,
                          SUM(CASE WHEN status = 'UP' THEN 1 ELSE 0 END) as up_count
                   FROM check_results
                   WHERE endpoint_name = ? AND checked_at >= ?""",
                (name, cutoff),
            ).fetchone()

            total = stats["total"]
            uptime = round((stats["up_count"] / total) * 100, 1) if total > 0 else 0

            # Response time history (last 50)
            history = conn.execute(
                """SELECT response_time_ms, status, checked_at
                   FROM check_results
                   WHERE endpoint_name = ?
                   ORDER BY checked_at DESC LIMIT 50""",
                (name,),
            ).fetchall()

            endpoints.append({
                "name": name,
                "url": row["url"],
                "status": row["status"],
                "status_code": row["status_code"],
                "response_time_ms": row["response_time_ms"],
                "error_message": row["error_message"],
                "checked_at": row["checked_at"],
                "uptime_24h": uptime,
                "history": [
                    {
                        "time": h["checked_at"],
                        "response_ms": h["response_time_ms"],
                        "status": h["status"],
                    }
                    for h in reversed(history)
                ],
            })

        return jsonify({"endpoints": endpoints, "timestamp": datetime.utcnow().isoformat()})

    finally:
        conn.close()


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("DASHBOARD_PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
