# SentinEL Security & Compliance

## 1. Principles
SentinEL is designed with **"Zero Trust"** and **"Human-in-the-Loop Safety"** principles.

## 2. API Key Management
- All keys (OpenAI, Pathway, Slack) are injected via `os.environ`.
- Keys are **never** logged to the telemetry stream or console.
- **Circuit Breaker**: If keys are missing, the system defaults to "Safe Mode" (Mock inference), preventing unauthenticated API calls.

## 3. Autonomous Safety Layers
### a. Confidence Thresholds
- Agents assess their own confidence (0.0 - 1.0).
- **Threshold**: Actions with `< 0.70` confidence are **BLOCKED** autonomously.
- **Alert**: Blocked actions trigger a "Human Review" notification.

### b. Rate Limiting
- The `Actions` layer implements a cooldown to prevent message flooding (e.g., max 1 email/hour per shipment).

### c. Role-Based Access (Future)
- `REROUTE` actions require `ADMIN` policy context.
- `NOTIFY` actions require `VIEWER` context.

## 4. Audit Trail
- Every decision is logged to an immutable **append-only** CSV/Parquet log (`memory_log.csv`).
- Logs contain: `EventID`, `InputHash`, `ReasoningTrace`, `Decision`, `Outlet`.
- This ensures full **explainability** for post-incident audits.
