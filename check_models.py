import google.generativeai as genai
import sys

API_KEY = "AIzaSyCVvcbz8VfxO7nSxeZkMttZ6YHpDti0NOQ"
genai.configure(api_key=API_KEY)

try:
    print("Models available for generateContent:")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
except Exception as e:
    print(f"Error: {e}")
