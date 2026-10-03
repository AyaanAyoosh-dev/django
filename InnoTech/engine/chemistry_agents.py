import os
import json
import re
import time
from openai import OpenAI
from dotenv import load_dotenv
from google import genai
from google.genai.errors import ServerError
from .data_retriever import fetch_and_store_literature

# 1. Load environment variables from .env first
load_dotenv()

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Initialize the OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -------------------------------------------------------------------
# MODEL CONFIGURATION (SWITCHED TO OPENAI)
# -------------------------------------------------------------------
PRIMARY_MODEL = "gpt-4o"
FALLBACK_MODEL = "gpt-4o-mini"

def call_gemini_with_fallback(client, prompt):
    """Refactored helper to route requests through OpenAI GPT models safely."""
    models_to_try = [PRIMARY_MODEL, FALLBACK_MODEL]
    
    for model_name in models_to_try:
        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = openai_client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are an expert industrial chemical engineering and safety auditing assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3
                )
                
                # Mock a response object with a `.text` attribute to match your existing code structure
                class OpenAIResponseMock:
                    def __init__(self, content):
                        self.text = content
                
                return OpenAIResponseMock(response.choices[0].message.content)
                
            except Exception as e:
                error_message = str(e)
                print(f" [WARNING] OpenAI Model {model_name} encountered an issue: {error_message}")
                
                if attempt < max_retries - 1:
                    print(f" [WARNING] Retrying {model_name} in 2 seconds...")
                    time.sleep(2)
                    continue
                
                print(f" [WARNING] Switching from {model_name} to fallback model...")
                break 
                
    raise Exception("Critical Error: All OpenAI model options and fallbacks failed.")
# -------------------------------------------------------------------
# AGENT SYSTEM PROMPTS (MULTI-STEP SEQUENTIAL EXTRACTION)
# -------------------------------------------------------------------

CHEMIST_SYSTEM_PROMPT = """
YOU ARE THE LEAD METALLURGICAL CHEMIST.
- Your role is to formulate and optimize a MULTI-STEP Deep Eutectic Solvent (DES) extraction recipe based on XRF telemetry.
- You must structure the recipe into clear, sequential steps (e.g., Step 1: Base metal pre-leaching, Step 2: Copper extraction, Step 3: Precious metal/Gold recovery) to ensure clean separation of all detected elements.
- CRITICAL: You must include physical safety engineering controls demanded by the auditor, such as emergency quench interlocks, iodine/off-gas scrubbers, pressure relief, and strict PPE protocols, to avoid safety rejections.
"""

PEER_CHECKER_SYSTEM_PROMPT = """
YOU ARE THE SENIOR CROSS-CHECKER & PEER REVIEWER.
- Your role is to critically evaluate the Chemist's multi-step extraction sequence for thermodynamic feasibility, phase crossover risks, and selectivity between steps.
- Verify that each step logically follows the previous one and prevents co-dissolution or contamination of high-value metals.
"""

AUDITOR_KAREN_SYSTEM_PROMPT = """
YOU ARE "KAREN", THE CHIEF COMPLIANCE & SAFETY AUDITOR.
- Your role is to inspect the multi-step sequential recipe and assign a strict safety score from 0 to 100.
- You are exceptionally rigorous and reject "thermal gerrymandering" or policy loopholes. Every step must feature real engineering controls (scrubbers, quench systems, pressure relief valves) if handling volatile reagents like iodine, H2O2, or FeCl3/Cu2+ shuttles.
- You MUST return ONLY a valid JSON payload matching this exact format:
{
    "safety_score": <integer 0-100>,
    "hazards": ["hazard 1", "hazard 2"],
    "critique": "Karen's sharp, uncompromising critique of the multi-step sequence."
}
"""

# -------------------------------------------------------------------
# INDIVIDUAL AGENT FUNCTIONS (GEMINI BACKED)
# -------------------------------------------------------------------

def run_chemist_agent(client, serial_number, xrf_data, lit_snippet, current_recipe, previous_critique):
    """Agent 1: Chemist - Proposes/refines a multi-step metal recovery recipe."""
    prompt = f"""
    {CHEMIST_SYSTEM_PROMPT}
    
    Batch Serial: {serial_number}
    XRF Telemetry: {xrf_data}
    Verified Literature Context: {lit_snippet[:500]}
    Current Multi-Step Recipe: {current_recipe}
    Previous Audit/Peer Feedback to Fix: {previous_critique}
    
    Refine or build a strict, multi-step sequential Deep Eutectic Solvent (DES) extraction protocol that addresses all safety and hazard criticisms.
    """
    response = call_gemini_with_fallback(client, prompt)
    return response.text

