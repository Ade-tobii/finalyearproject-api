from flask import Flask, request, jsonify
from datetime import datetime
import logging
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import numpy as np

# Initialize Flask app
app = Flask(__name__)

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Supabase connection setup
def get_supabase_client() -> Client:
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    if not supabase_url or not supabase_key:
        logger.error("SUPABASE_URL or SUPABASE_KEY not set in .env")
        exit(1)
    try:
        supabase_client = create_client(supabase_url, supabase_key)
        # Test connection by querying the database
        supabase_client.table('sensor_data').select('*').limit(1).execute()
        logger.info("Connected to Supabase successfully")
        return supabase_client
    except Exception as e:
        logger.error(f"Failed to connect to Supabase: {e}")
        exit(1)

# Initialize Supabase
supabase_client = get_supabase_client()

@app.route('/', methods=['GET'])
def index():
    return "Welcome to the Soil Sensor Monitoring API!"

# GET endpoint to retrieve recommendations
@app.route('/api/recommendations', methods=['GET'])
def get_recommendations():
    try:
        response = supabase_client.table('recommendations').select('*').order('timestamp', desc=True).execute()
        data = response.data
        logger.info("Retrieved recommendations successfully")
        return jsonify(data), 200
    except Exception as e:
        logger.error(f"Error retrieving recommendations: {e}")
        return jsonify({"error": "Internal server error"}), 500

# POST endpoint to receive recommendation and severity
@app.route('/api/recommendations', methods=['POST'])
def receive_recommendation():
    try:
        data = request.get_json()
        if not data:
            logger.warning("No JSON data received")
            return jsonify({"error": "No data provided"}), 400

        required_fields = ["recommendation", "severity"]
        if not all(field in data for field in required_fields):
            missing = [field for field in required_fields if field not in data]
            logger.warning(f"Missing fields: {missing}")
            return jsonify({"error": f"Missing fields: {missing}"}), 400

        recommendation = str(data["recommendation"])
        severity = str(data["severity"]).lower()
        
        # Validate severity
        valid_severities = ["high", "medium", "low"]
        if severity not in valid_severities:
            logger.warning(f"Invalid severity value: {severity}")
            return jsonify({"error": f"Severity must be one of {valid_severities}"}), 400

        recommendation_record = {
            "recommendation": recommendation,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Insert data into Supabase recommendations table
        response = supabase_client.table('recommendations').insert(recommendation_record).execute()
        inserted_id = response.data[0]['id']
        logger.info(f"Recommendation inserted with ID: {inserted_id}")

        return jsonify({
            "message": "Recommendation received and stored successfully",
            "id": str(inserted_id)
        }), 201

    except ValueError as ve:
        logger.error(f"Invalid data format: {ve}")
        return jsonify({"error": "Invalid data format"}), 400
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return jsonify({"error": "Internal server error"}), 500

# POST endpoint to receive sensor data
@app.route('/api/sensor_data', methods=['POST'])
def receive_sensor_data():
    try:
        data = request.get_json()
        if not data:
            logger.warning("No JSON data received")
            return jsonify({"error": "No data provided"}), 400

        required_fields = ["soil_moisture", "soil_temperature", "soil_humidity"]
        if not all(field in data for field in required_fields):
            missing = [field for field in required_fields if field not in data]
            logger.warning(f"Missing fields: {missing}")
            return jsonify({"error": f"Missing fields: {missing}"}), 400

        soil_moisture = float(data["soil_moisture"])
        soil_temperature = float(data["soil_temperature"])
        soil_humidity = float(data["soil_humidity"])
        # Generate random pH between 6.5 and 7.5
        soil_ph = float(np.random.uniform(6.5, 7.5))

        sensor_record = {
            "soil_moisture": soil_moisture,
            "soil_temperature": soil_temperature,
            "soil_humidity": soil_humidity,
            "soil_ph": soil_ph,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Insert data into Supabase
        response = supabase_client.table('sensor_data').insert(sensor_record).execute()
        inserted_id = response.data[0]['id']
        logger.info(f"Data inserted with ID: {inserted_id}")

        return jsonify({
            "message": "Data received and stored successfully",
            "id": str(inserted_id),
            "generated_soil_ph": soil_ph
        }), 201

    except ValueError as ve:
        logger.error(f"Invalid data format: {ve}")
        return jsonify({"error": "Invalid data format (values must be numbers)"}), 400
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return jsonify({"error": "Internal server error"}), 500

# GET endpoint to retrieve sensor data
@app.route('/api/sensor_data', methods=['GET'])
def get_sensor_data():
    try:
        response = supabase_client.table('sensor_data').select('*').order('timestamp', desc=True).limit(50).execute()
        data = response.data
        logger.info("Retrieved sensor data successfully")
        return jsonify(data), 200
    except Exception as e:
        logger.error(f"Error retrieving data: {e}")
        return jsonify({"error": "Internal server error"}), 500

# Function to close Supabase connection on app shutdown
def close_supabase_connection():
    logger.info("Supabase connection cleanup completed")

# Register shutdown hook
import atexit
atexit.register(close_supabase_connection)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))