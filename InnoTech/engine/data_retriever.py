import os
import sqlite3
import urllib.parse
import urllib.request
from dotenv import load_dotenv
from openai import OpenAI
from whitelist import ALLOWED_DOMAINS
load_dotenv()
def fetch_and_store_literature(serial_number, xrf_data, db_path="db.sqlite3"):
    """
    Fetches raw literature from whitelisted domains, uses GPT-4o to parse/summarize 
    relevant extraction parameters, and logs it into SQLite3 tied to the serial number.
    """
    target_url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/choline%20chloride/property/IUPACName/json"
    parsed = urllib.parse.urlparse(target_url)
    
    # 1. Enforce strict whitelist verification
    if parsed.netloc not in ALLOWED_DOMAINS:
        return f"ACCESS DENIED: Domain '{parsed.netloc}' is not in the verified whitelist."
    
    try:
        # 2. Fetch raw data securely
        req = urllib.request.Request(target_url, headers={'User-Agent': 'InnoTech/1.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw_content = resp.read().decode('utf-8')[:3000]
            
        # 3. Use GPT-4o to parse and format the literature for hydrometallurgical context
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        extraction_prompt = f"""
        Analyze this raw database payload for XRF telemetry data ({xrf_data}) and extract 
        relevant Deep Eutectic Solvent (DES) / chemical property insights into a clean, concise technical summary:
        
        {raw_content}
        """
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a precise scientific data parsing assistant for hydrometallurgical operations."},
                {"role": "user", "content": extraction_prompt}
            ]
        )
        parsed_snippet = response.choices[0].message.content

        # 4. Store into SQLite3 bound to the batch serial number
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS literature_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                serial_number TEXT,
                xrf_data TEXT,
                url TEXT,
                domain TEXT,
                snippet TEXT,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            INSERT INTO literature_cache (serial_number, xrf_data, url, domain, snippet)
            VALUES (?, ?, ?, ?, ?)
        """, (serial_number, xrf_data, target_url, parsed.netloc, parsed_snippet))
        conn.commit()
        conn.close()
        
        return parsed_snippet
        
    except Exception as e:
        return f"GPT-4o Retriever/Database error for batch {serial_number}: {str(e)}"