def run_peer_checker_agent(client, proposed_recipe):
    """Agent 2: Peer / Cross-Checker - Evaluates multi-step sequence feasibility."""
    prompt = f"""
    {PEER_CHECKER_SYSTEM_PROMPT}
    
    Review this proposed multi-step extraction protocol for chemical and kinetic validity:
    {proposed_recipe}
    
    Provide your cross-check evaluation, pointing out any flaws in step ordering, reagent crossover, or selectivity.
    """
    response = call_gemini_with_fallback(client, prompt)
    return response.text

def run_auditor_agent(client, proposed_recipe):
    """Agent 3: Karen Auditor - Strict multi-step safety score calculation."""
    prompt = f"""
    {AUDITOR_KAREN_SYSTEM_PROMPT}
    
    Audit this multi-step recipe for safety compliance and engineering controls:
    {proposed_recipe}
    """
    response = call_gemini_with_fallback(client, prompt)
    
    raw_text = response.text
    json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
    
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
            
    return {
        "safety_score": 20,
        "hazards": ["JSON Parsing Failure", "Unverified Safety Submission"],
        "critique": "Audit output format rejected. Unacceptable safety standard!"
    }

# -------------------------------------------------------------------
# MAIN PIPELINE ORCHESTRATOR (CONDITIONAL WORKFLOW)
# -------------------------------------------------------------------

def run_full_industrial_pipeline(serial_number, xrf_data, initial_recipe):
    """Orchestrates conditional debate loop using Gemini: Chemist -> Karen -> (If fail) Peer Checker -> Chemist."""
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    # Fetch literature context via OpenAI retriever
    lit_snippet = fetch_and_store_literature(serial_number, xrf_data)
    
    current_recipe = initial_recipe
    audit_history = []
    safety_score = 0
    max_turns = 3
    turn = 0
    previous_feedback = "None"

    while safety_score < 90 and turn < max_turns:
        turn += 1
        print(f"\n--- [GEMINI CONDITIONAL LOOP: TURN {turn} / {max_turns}] ---")

        # 1. Chemist builds or refines the sequence
        print(" > Chemist is formulating/refining multi-step sequence...")
        current_recipe = run_chemist_agent(client, serial_number, xrf_data, lit_snippet, current_recipe, previous_feedback)

        # 2. Straight to Karen Auditor first
        print(" > Karen Auditor is inspecting safety and scoring...")
        audit_result = run_auditor_agent(client, current_recipe)
        
        safety_score = audit_result.get("safety_score", 0)
        critique = audit_result.get("critique", "")
        hazards = audit_result.get("hazards", [])
        print(f" -> Karen's Safety Score for Turn {turn}: {safety_score}/100")

        # 3. If Karen approves (90+), skip peer review and exit loop successfully
        if safety_score >= 90:
            print(" -> Karen approved the recipe on first check! Pipeline successful.")
            audit_history.append({
                "turn": turn,
                "chemist_proposal": current_recipe,
                "peer_critique": "Skipped (Passed Karen directly)",
                "safety_score": safety_score,
                "auditor_critique": critique,
                "hazards": hazards
            })
            break

        # 4. If Karen rejects it, engage the Peer Checker for diagnostic feedback
        print(" > Karen rejected it. Sending to Peer Checker to evaluate flaws...")
        peer_critique = run_peer_checker_agent(client, current_recipe)

        audit_history.append({
            "turn": turn,
            "chemist_proposal": current_recipe,
            "peer_critique": peer_critique,
            "safety_score": safety_score,
            "auditor_critique": critique,
            "hazards": hazards
        })

        # Pack both critiques for the Chemist's next iteration
        previous_feedback = f"Karen's Rejection Critique: {critique} | Peer Technical Review: {peer_critique}"

    target_achieved = safety_score >= 90

    return {
        "serial_number": serial_number,
        "final_recipe": current_recipe,
        "final_score": safety_score,
        "status": "READY_FOR_HUMAN_SIGN_OFF" if target_achieved else "FAILED_SAFETY_THRESHOLD",
        "history": audit_history,
        "total_turns": turn
    }