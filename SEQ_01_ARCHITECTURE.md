# SentinEL: System Architecture & Design

## 1. System Overview
**SentinEL** is a real-time, event-driven Agentic AI system designed to detect and mitigate supply chain disruptions. It leverages **Pathway** for high-throughput streaming ingestion and continuous vector indexing, and **LangGraph** for stateful, autonomous agent orchestration.

**Goal**: React to global events (e.g., "Port Strike in Rotterdam") faster than human operators by processing live streams and triggering pre-approved mitigation policies.

---

## 2. Architecture Layers

### Layer 1: Input Layer (Live Data Streams)
**Problem**: Static files don't reflect the world *now*.
**Solution**: Infinite data streams.
- **News/Social**: RSS feeds, Twitter/X firehose (simulated), GDELT.
- **Weather**: live cyclone/flood warnings.
- **Logistics**: AIS shipping telemetry (simulated location updates).
- **Internal ERP**: Orders, Shipments, Inventory levels.

### Layer 2: Streaming Ingestion (Pathway)
**Why Pathway?**
- Standard Python ETL is batch-oriented (pandas) or complex (Spark).
- **Pathway** unifies streaming, batch, and ML in one Python syntax.
- It handles **late data**, **out-of-order events**, and **exact-once processing** automatically.
- **Responsibility**: Ingest raw JSON/CSV streams -> Normalize -> Deduplicate -> Update Tables.

### Layer 3: Real-Time Vector Store (The "Now" Index)
**Innovation**: Most RAG systems search a static DB. SentinEL searches a **living index**.
- **Mechanism**: Pathway's `VectorStore` server, linked directly to the ingestion table.
- **Behavior**: As new news arrives, it is embedded and indexed immediately. Old news implicitly decays or is filtered by timestamp.
- **Querying**: The Agent queries this store for "events affecting [Route X] in the last hour".

### Layer 4: Event Detection & Perception
**Logic**:
1. **Semantic Anomaly**: "Is this news article about a disruption?" (Keyword/LLM-based filter).
2. **Geo-Spatial Intersection**: `ST_Intersects(Shipment_Route, Event_Location)`.
3. **Risk Scoring**: `Severity (1-10) * Impact (Shipment Value)`.
**Output**: A stream of `DisruptionEvent` objects pushed to the Agent.

### Layer 5: Agent Brain (LangGraph)
**Structure**: A cyclic StateGraph.
**States**:
1.  **OBSERVE**: Idle/Listening. Receives a `DisruptionEvent`.
2.  **RETRIEVE**: Query Pathway Vector Store for context (e.g., "What other shipments are near Suez?").
3.  **ANALYZE**: LLM (Reasoning Layer) assesses impact. " blockage delays ETA by 4 days."
4.  **DECIDE**: Select Policy. (e.g., IF delay > 2 days AND cargo = perishable -> REROUTE).
5.  **ACT**: Execute tool calls.
6.  **LOG**: Persist outcome to Memory.

### Layer 6: Reasoning Layer (LLM)
- **Constraint**: No hallucinations. LLM only reasons over *provided* context from Pathway.
- **Role**: Explainer and Judge. "Why is this a risk?"

### Layer 7: Action Layer (Autonomous)
- **Tools**:
    - `send_email_alert(recipient, subject, body)`
    - `update_erp_status(shipment_id, status)`
    - `trigger_slack_notification(channel, message)`
- **Safety**: Actions are logged in an append-only audit trail.

### Layer 8: Long-Term Memory
- **Storage**: Persistent append-only log (csv/parquet) managed by Pathway or external DB.
- **Content**: Event vectors + Action taken + Success/Fail feedback.

---

## 3. Data Flow (End-to-End)

1.  **World**: A "Strike" occurs in "Hamburg".
2.  **Input**: News API picks up the alert.
3.  **Ingest**: Pathway normalizes the text and extracts entities (`Location: Hamburg`, `Topic: Strike`).
4.  **Index**: Pathway embeds the text -> Vector Store updates.
5.  **Percept**: Spatial join finds 3 shipments currently in `Hamburg`.
6.  **Trigger**: `DisruptionEvent` sent to Agent queue.
7.  **Agent**:
    - Wakes up.
    - Queries Vector Store: "History of strikes in Hamburg?"
    - Analyzes: "Shipment A is high priority."
    - Decides: "Notify Logistics Manager."
    - Acts: Calls `notify_slack()`.
8.  **Output**: Slack message appears.

---

## 4. Failure Handling & Scalability

- **Fault Tolerance**: Pathway checkpoints state. If the process crashes, it resumes from the last offset.
- **Scalability**: Pathway engine is written in Rust (highly efficient). Can scale vertically on large instances or distribute (Enterprise).
- **Rate Limiting**: Agent has a "Cooldown" state to prevent spamming alerts for the same event.

## 5. Security

- **API Keys**: Stored in environment variables, never committed.
- **Action Limits**: The agent cannot "Delete" records, only "Update Status" or "Append Note". Human-in-the-loop setting available for high-cost actions.

## 6. Future Upgrade: BDH & Continual Learning
- **Bayesian Dynamic Hypernetworks (BDH)**: Can be integrated to update the LLM's weights (or adapter) based on "Outcome" feedback without full retraining.
- **Concept**: If "Rerouting" fails 5 times in winter, the model learns "Winter Reroute Risk" is higher.
