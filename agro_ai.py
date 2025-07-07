import requests
import json
from datetime import datetime

OPENROUTER_API_KEY = "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"

def clean_format(text):
    replacements = [
        ("**", ""),
        ("### ", "\n\n"),
        ("## ", "\n\n"),
        ("# ", "\n\n"),
        ("- ", "\n- ")
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text.strip()

def extract_summary(full_text):
    summary_lines = []
    capturing = False
    for line in full_text.splitlines():
        if line.strip().lower().startswith("2. specific maize farming actions"):
            capturing = True
            continue
        if capturing:
            if line.strip().startswith("3. "):
                break
            if line.strip().startswith("-"):
                summary_lines.append(line.strip())
    if not summary_lines:
        summary_lines.append("- No specific actions extracted. Please verify formatting.")
    return "Quick Summary of Actions:\n" + "\n".join(summary_lines) + "\n\nFull Recommendation:\n" + full_text

def analyze_soil_data(soil_data):
    if not soil_data:
        return None, None

    soil_moisture = soil_data.get("soil_moisture")
    soil_temperature = soil_data.get("soil_temperature")
    soil_humidity = soil_data.get("soil_humidity")
    soil_ph = soil_data.get("soil_ph")
    timestamp = soil_data.get("timestamp")

    prompt = f"""
    You are an agricultural advisor specializing in maize (corn) farming. Analyze the following soil data and provide recommendations based on optimal conditions for maize:

    - Soil Moisture: {soil_moisture}%
    - Soil Temperature: {soil_temperature}°C
    - Soil Humidity: {soil_humidity}%
    - Soil pH: {soil_ph}
    - Timestamp: {timestamp}

    Ideal maize conditions:
    - Moisture: 60% to 80%
    - pH: 5.5 to 7.0
    - Temperature: 15°C to 30°C
    - Humidity: 50% to 70%

    Provide:
    1. Assessment of current soil conditions
    2. Specific maize farming actions to optimize growth
    3. Warnings if any values fall outside the ideal range
    4. Reminders about maize growth stages and relevant care
    Format the output as plain text without markdown characters like asterisks or hashtags.
    """

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://agrobot-api.onrender.com",
                "X-Title": "AgroBot Soil Analysis",
            },
            data=json.dumps({
                "model": "mistralai/mistral-small-3.1-24b-instruct:free",
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            })
        )
        response.raise_for_status()
        result = response.json()
        if "choices" in result and result["choices"]:
            raw_recommendation = result["choices"][0]["message"]["content"].strip()
            cleaned = clean_format(raw_recommendation)
            summary = extract_summary(cleaned)
            severity = determine_severity(soil_moisture, soil_temperature, soil_humidity, soil_ph)
            return summary, severity
        else:
            return None, None
    except requests.exceptions.RequestException as e:
        print(f"Error generating AI recommendation: {e}")
        return None, None

def determine_severity(moisture, temperature, humidity, ph):
    score = 0

    if moisture is not None:
        if moisture < 50 or moisture > 90:
            score += 2
        elif moisture < 60 or moisture > 80:
            score += 1

    if temperature is not None:
        if temperature < 10 or temperature > 35:
            score += 2
        elif temperature < 15 or temperature > 30:
            score += 1

    if humidity is not None:
        if humidity < 40 or humidity > 80:
            score += 2
        elif humidity < 50 or humidity > 70:
            score += 1

    if ph is not None:
        if ph < 5.0 or ph > 8.0:
            score += 2
        elif ph < 5.5 or ph > 7.0:
            score += 1

    if score >= 4:
        return "high"
    elif score >= 2:
        return "medium"
    else:
        return "low"

def send_recommendation(recommendation, severity):
    if not recommendation or not severity:
        return False

    try:
        response = requests.post(
            RECOMMENDATIONS_URL,
            headers={"Content-Type": "application/json"},
            json={"recommendation": recommendation, "severity": severity}
        )
        response.raise_for_status()
        print("Recommendation sent successfully.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error sending recommendation: {e}")
        return False

def main():
    print(f"Running maize soil analyzer @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    soil_data = get_sensor_data()
    if not soil_data:
        print("No data. Exiting.")
        return

    recommendation, severity = analyze_soil_data(soil_data)
    if not recommendation:
        print("AI failed to generate recommendation.")
        return

    print(f"Severity: {severity}\n{recommendation}")
    send_recommendation(recommendation, severity)

if __name__ == "__main__":
    main()
