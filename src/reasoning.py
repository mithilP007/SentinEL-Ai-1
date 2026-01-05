import requests
import json
import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

# --- LLM CLIENTS ---

class GeminiRESTClient:
    """
    Primary: Google Gemini.
    Uses the official google-generativeai SDK.
    """
    def __init__(self, api_key):
        self.api_key = api_key
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
            self.available = True
        except Exception as e:
            print(f"[WARNING] Could not initialize Gemini: {e}")
            self.model = None
            self.available = False

    def invoke(self, system_prompt: str, user_prompt: str) -> str:
        if not self.available or not self.model:
            raise Exception("Gemini not initialized")
        
        try:
            # Combine system and user prompts
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            response = self.model.generate_content(
                full_prompt,
                generation_config={
                    "temperature": 0.1,
                    "max_output_tokens": 500,
                }
            )
            return response.text
        except Exception as e:
            raise Exception(f"Gemini Error: {e}")


class GroqRESTClient:
    """
    Fallback 1: Groq Cloud (Llama 3.3 70B).
    Fast inference, OpenAI-compatible API.
    """
    def __init__(self, api_key):
        self.api_key = api_key
        self.url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.3-70b-versatile"

    def invoke(self, system_prompt: str, user_prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1
        }
        
        try:
            response = requests.post(self.url, headers=headers, json=payload, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content']
            else:
                raise Exception(f"Groq API Error {response.status_code}: {response.text}")
        except Exception as e:
            raise Exception(f"Groq Network Error: {e}")


class MistralRESTClient:
    """
    Fallback 2: Mistral Large.
    """
    def __init__(self, api_key):
        self.api_key = api_key
        self.url = "https://api.mistral.ai/v1/chat/completions"
        self.model = "mistral-large-latest"

    def invoke(self, system_prompt: str, user_prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1
        }
        
        try:
            response = requests.post(self.url, headers=headers, json=payload, timeout=8)
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content']
            else:
                raise Exception(f"Mistral API Error {response.status_code}")
        except Exception as e:
            raise Exception(f"Mistral Network Error: {e}")


# --- ENGINE ---

class ReasoningEngine:
    def __init__(self):
        # 1. Primary: Google Gemini 2.0 Flash
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.primary = GeminiRESTClient(gemini_key) if gemini_key else None
        
        # 2. Fallback 1: Groq
        groq_key = os.getenv("GROQ_API_KEY", "")
        self.fallback1 = GroqRESTClient(groq_key) if groq_key else None
        
        # 3. Fallback 2: Mistral
        mistral_key = os.getenv("MISTRAL_API_KEY", "") 
        self.fallback2 = MistralRESTClient(mistral_key) if mistral_key else None
        
        print(f"[INFO] Reasoning Engine Initialized.")
        print(f"       🔮 Primary: Gemini 2.0 Flash ({'✅ Active' if self.primary else '❌ Missing Key'})")
        print(f"       🦙 Fallback 1: Groq Llama 3.3 ({'✅ Active' if self.fallback1 else '⚪ Inactive'})")
        print(f"       🌊 Fallback 2: Mistral Large ({'✅ Active' if self.fallback2 else '⚪ Inactive'})")

    def invoke_with_fallback(self, system_prompt, user_prompt):
        # Attempt Primary: Gemini
        if self.primary:
            try:
                return self.primary.invoke(system_prompt, user_prompt)
            except Exception as e:
                print(f"[WARNING] Primary LLM (Gemini) Failed: {e}. Switching to Fallback.")
        
        # Attempt Fallback 1: Groq
        if self.fallback1:
            try:
                print("   (Using Groq Fallback...)")
                return self.fallback1.invoke(system_prompt, user_prompt)
            except Exception as e:
                print(f"[WARNING] Fallback 1 (Groq) Failed: {e}. Trying next fallback.")
        
        # Attempt Fallback 2: Mistral
        if self.fallback2:
            try:
                print("   (Using Mistral Fallback...)")
                return self.fallback2.invoke(system_prompt, user_prompt)
            except Exception as e:
                print(f"[ERROR] Fallback 2 (Mistral) Failed: {e}.")
        
        # Ultimate Fallback: Mock
        print("[WARNING] All LLMs failed. Using Logic Gate.")
        return None

    def analyze_impact(self, event_summary: str, shipment_details: Dict[str, Any]) -> str:
        """
        Asks the LLM to explain WHY this event impacts this shipment.
        """
        system_prompt = "You are an Elite AI Logistics Command Agent. Analyze real-time disruptions including road conditions, weather, and local events. Focus on transit time impact and supply chain integrity."
        user_prompt = f"""
        LIVE DISRUPTION DETECTED:
        Event Summary: {event_summary}
        Current Route: {shipment_details.get('route_id')}
        Vessel/Vehicle Current Location: {shipment_details.get('current_location')}
        ETA Impact: {shipment_details.get('eta_days', 'N/A')} days remaining

        TASK: Provide a sharp, real-time assessment of how this event affects THIS specific shipment. 
        If it's a festival, road closure, or traffic in India (like Pongal, Chennai traffic, NH44 works), explain the specific impact.
        Mention if a DIVERSION or alternate highway is needed. Max 2 sentences.
        """
        
        response = self.invoke_with_fallback(system_prompt, user_prompt)
        if response:
            return response
            
        # Mock Response
        return f"Mock Analysis: {event_summary} may cause delays on {shipment_details.get('route_id')}."

    def recommend_action(self, impact_analysis: str, risk_score: float) -> str:
        """
        Decides on the mitigation policy based on analysis.
        Uses LLM to provide a human-readable recommendation.
        """
        system_prompt = "You are a Logistics Dispatcher. Based on the impact analysis, provide a 1-sentence recommendation. Always start with 'CRITICAL: REROUTE', 'WARNING: ALERT', or 'ADVISORY: MONITOR'."
        user_prompt = f"Impact Analysis: {impact_analysis}\nRisk Score: {risk_score}/100\n\nProvide the best next step (e.g. 'Take diversion via...', 'Alert driver...', 'Proceed with caution...')."
        
        response = self.invoke_with_fallback(system_prompt, user_prompt)
        if response:
            return response.strip()
            
        # Fallback if LLM fails
        if risk_score > 80: return "CRITICAL: REROUTE REQUIRED"
        elif risk_score > 50: return "WARNING: ALERT ISSUED"
        return "ADVISORY: PROCEED WITH CAUTION"
    
    def analyze_route_threats(self, route_info: Dict, threats: list) -> str:
        """
        Analyze threats along a specific route using Gemini.
        """
        if not threats:
            return "No significant threats detected along your route."
        
        system_prompt = """You are an AI Supply Chain Risk Advisor. Analyze the threats along the user's shipping route and provide:
1. A brief risk assessment (1-2 sentences)
2. The most critical threat
3. A recommended action

Keep your response concise and actionable."""

        threat_summary = "\n".join([
            f"- {t.get('topic', 'Unknown')} at {t.get('location', 'Unknown')} (Severity: {t.get('severity', 5)}/10)"
            for t in threats[:5]
        ])
        
        user_prompt = f"""
Route: {route_info.get('start', {}).get('address', 'Unknown')} → {route_info.get('end', {}).get('address', 'Unknown')}
Distance: {route_info.get('distance_km', 0):.0f} km
Duration: {route_info.get('duration_minutes', 0):.0f} minutes

Detected Threats:
{threat_summary}

Provide your risk analysis.
"""
        
        response = self.invoke_with_fallback(system_prompt, user_prompt)
        return response or "Unable to analyze threats at this time."

    def smart_route_selection(self, context: Dict) -> str:
        """
        Compare route options and provide an AI recommendation.
        Context includes: start, end, options (list of routes with risks/scores).
        """
        system_prompt = """You are an Expert Logistics Route Planner AI. 
        Your goal is to select the safest and most efficient route for a cargo vehicle.
        
        Consider:
        1. Travel time (Duration).
        2. Real-time Weather conditions (Severity).
        3. Security/Event threats (Road blocks, festivals, strikes).
        
        You must:
        - Identify the BEST recommended route.
        - Explain WHY (e.g., "Route A is faster but has severe storms; Route B is safer").
        - List the specific risks avoided.
        
        Output format:
        **RECOMMENDATION:** [Route Name/Number]
        **REASONING:** [Explanation]
        """
        
        routes_desc = ""
        for i, opt in enumerate(context.get("options", [])):
            routes_desc += f"\nROUTE OPTION {i+1}:\n"
            routes_desc += f"- Distance: {opt['distance_km']:.1f} km\n"
            routes_desc += f"- Duration: {opt['duration_minutes']:.1f} min\n"
            routes_desc += f"- Weather Risks: {', '.join(opt['analysis']['weather_risks']) or 'None'}\n"
            routes_desc += f"- Event Risks: {', '.join(opt['analysis']['event_risks']) or 'None'}\n"
            routes_desc += f"- Safety Score: {opt['analysis']['score']:.1f}/100\n"
            
        user_prompt = f"""
        Origin: {context.get('start_address')}
        Destination: {context.get('end_address')}
        
        Available Routes:
        {routes_desc}
        
        Which route do you recommend and why?
        """
        
        response = self.invoke_with_fallback(system_prompt, user_prompt)
        return response or "Analysis unavailable. Please choose the route with the highest safety score."


