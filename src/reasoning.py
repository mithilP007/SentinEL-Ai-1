import requests
import json
import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

# --- LLM CLIENTS ---

class GroqRESTClient:
    """
    Primary: Groq Cloud (Llama 3.3 70B).
    Fast inference, OpenAI-compatible API.
    """
    def __init__(self, api_key):
        self.api_key = api_key
        self.url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.3-70b-versatile" # Latest Llama 3.3

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
    Fallback: Mistral Large.
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
        # 1. Primary: Groq
        groq_key = os.getenv("GROQ_API_KEY", "")
        self.primary = GroqRESTClient(groq_key) if groq_key else None
        
        # 2. Fallback: Mistral
        mistral_key = os.getenv("MISTRAL_API_KEY", "") 
        self.fallback = MistralRESTClient(mistral_key) if mistral_key else None
        
        print(f"[INFO] Reasoning Engine Initialized.")
        print(f"       Primary: Groq Llama 3.3 ({'Active' if self.primary else 'Missing Key'})")
        print(f"       Fallback: Mistral Large ({'Active' if self.fallback else 'Inactive'})")

    def invoke_with_fallback(self, system_prompt, user_prompt):
        # Attempt Primary
        if self.primary:
            try:
                # print("   (Using Groq...)")
                return self.primary.invoke(system_prompt, user_prompt)
            except Exception as e:
                print(f"[WARNING] Primary LLM (Groq) Failed: {e}. Switching to Fallback.")
        
        # Attempt Fallback
        if self.fallback:
            try:
                print("   (Using Mistral Fallback...)")
                return self.fallback.invoke(system_prompt, user_prompt)
            except Exception as e:
                print(f"[ERROR] Fallback LLM (Mistral) Failed: {e}.")
        
        # Ultimate Fallback: Mock
        print("[WARNING] All LLMs failed. Using Logic Gate.")
        return None

    def analyze_impact(self, event_summary: str, shipment_details: Dict[str, Any]) -> str:
        """
        Asks the LLM to explain WHY this event impacts this shipment.
        """
        system_prompt = "You are a Logistics Risk Analyst. Keep answers under 2 sentences. Focus on delay and risk."
        user_prompt = f"""
        Event: {event_summary}
        Route: {shipment_details.get('route_id')}
        Location: {shipment_details.get('current_location')}
        
        Analyze impact.
        """
        
        response = self.invoke_with_fallback(system_prompt, user_prompt)
        if response:
            return response
            
        # Mock Response
        return f"Mock Analysis: {event_summary} may cause delays on {shipment_details.get('route_id')}."

    def recommend_action(self, impact_analysis: str, risk_score: float) -> str:
        """
        Decides on the mitigation policy based on analysis.
         LLM could do this, but for speed/safety/determinism, we often keep policy heuristic.
         However, let's try LLM for "Reasoning" here too if available.
        """
        # We can ask LLM to recommend, or stick to robust thresholds.
        # For the demo "Reasoning" proof, let's ask LLM to JUSTIFY the threshold action.
        
        # Fast path
        action = "INFO"
        if risk_score > 80: action = "CRITICAL: REROUTE"
        elif risk_score > 50: action = "WARNING: ALERT"
        
        return action

