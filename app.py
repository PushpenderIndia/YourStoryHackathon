import streamlit as st
import json
import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

st.set_page_config(page_title="Rangyatra: Your Travel Planner", layout="wide")

st.title("✈️ Rangyatra: Your Personalized Travel Planner")
st.markdown("Plan your next adventure with AI-powered recommendations!")

def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("style.css")

# Input fields
st.header("Tell us about your trip:")
col1, col2, col3 = st.columns(3)

with col1:
    current_location = st.text_input("📍 Current Location", "Bengaluru, India")

with col2:
    destination = st.text_input("🗺️ Destination", "Goa, India")

with col3:
    num_days = st.number_input("🗓️ Number of Days", min_value=1, max_value=30, value=5)

if st.button("✨ Generate Travel Plan", type="primary"):
    if not GEMINI_API_KEY:
        st.error("Gemini API Key is not set! Please set the GEMINI_API_KEY environment variable.")
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
                - "clothing_advice": A string providing advice on clothing types to pack considering the weather in {current_location} and {destination} and the time of year.
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
                response.raise_for_status()  # Raise error for bad responses

                result = response.json()

                if result.get("candidates") and result["candidates"][0].get("content") and result["candidates"][0]["content"].get("parts"):
                    gemini_response_text = result["candidates"][0]["content"]["parts"][0]["text"]

                    travel_plan = json.loads(gemini_response_text)

                    st.success("Travel plan generated successfully!")
                    st.subheader(f"✨ Your {num_days}-Day Trip to {destination} ✨")

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

                    st.header("🏨 Hotel Recommendations")
                    if travel_plan.get("hotels"):
                        for hotel in travel_plan["hotels"]:
                            st.write(f"- {hotel}")
                    else:
                        st.write("No specific hotel recommendations available.")

                    st.header("🍽️ Food Outlet Recommendations")
                    if travel_plan.get("food_outlets"):
                        for food in travel_plan["food_outlets"]:
                            st.write(f"- {food}")
                    else:
                        st.write("No specific food outlet recommendations available.")

                    st.header("👕 Clothing Advice")
                    st.info(travel_plan.get("clothing_advice", "No specific clothing advice available."))

                    st.header("🚦 Rush Information (General Advice)")
                    st.warning(travel_plan.get("rush_info", "No specific rush information available."))
                    st.caption("*(Note: Real-time rush data would require integration with external APIs.)*")

                    st.markdown("---")
                    st.caption(travel_plan.get("disclaimer", "Disclaimer: This plan is AI-generated. Real-time data and booking require additional integrations."))

                else:
                    st.error("Could not get a valid response from Gemini. Please try again.")
                    st.json(result)  # For debugging

            except json.JSONDecodeError:
                st.error("Failed to parse JSON response from Gemini. The response might not be in the expected format.")
                st.code(gemini_response_text)
            except requests.exceptions.RequestException as e:
                st.error(f"Error communicating with Gemini API: {e}")
                st.write("Please check your API key and network connection.")
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")
