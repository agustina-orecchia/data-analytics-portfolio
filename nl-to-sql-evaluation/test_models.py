import os
from dotenv import load_dotenv
from google import genai
from groq import Groq

load_dotenv()  # reads the keys from .env

QUESTION = "Reply with exactly: SELECT 1;"

GEMINI_MODEL = "gemini-4-hydrogen"
GROQ_MODEL = "openai/gpt-oss-120b"

gemini = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
r1 = gemini.models.generate_content(model=GEMINI_MODEL, contents=QUESTION)
print(f"Gemini ({GEMINI_MODEL}): {r1.text}")

groq = Groq(api_key=os.environ["GROQ_API_KEY"])
r2 = groq.chat.completions.create(
    model=GROQ_MODEL,
    messages=[{"role": "user", "content": QUESTION}],
)
print(f"Groq ({GROQ_MODEL}): {r2.choices[0].message.content}")