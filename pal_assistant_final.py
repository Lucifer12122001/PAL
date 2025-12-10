import datetime
import os
import sys
import subprocess
import webbrowser
import sqlite3
import smtplib 
from email.message import EmailMessage 
from waitress import serve


# Machine Learning & NLP Imports
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import LabelEncoder
from flask import Flask, request, jsonify




# --- 0. SECURITY & CONFIG ---
SECRET_NAME = "CIM"
MASTER_EMAIL = "dhiyaneshpandi@gmail.com"
MASTER_PHONE = "+916369487851"
SESSION_DURATION_MINUTES = 30 
DB_NAME = 'pal_memory.db'


# !!! ACTION REQUIRED: REPLACE THESE WITH YOUR GMAIL APP PASSWORD CREDENTIALS !!!
SENDER_EMAIL = "your_sender_email@gmail.com"
SENDER_APP_PASSWORD = "YOUR_GMAIL_APP_PASSWORD" 
 
# --- GLOBAL MEMORY AND STATE ---
IS_AUTHENTICATED = False
SESSION_START_TIME = None
CONTEXT_MEMORY = {'last_intent': None, 'last_entity': None}
DEVICE_TYPE = None # Set during interactive startup




# --- ML/NLP SETUP ---
try:
    nlp = spacy.load("en_core_web_sm")
    
    # Training Data (Intent Classification, including new intents)
    texts = [
        "hello there", "hi", "greetings",
        "what is the time now", "tell me the current time",
        "what is the weather in London", "how is the climate in Paris",
        "how about tomorrow", "how about there",
        "open google", "launch google",
        "P.A.L Update yourself", "run update", "install new code",
        "my favorite city is tokyo", "remember my name is dave", "i like pizza",
        "bye", "exit the program", "quit assistant"
    ]
    intents = [
        'greet', 'greet', 'greet',
        'get_time', 'get_time',
        'get_weather', 'get_weather',
        'contextual_followup', 'contextual_followup',
        'open_app', 'open_app',
        'update_self', 'update_self', 'update_self',
        'set_preference', 'set_preference', 'set_preference',
        'exit', 'exit', 'exit'
    ]
    
    label_encoder = LabelEncoder()
    y_labels = label_encoder.fit_transform(intents)
    model = make_pipeline(TfidfVectorizer(), MultinomialNB())
    model.fit(texts, y_labels)
    
except Exception as e:
    print(f"Error during NLP setup: {e}")
    print("Please check imports and dependencies.")




# --- DATABASE FUNCTIONS ---


