import streamlit as st
import json
import os
import requests # For making API calls to Gemini
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()  

# --- Firebase/Snowflake Placeholder (for demonstration) ---
# In a real application, you would initialize Firebase/Snowflake here.
# For this hackathon, we'll simulate the connection and data saving.

# Global variables for Firebase/Snowflake (as per instructions)
# In a real Canvas environment, these would be provided at runtime.
# For local testing, you might set dummy values or comment them out.
__app_id = os.environ.get('APP_ID', 'rangyatra-hackathon-app')
__firebase_config = os.environ.get('FIREBASE_CONFIG', '{}')
__initial_auth_token = os.environ.get('INITIAL_AUTH_TOKEN', None)

# Simulate Firebase/Firestore initialization and user ID
# In a real Firebase setup, you'd use firebase_admin or similar.
# For this example, we'll just print to console.
def init_firestore_and_auth():
    st.sidebar.write("Simulating Firebase/Firestore initialization...")
    st.sidebar.write(f"App ID: {__app_id}")
    st.sidebar.write(f"Firebase Config: {__firebase_config}")
    st.sidebar.write(f"Initial Auth Token: {'Present' if __initial_auth_token else 'Not Present'}")
    # In a real app:
    # app = initializeApp(firebaseConfig)
    # db = getFirestore(app)
    # auth = getAuth(app)
    # if __initial_auth_token:
    #     signInWithCustomToken(auth, __initial_auth_token)
    # else:
    #     signInAnonymously(auth)
    # userId = auth.currentUser?.uid || crypto.randomUUID()
    # st.session_state['user_id'] = userId
    st.session_state['user_id'] = "simulated_user_id_12345" # Dummy user ID for demonstration
    st.sidebar.success(f"Simulated User ID: {st.session_state['user_id']}")

def save_travel_plan_to_snowflake(plan_data):
    """
    Simulates saving a travel plan to Snowflake.
    In a real application, you would use a Snowflake connector here.
    """
    st.sidebar.write("Simulating saving travel plan to Snowflake...")
    # Example of how you might structure data for Snowflake
    # This would typically involve a database connection and SQL INSERT
    st.sidebar.json({
        "app_id": __app_id,
        "user_id": st.session_state.get('user_id', 'unknown'),
        "timestamp": datetime.now().isoformat(),
        "plan_data": plan_data
    })
    st.sidebar.success("Travel plan simulated to be saved to Snowflake!")


GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "") 
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# --- Streamlit UI ---
st.set_page_config(page_title="Rangyatra: Your Travel Planner", layout="wide")

st.title("✈️ Rangyatra: Your Personalized Travel Planner")
st.markdown("Plan your next adventure with AI-powered recommendations!")

# Initialize session state for user ID if not already set
if 'user_id' not in st.session_state:
    init_firestore_and_auth()

# Input fields
st.header("Tell us about your trip:")
col1, col2, col3 = st.columns(3)

with col1:
    current_location = st.text_input("📍 Current Location", "Bengaluru, India")

with col2:
    destination = st.text_input("🗺️ Destination", "Goa, India")

with col3:
    num_days = st.number_input("🗓️ Number of Days", min_value=1, max_value=30, value=5)

