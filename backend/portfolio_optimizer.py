import sys
import json
import os
import google.generativeai as genai

# Configure Gemini
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    try:
        with open("token.txt", "r") as f:
            API_KEY = f.read().strip()
    except:
        pass
genai.configure(api_key=API_KEY)

def optimize_portfolio(portfolio_file):
    print(f"Starting CFA Portfolio AI Optimization from {portfolio_file}...")
    
    try:
        with open(portfolio_file, "r") as f:
            portfolio_data = json.load(f)
    except Exception as e:
        print(f"Failed to read portfolio file: {e}")
        sys.exit(1)
        
    prompt = f"""
    You are an elite Chartered Financial Analyst (CFA) and Quantitative Portfolio Manager.
    
    Analyze the user's current live portfolio data:
    {json.dumps(portfolio_data, indent=2)}
    
    The user wants a highly visual and concise portfolio optimization report for their dashboard.
    Do NOT output a wall of text.
    You must output EXACTLY a valid JSON object matching this schema, without any markdown formatting (do NOT wrap in ```json ... ```):
    {{
      "detailed_analysis": "Provide a comprehensive 2-paragraph CFA verdict on the portfolio's diversification, capital efficiency, risk exposure, and actionable rebalancing advice.",
      "kpis": [
        {{ "label": "Diversification", "value": "Good/Poor", "color": "#238636" }},
        {{ "label": "Growth Tilt", "value": "High/Low", "color": "#58a6ff" }},
        {{ "label": "Risk Profile", "value": "Aggressive", "color": "#f85149" }},
        {{ "label": "Action", "value": "Rebalance", "color": "#d2a8ff" }}
      ],
      "doughnut_chart": [
        {{ "name": "Defensive", "value": 30, "fill": "#3fb950" }},
        {{ "name": "Cyclical", "value": 70, "fill": "#f85149" }}
      ],
      "bar_chart": [
        {{ "name": "Suggested Cash (%)", "value": 15, "fill": "#d2a8ff" }},
        {{ "name": "Suggested Equities (%)", "value": 85, "fill": "#58a6ff" }}
      ]
    }}
    
    Rules for JSON generation:
    1. Provide exactly 4 KPIs with hex colors based on sentiment (e.g., Green for good, Red for bad, Blue/Purple for neutral descriptors).
    2. Provide exactly 2 or 3 entries in `doughnut_chart` representing the AI's perceived Risk Profile (e.g., Defensive, Cyclical, Growth, Value). Must sum to 100.
    3. Provide exactly 2 to 4 key target weight percentages in `bar_chart` representing your suggested Rebalancing Targets (e.g., Suggested Cash, Suggested Large Cap, Suggested Mid Cap).
    4. Output ONLY the raw JSON string. Do NOT add markdown tags.
    """
    
    model_ai = genai.GenerativeModel('gemini-2.5-flash')
    response = model_ai.generate_content(prompt)
    report = response.text.strip()

    # Strip markdown if Gemini accidentally included it
    if report.startswith("```json"):
        report = report[7:]
    if report.endswith("```"):
        report = report[:-3]
    report = report.strip()

    # Verify it is valid JSON
    try:
        json.loads(report)
    except json.JSONDecodeError as e:
        print(f"AI did not return valid JSON: {e}")
        # Fallback dummy data if AI fails formatting
        report = json.dumps({
            "detailed_analysis": "The AI failed to format the response as JSON. Please try again.",
            "kpis": [],
            "doughnut_chart": [],
            "bar_chart": []
        })

    # Save to file
    with open("portfolio_ai_report.json", "w") as f:
        f.write(report)
    
    print(f"Successfully generated and saved CFA Portfolio Optimization Report.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python portfolio_optimizer.py <portfolio_json_file>")
        sys.exit(1)
    
    portfolio_file = sys.argv[1]
    optimize_portfolio(portfolio_file)
