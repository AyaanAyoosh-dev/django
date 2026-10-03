import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()

try:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Say hello inside a raw JSON block like: {'msg': 'hello'}"}],
        response_format={"type": "json_object"}
    )
    print("\n🟢 SUCCESS! Here is how your installed library wants it written:")
    print("-----------------------------------------------------------------")
    print(f"Option A: {response.choices[0].message.content}")
except Exception as e:
    print(f"\n❌ Option A failed with error: {e}")

try:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Say hello inside a raw JSON block like: {'msg': 'hello'}"}],
        response_format={"type": "json_object"}
    )
    print(f"Option B (No Index): {response.choices.message.content}")
except Exception as e:
    print(f"❌ Option B failed with error: {e}")
