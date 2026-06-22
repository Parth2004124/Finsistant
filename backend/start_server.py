import os
import sys

# Stdout redirection removed so console window shows logs

from pyngrok import ngrok
from waitress import serve
from main import app

if __name__ == "__main__":
    port = 8000
    print("Opening Ngrok tunnel...")
    
    try:
        public_url = ngrok.connect(port).public_url
        print("\n" + "="*50)
        print("NGROK TUNNEL CREATED SUCCESSFULLY!")
        print(f"---> {public_url} <---")
        print("="*50 + "\n")
        
        with open('ngrok_url.txt', 'w') as f:
            f.write(public_url)
    except Exception as e:
        print(f"Ngrok is likely already running. Ignoring error: {e}")

        
    print(f"Starting Waitress server on port {port}...")
    serve(app, host="0.0.0.0", port=port)