def initialize_database():
    """Creates the preferences table if it doesn't exist."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS preferences (key TEXT PRIMARY KEY, value TEXT)")
        conn.commit()
        conn.close()
        print(f"[DB] Initialized database: {DB_NAME}.")
    except Exception as e:
        print(f"[DB ERROR] Could not initialize database: {e}")


def save_preference(key, value):
    """Saves a key-value preference pair."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO preferences (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def get_preference(key):
    """Retrieves a preference value."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM preferences WHERE key = ?", (key,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except Exception:
        return None


# --- SECURITY AND ALERT FUNCTIONS ---


def send_email_alert():
    """Sends a security alert email via SMTP."""
    try:
        msg = EmailMessage()
        msg['Subject'] = '!!! P.A.L. SECURITY ALERT !!!'
        msg['From'] = SENDER_EMAIL
        msg['To'] = MASTER_EMAIL
        msg.set_content(f"Unauthorized access attempt to P.A.L. at {datetime.datetime.now()}.")


        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
            server.send_message(msg)
            print(f"[EMAIL ALERT] Sent security alert to {MASTER_EMAIL}.")
            return True
    except Exception as e:
        print(f"[EMAIL ALERT FAILED] Could not send email. Error: {e}")
        return False


def send_sms_alert():
    """Simulates/sends an SMS alert."""
    print(f"[SMS ALERT] SMS Alert triggered. Message: 'Someone trying to access your AI !!' sent to {MASTER_PHONE}.")


def conditional_alert():
    """Triggers alerts based on the DEVICE_TYPE set at startup."""
    
    send_email_alert()
    
    if DEVICE_TYPE and DEVICE_TYPE.lower() == 'mobile':
        send_sms_alert()
        print(f"[CONDITIONAL ALERT] Device is Mobile. Sending SMS + Email.")
    else:
        print(f"[CONDITIONAL ALERT] Device is Laptop. Sending Email only.")


def check_session_validity():
    """Checks if the 30-minute session has expired."""
    global IS_AUTHENTICATED, SESSION_START_TIME
    
    if IS_AUTHENTICATED and SESSION_START_TIME:
        elapsed_time = datetime.datetime.now() - SESSION_START_TIME
        if elapsed_time.total_seconds() > (SESSION_DURATION_MINUTES * 60):
            IS_AUTHENTICATED = False
            SESSION_START_TIME = None
            print(f"\n[SYSTEM ALERT] Session expired. System has gone to OFF mode.")
            return False 
    return IS_AUTHENTICATED 




# --- CORE ASSISTANT LOGIC ---


def assistant_response(user_input):
    global CONTEXT_MEMORY


    predicted_label_index = model.predict([user_input])[0]
    predicted_intent = label_encoder.inverse_transform([predicted_label_index])[0]
    doc = nlp(user_input)


    # --- 1. Self-Update Logic ---
    if predicted_intent == 'update_self':
        # Execute the separate update script in the background
        # It will handle the file replacement and restart the entire app
        subprocess.Popen([sys.executable, 'update_script.py'])
        return "Acknowledged, Master. P.A.L. is initiating self-update and will restart shortly to apply changes."


    # --- 2. Memory/Preference Logic ---
    if predicted_intent == 'set_preference':
        user_input_lower = user_input.lower()
        
        if 'city is' in user_input_lower:
            key = 'favorite_city'
            value = user_input_lower.split('city is', 1)[1].strip().title()
        elif 'my name is' in user_input_lower:
            key = 'user_name'
            value = user_input_lower.split('my name is', 1)[1].strip().title()
        else:
            return "Master, I don't know how to save that preference yet. Try saying 'My favorite city is [City]'."
            
        if save_preference(key, value):
            return f"Understood, Master. I have permanently saved your '{key}' as '{value}'."
        else:
            return "Master, I encountered a system error while trying to save your preference."




    # --- 3. Normal Intents ---
    if predicted_intent == 'greet':
        user_name = get_preference('user_name')
        if user_name:
            return f"Hello again, Master {user_name}! I am P.A.L. 5.3, ready for your command."
        return "Greetings, Master. I am P.A.L. 5.3, standing by for your command."


    elif predicted_intent == 'get_time':
        now = datetime.datetime.now()
        current_time = now.strftime("%I:%M:%S %p")
        tz = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
        return f"The current time is **{current_time}** (synced with your device timezone: **{tz}**), Master."
    
    elif predicted_intent == 'get_weather':
        location = extract_entity(doc, ['GPE', 'LOC'])
        
        # Use saved preference as fallback location
        if not location:
            location = get_preference('favorite_city')
                
        if location:
            CONTEXT_MEMORY['last_intent'] = 'get_weather'
            CONTEXT_MEMORY['last_entity'] = location
            return f"Checking the weather for **{location}**. (Simulated: It is 18°C and cloudy.)"
        else:
            return "I need a location to check the weather. Where should I check?"
            
    elif predicted_intent == 'contextual_followup':
        if CONTEXT_MEMORY['last_intent'] == 'get_weather' and CONTEXT_MEMORY['last_entity']:
            location = CONTEXT_MEMORY['last_entity']
            return f"As you wish, Master. Checking the **forecast for tomorrow** in **{location}**."
        return "I do not have enough recent context, Master."


    elif predicted_intent == 'open_app':
        webbrowser.open("https://www.google.com")
        return "Opening Google now, Master."
        
    elif predicted_intent == 'exit':
        return "Acknowledged, Master. Shutting down systems."
        
    return f"Command received: '{user_input}'. Executing command, Master."




# --- 4. FLASK API IMPLEMENTATION ---


app = Flask(__name__)


# --- Authentication Endpoint ---
@app.route('/auth', methods=['POST'])
def authenticate():
    global IS_AUTHENTICATED, SESSION_START_TIME
    data = request.get_json()
    user_secret = data.get('secret_name', '').strip().upper()
    
    if user_secret == SECRET_NAME:
        IS_AUTHENTICATED = True
        SESSION_START_TIME = datetime.datetime.now()
        global CONTEXT_MEMORY
        CONTEXT_MEMORY = {'last_intent': None, 'last_entity': None}
        return jsonify({"status": "Success", "message": "Access Granted. Welcome, Master. Session timer started (30 minutes)."}), 200
    else:
        conditional_alert()
        return jsonify({"status": "Failed", "message": "Authentication failed. Access is restricted and alert(s) have been sent."}), 401


# --- Main Assistant Endpoint ---
@app.route('/command', methods=['POST'])
def handle_command():
    
    if not check_session_validity():
        return jsonify({"response": "System is currently in OFF mode. Please re-authenticate."}), 403
        
    data = request.get_json()
    user_input = data.get('query', '')
    
    response_text = assistant_response(user_input)
    
    return jsonify({
        "response": response_text,
        "security_status": "Master"
    }), 200




# --- 5. STARTUP PROCEDURE ---


91% of storage used … If you run out, you can't create, edit, and upload files. Share 100 GB of storage with your family members for ₹59 for 3 months ₹130.

def startup_procedure():
    global IS_AUTHENTICATED, DEVICE_TYPE

    # A. Device Type Selection
    while DEVICE_TYPE not in ['MOBILE', 'LAPTOP']:
        # CHANGE: Use sys.stdin.readline() for robust console input
        print("P.A.L.: Is this instance running on a [Mobile] or [Laptop]? ", end='')
        sys.stdout.flush()
        user_choice = sys.stdin.readline().strip().upper() 

        if user_choice in ['MOBILE', 'LAPTOP']:
            DEVICE_TYPE = user_choice
        else:
            print("P.A.L.: Invalid input. Please type 'Mobile' or 'Laptop'.")

    print(f"\nP.A.L.: Device Type set to {DEVICE_TYPE}. Initiating Security Check.")

    # B. Security Handshake
    while not IS_AUTHENTICATED:
        # CHANGE: Use sys.stdin.readline() here too
        print(f"P.A.L.: What was your Secret Name? ", end='')
        sys.stdout.flush()
        user_input = sys.stdin.readline().strip().upper()

        if user_input == SECRET_NAME:
            IS_AUTHENTICATED = True
            initialize_database()
            print("\nP.A.L.: Access Granted. Welcome, Master. Starting API.")
        else:
            conditional_alert()
            print("P.A.L.: Security failure. Please try again.")

if __name__ == "__main__":
    startup_procedure()
    if IS_AUTHENTICATED:
        print(f"\n* Starting P.A.L. API using Waitress on http://127.0.0.1:8080/ *")

        serve(app, host='0.0.0.0', port=8080)
