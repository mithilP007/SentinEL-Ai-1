# 🛰️ SentinEL: AI-Powered Supply Chain Resilience & Monitoring

![SentinEL Header](https://raw.githubusercontent.com/mithilP007/SentinEL-Ai-1/main/docs/header_mockup.png)

> **SentinEL** is a high-performance, real-time supply chain monitoring system that leverages **Pathway**, **Gemini 2.0 Flash**, and **GDELT Global News Feeds** to predict and mitigate logistical disruptions before they impact your bottom line.

---

## 🌟 Key Features

### 🧠 Smart AI Route Analysis
Input your origin and destination and let **Gemini 2.0** analyze multiple route alternatives. SentinEL evaluates:
*   **Real-Time Weather**: Integration with Open-Meteo for severe storm detection.
*   **Global Threat Feeds**: Real-time GDELT news analysis for strikes, events, road conditions, wheather and geopolitical tensions.
*   **Safety Scoring**: Dynamic risk scores from 0-100 for every route option.

### 🚚 Real-Time Journey Tracking
Monitor your shipments live on an interactive **Leaflet-powered map**. 
*   **GPS-Synchronized Monitoring**: Track progress with simulated high-fidelity telemetry.
*   **Dynamic Rerouting**: AI-driven suggestions to take diversions if a new threat (like a festival blockade or road closure) is detected live.

### 📊 Performance Observability
Track critical logistical KPIs in a premium dark-mode dashboard:
*   **MTTD (Mean Time to Detection)**: Speed of identifying disruptions.
*   **MTTA (Mean Time to Action)**: Speed of AI-driven mitigation.
*   **Value Tracking**: Automatically calculates **Estimated Days Saved** and **Cost Saved ($)**.

### 📡 Live Data Fabric
SentinEL doesn't rely on mocks. It uses:
*   **GDELT Project**: Scans global news every 60 seconds.
*   **AIS Data**: Real-time ship positioning streams.
*   **Pathway**: High-performance stream processing engine for low-latency analysis.

---
Flowchart - 
<img width="783" height="274" alt="image" src="https://github.com/user-attachments/assets/ba1f90d0-e40a-4780-8a58-927b7eaac3ba" />

Our PipeLine -
<img width="769" height="303" alt="image" src="https://github.com/user-attachments/assets/ecc0660e-5505-48c8-87fb-3d3ea84e6c6d" />


## 🛠️ Architecture

SentinEL is built with a rugged, scalable architecture designed for high-stress logistical environments:

*   **Frontend**: Vanilla HTML5/CSS3/JS with **Leaflet.js** for mapping and **Chart.js** for real-time risk trends.
*   **Backend**: **FastAPI** (Python) for ultra-fast API response times and WebSocket streaming.
*   **AI Engine**: **Google Gemini 2.0 Flash** for complex reasoning and reasoning-with-fallback (Groq/Mistral).
*   **Stream Processing**: **Pathway** for real-time data joining and detection.
*   **Database**: SQLite-backed **Temporal Memory Store** for tracking recurring risk patterns.

---

## 🚀 Getting Started

### 1. Prerequisites
*   Python 3.10+
*   Google Gemini API Key

### 2. Installation
```bash
git clone https://github.com/mithilP007/SentinEL-Ai-1.git
cd SentinEL-Ai-1
pip install -r requirements.txt
```

### 3. Environment Setup
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_key_here
```

### 4. Launch
```bash
# Start the Dashboard & Agent concurrently
python -m uvicorn src.dashboard.app:app --host 127.0.0.1 --port 8000
python -m src.main
```
Access the dashboard at `http://localhost:8000`.

---

## 🗺️ Local Demo (India Focus)
SentinEL is optimized for Indian logistical corridors. 
*   **Route**: Chennai → surat
*   **Sensed Events**: NH44 road works, Pongal holiday traffic, Salem regional diversions.
*   OUR FRONTEND -
<img width="1914" height="874" alt="image" src="https://github.com/user-attachments/assets/cfc750cf-939c-4d94-96ad-519784081150" />
<img width="643" height="615" alt="image" src="https://github.com/user-attachments/assets/33a23dbf-69f2-4e9f-8a6b-ac9d3f7c1802" />


---

## 📄 License
Custom Open Source License - See [LICENSE](LICENSE) for details.

Developed with ❤️ by **SentinEL AI Team**
