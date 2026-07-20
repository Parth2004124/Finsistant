import os
import sys

# Force unbuffered output so print statements show up immediately
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

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
            
        print("Syncing ngrok URL to GitHub...")
        os.system('git add ngrok_url.txt >nul 2>&1')
        os.system('git commit -m "Auto-update ngrok URL" >nul 2>&1')
        os.system('git push origin master >nul 2>&1')
        print("Sync complete!")
    except Exception as e:
        print(f"Ngrok is likely already running. Ignoring error: {e}")

        
    print(f"Starting Waitress server on port {port}...")
    serve(app, host="0.0.0.0", port=port)