# Generate Plan Button
if st.button("✨ Generate Travel Plan", type="primary"):
    if not GEMINI_API_KEY:
        st.error("Gemini API Key is not set! Please set the `GEMINI_API_KEY` environment variable or replace the placeholder in the code.")
    else:
        with st.spinner("Generating your personalized travel plan... This might take a moment!"):
            try:
                prompt = f"""
                You are an expert travel planner. I need a detailed travel plan for a trip from {current_location} to {destination} for {num_days} days.
                Please provide the information in a structured JSON format.

                The JSON should have the following keys:
                - "itinerary": An array of objects, each representing a day. Each day object should have:
                    - "day": Integer (e.g., 1, 2)
                    - "theme": String (e.g., "Beach Exploration", "Cultural Immersion")
                    - "activities": An array of strings describing activities for that day.
                    - "notes": String for any special considerations or tips for the day.
                - "hotels": An array of strings, listing 2-3 recommended hotel names/types with a brief reason.
                - "food_outlets": An array of strings, listing 2-3 recommended food outlets/restaurants with a brief description of cuisine.
                - "clothing_advice": A string providing advice on clothing types to pack, considering the weather in {current_location} and {destination} and the time of year (you can make reasonable assumptions about typical weather for these locations).
                - "rush_info": A string providing general advice on typical rush hours or crowded periods for popular attractions in {destination}, and tips to avoid them.
                - "disclaimer": A string stating that real-time data for rush and hotel availability requires external APIs.

                Ensure the JSON is valid and complete. Do not include any text outside the JSON block.
                """

                headers = {
                    "Content-Type": "application/json"
                }
                payload = {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [{"text": prompt}]
                        }
                    ],
                    "generationConfig": {
                        "responseMimeType": "application/json"
                    }
                }

                response = requests.post(f"{GEMINI_API_URL}?key={GEMINI_API_KEY}", headers=headers, json=payload)
                response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)

                result = response.json()
                # st.write(result) # For debugging raw response

                if result.get("candidates") and result["candidates"][0].get("content") and result["candidates"][0]["content"].get("parts"):
                    gemini_response_text = result["candidates"][0]["content"]["parts"][0]["text"]
                    # st.write(gemini_response_text) # For debugging raw JSON string

                    # Parse the JSON string
                    travel_plan = json.loads(gemini_response_text)

                    st.success("Travel plan generated successfully!")

                    # Display the plan
                    st.subheader(f"✨ Your {num_days}-Day Trip to {destination} ✨")

                    # Itinerary
                    st.markdown("---")
                    st.header("🗓️ Itinerary")
                    for day_plan in travel_plan.get("itinerary", []):
                        st.subheader(f"Day {day_plan.get('day', 'N/A')}: {day_plan.get('theme', 'No Theme')}")
                        if day_plan.get('activities'):
                            for activity in day_plan['activities']:
                                st.write(f"- {activity}")
                        if day_plan.get('notes'):
                            st.info(f"Notes: {day_plan['notes']}")
                        st.markdown("---")

                    # Hotels
                    st.header("🏨 Hotel Recommendations")
                    if travel_plan.get("hotels"):
                        for hotel in travel_plan["hotels"]:
                            st.write(f"- {hotel}")
                    else:
                        st.write("No specific hotel recommendations available.")

                    # Food Outlets
                    st.header("🍽️ Food Outlet Recommendations")
                    if travel_plan.get("food_outlets"):
                        for food in travel_plan["food_outlets"]:
                            st.write(f"- {food}")
                    else:
                        st.write("No specific food outlet recommendations available.")

                    # Clothing Advice
                    st.header("👕 Clothing Advice")
                    st.info(travel_plan.get("clothing_advice", "No specific clothing advice available."))

                    # Rush Info
                    st.header("🚦 Real-time Rush Information (General Advice)")
                    st.warning(travel_plan.get("rush_info", "No specific rush information available."))
                    st.caption("*(Note: Real-time rush data would require integration with services like Google Maps Places API.)*")


                    # Disclaimer
                    st.markdown("---")
                    st.caption(travel_plan.get("disclaimer", "Disclaimer: This plan is AI-generated. Real-time data and booking require external API integrations."))

                    # Simulate saving to Snowflake
                    save_travel_plan_to_snowflake(travel_plan)

                else:
                    st.error("Could not get a valid response from Gemini. Please try again.")
                    st.json(result) # Show the raw response for debugging

            except json.JSONDecodeError:
                st.error("Failed to parse JSON response from Gemini. The response might not be in the expected format.")
                st.write("Raw Gemini response (attempted to parse):")
                st.code(gemini_response_text)
            except requests.exceptions.RequestException as e:
                st.error(f"Error communicating with Gemini API: {e}")
                st.write("Please check your API key and network connection.")
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")

st.markdown("---")
st.markdown("### How to run this application:")
st.markdown("1.  **Save the code:** Save the above code as `app.py`.")
st.markdown("2.  **Install dependencies:** `pip install streamlit requests`")
st.markdown("3.  **Get your Gemini API Key:** Visit [Google AI Studio](https://aistudio.google.com/app/apikey) to get your API key.")
st.markdown("4.  **Set API Key:** Replace `""` with your actual API key in the `GEMINI_API_KEY` variable in the code, or set it as an environment variable before running: `export GEMINI_API_KEY='YOUR_API_KEY'`")
st.markdown("5.  **Run the app:** `streamlit run app.py`")
