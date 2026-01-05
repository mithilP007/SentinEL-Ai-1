---
description: Route-Based Real-Time Supply Chain Monitoring Implementation Plan
---

# SentinEL Route Monitoring Enhancement

## Overview
Transform SentinEL from a general global monitoring system to a **user-focused route-based threat detection system** that monitors real-time risks between user-specified start and end points.

## Core Features to Implement

### 1. Route Input System (Frontend)
- **Geolocation Permission**: Browser asks for location access
  - If allowed: Auto-fill start point with current location
  - If denied: User manually enters start point
- **Manual End Point Entry**: User always enters destination manually
- **Map Route Visualization**: Draw route polyline on Leaflet map
- **Radar Circle**: Scanning animation around route corridor

### 2. Real-Time Data Sources (All LIVE - No Mock Data)
- **GDELT News API**: Already implemented - filter for route-specific locations
- **OpenWeatherMap API**: Weather alerts along route corridor
- **OSRM/GraphHopper**: Route calculation between points
- **Nominatim/OpenCage**: Geocoding addresses to coordinates

### 3. Backend Route Processing
- Calculate waypoints along the route
- Define monitoring corridor (e.g., 200km buffer around route)
- Filter all real-time events for this corridor
- WebSocket push filtered alerts to frontend

## Implementation Steps

// turbo-all

### Step 1: Update Frontend HTML - Add Route Input Modal
Add a route input modal that appears on page load with:
- "Use My Location" button (geolocation API)
- Start point text input (for manual or auto-filled)
- End point text input (always manual)
- "Start Monitoring" button

### Step 2: Add Geocoding Service
Create new endpoint `/api/geocode` that converts address strings to lat/lng coordinates using:
- Nominatim (free, OpenStreetMap-based)
- Returns: {lat, lng, display_name}

### Step 3: Add Route Calculation Service
Create new endpoint `/api/route` that calculates route between two points using:
- OSRM public API (free routing)
- Returns: polyline geometry, waypoints, distance, duration

### Step 4: Update WebSocket to Support Route Filtering
Modify the backend to:
- Store active user route
- Filter GDELT/Weather events within route corridor
- Only broadcast relevant events

### Step 5: Add Radar Visualization
Implement animated radar sweep on the map:
- Pulsing circles along route
- Threat markers with severity colors
- Route polyline with gradient based on risk

### Step 6: Integrate Real Weather API
Replace mock weather with real OpenWeatherMap API:
- Get weather for waypoints along route
- Alert on severe conditions (storms, fog, extreme temps)

## API Keys Required
- `OPENWEATHER_API_KEY` - For real weather data
- No key needed for: Nominatim, OSRM (public APIs)

## File Changes Summary
1. `src/dashboard/index.html` - Add route input modal, radar, route visualization
2. `src/dashboard/app.py` - Add geocoding, routing, route-filtered WebSocket
3. `src/ingestion_live.py` - Add route-aware filtering for GDELT
4. New: `src/route_service.py` - Geocoding and routing logic
5. New: `src/weather_live.py` - Real OpenWeatherMap integration
