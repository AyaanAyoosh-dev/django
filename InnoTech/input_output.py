import os
import json
import uuid
from dotenv import load_dotenv
import django

# 1. Load environment variables from .env first
load_dotenv()

# Initialize Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InnoTech.settings')
django.setup()

from engine.chemistry_agents import run_full_industrial_pipeline

def main():
    print("=" * 70)
    print("   [INNOTECH] URBAN ORE HYDROMETALLURGICAL CONTROL TERMINAL - I/O")
    print("=" * 70)
    
    # 1. Factory POV: Input XRF Telemetry Data
    print("\n[FACTORY FLOOR TELEMETRY]")
    xrf_input = input("Enter XRF Elemental Data (e.g., au=2, cu=45, pb=5, fe=38): ").strip()
    if not xrf_input:
        xrf_input = "au=2, cu=45, pb=5, fe=38"
        print(f"-> Using default telemetry: {xrf_input}")

    # 2. Assign Unique Serial Number for this Batch/Run
    serial_number = f"IT-BATCH-{uuid.uuid4().hex[:8].upper()}"
    print(f"\n[SYSTEM] Generated Batch Serial Number: {serial_number}")

    approved = False
    current_recipe = "Choline Chloride : Urea (1:2 ratio) @ 80°C"
    
    while not approved:
        print(f"\n[SYSTEM] Transmitting Serial [{serial_number}] to Data Retriever & Chemistry Processing Units...")
        
        # Call the processing engine (handles literature retrieval + multi-agent debate)
        pipeline_result = run_full_industrial_pipeline(serial_number, xrf_input, current_recipe)
        
        # 3. Customer POV Dashboard Display
        print("\n" + "=" * 30 + " CUSTOMER DASHBOARD " + "=" * 30)
        print(f" Batch Serial Number : {serial_number}")
        print(f" Final Safety Score  : {pipeline_result['final_score']} / 100")
        print(f" Pipeline Status     : {pipeline_result['status']}")
        print(f" Total Debate Turns  : {pipeline_result['total_turns']}")
        print("-" * 76)
        print(" FINAL RECOMMENDED EXTRACTION RECIPE:")
        print(f" {pipeline_result['final_recipe']}")
        print("=" * 76)
        
        # --- FULL CHAT & DEBATE LOG DISPLAY ---
        print("\n" + "~" * 30 + " FULL AGENT DEBATE LOG " + "~" * 30)
        for turn in pipeline_result['history']:
            print(f"\n >>> [TURN {turn['turn']}] --- Safety Score: {turn['safety_score']}/100 | Hazards: {turn['hazards']}")
            
            print(f"\n [CHEMIST PROPOSAL]:")
            print(f"{turn['chemist_proposal']}")
            
            print(f"\n [PEER REVIEWER CRITIQUE]:")
            print(f"{turn['peer_critique']}")
            
            print(f"\n [KAREN AUDITOR CRITIQUE]:")
            print(f"{turn['auditor_critique']}")
            print("-" * 76)

        # 4. Terminal Human Sign-Off Gate
        print(f"\n[HUMAN SAFETY OFFICER TERMINAL - {serial_number}]")
        decision = input("Enter command -> Type [approve] to authorize or [retry] to send back to Chemist: ").strip().lower()
        
        if decision == "approve":
            approved = True
            print(f"\n[SUCCESS] Batch {serial_number} approved and locked for industrial execution.")
        elif decision == "retry":
            print(f"\n[SYSTEM] Retry requested for Serial {serial_number}. Routing back to Chemist processing...")
            current_recipe = pipeline_result['final_recipe'] # Feed previous recipe back as base for adjustment
        else:
            print("\n[SYSTEM] Unrecognized command. Defaulting to retry loop.")
            current_recipe = pipeline_result['final_recipe']

if __name__ == "__main__":
    main()  