import streamlit as st
import json
import os
import requests
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd
import numpy as np
import altair as alt

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")
RAPIDAPI_HOST = "booking-com15.p.rapidapi.com"

st.set_page_config(page_title="Rangyatra: Your Travel Planner", layout="wide")

st.title("✈️ Rangyatra: Your Personalized Travel Planner")
st.markdown("Plan your next adventure with AI-powered recommendations!")

def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("style.css")

# Input fields
st.header("Tell us about your trip:")
col1, col2, col3, col4 = st.columns(4)

with col1:
    current_location = st.text_input("📍 Current Location", "Bengaluru, India")

with col2:
    destination = st.text_input("🗺️ Destination", "Goa, India")

with col3:
    num_days = st.number_input("🗓️ Number of Days", min_value=1, max_value=30, value=5)

with col4:
    interest = st.selectbox("🎯 Interest Type", ["Festivals", "Art", "Food", "Nature"])

if st.button("✨ Generate Travel Plan", type="primary"):
    if not GEMINI_API_KEY:
        st.error("Gemini API Key is not set! Please set the GEMINI_API_KEY environment variable.")
    else:
        with st.spinner("Generating your personalized travel plan... This might take a moment!"):
            try:
                prompt = f"""
                You are an expert travel planner. I need a detailed travel plan for a trip from {current_location} to {destination} for {num_days} days focusing on {interest}.
                Please provide the information in a structured JSON format.

                The JSON should have the following keys:
                - "itinerary": An array of objects, each representing a day. Each day object should have:
                    - "day": Integer (e.g., 1, 2)
                    - "theme": String (e.g., "Beach Exploration", "Cultural Immersion")
                    - "activities": An array of strings describing activities for that day.
                    - "notes": String for any special considerations or tips for the day.
                - "recommended_places": An array of 3-5 strings listing key places in {destination} relevant to {interest}.
                - "food_outlets": An array of strings, listing 2-3 recommended restaurants with cuisine description.
                - "clothing_advice": A string providing clothing recommendations based on weather and activities.
                - "rush_info": A string with advice on crowded periods and avoidance tips.
                - "disclaimer": A string stating that real-time data requires external APIs.

                Ensure the JSON is valid and complete. Do not include any text outside the JSON block.
                """

                headers = {"Content-Type": "application/json"}
                payload = {
                    "contents": [{
                        "role": "user",
                        "parts": [{"text": prompt}]
                    }],
                    "generationConfig": {"responseMimeType": "application/json"}
                }

                response = requests.post(f"{GEMINI_API_URL}?key={GEMINI_API_KEY}", headers=headers, json=payload)
                response.raise_for_status()

                result = response.json()
                if result.get("candidates") and result["candidates"][0].get("content") and result["candidates"][0]["content"].get("parts"):
                    gemini_response_text = result["candidates"][0]["content"]["parts"][0]["text"]
                    travel_plan = json.loads(gemini_response_text)

                    st.success("Travel plan generated successfully!")
                    st.subheader(f"✨ Your {num_days}-Day {interest} Trip to {destination} ✨")

                    # Display Itinerary
                    st.markdown("---")
                    st.header("🗓️ Itinerary")
                    for day_plan in travel_plan.get("itinerary", []):
                        st.subheader(f"Day {day_plan.get('day')}: {day_plan.get('theme', '')}")
                        for activity in day_plan.get("activities", []):
                            st.write(f"- {activity}")
                        if day_plan.get("notes"):
                            st.info(f"📌 Notes: {day_plan['notes']}")
                        st.markdown("---")

                    # Display Recommended Places and Hotels
                    if "recommended_places" in travel_plan and travel_plan["recommended_places"]:
                        st.header("🏨 Recommended Places & Hotels")
                        for place in travel_plan["recommended_places"]:
                            st.subheader(f"Places to visit and stay near {place}")
                            
                            if RAPIDAPI_KEY:
                                try:
                                    # Search hotels
                                    url = f"https://{RAPIDAPI_HOST}/api/v1/hotels/searchDestination"
                                    params = {"query": place}
                                    headers = {
                                        "x-rapidapi-key": RAPIDAPI_KEY,
                                        "x-rapidapi-host": RAPIDAPI_HOST
                                    }
                                    resp = requests.get(url, headers=headers, params=params)
                                    resp.raise_for_status()
                                    hotels = resp.json().get("data", [])[:3]  # Show top 3

                                    if hotels:
                                        for hotel in hotels:
                                            if hotel.get("search_type") == "hotel":
                                                col1, col2 = st.columns([1, 3])
                                                with col1:
                                                    st.image(hotel.get("image_url", ""), width=150)
                                                with col2:
                                                    st.write(f"**{hotel.get('name')}**")
                                                    st.caption(hotel.get("label", ""))
                                                    if st.button(f"Show Photos 🖼️", 
                                                               key=f"photos_{hotel.get('dest_id')}"):
                                                        with st.spinner("Loading photos..."):
                                                            photo_url = f"https://{RAPIDAPI_HOST}/api/v1/hotels/getHotelPhotos"
                                                            photo_resp = requests.get(
                                                                photo_url,
                                                                headers=headers,
                                                                params={"hotel_id": hotel.get("dest_id")}
                                                            )
                                                            if photo_resp.ok:
                                                                photos = photo_resp.json().get("data", [])[:3]
                                                                if photos:
                                                                    st.image([p.get("url") for p in photos], 
                                                                            width=200, 
                                                                            caption=[f"Photo {i+1}" for i in range(len(photos))])
                                                                else:
                                                                    st.warning("No photos available")
                                                            else:
                                                                st.error("Failed to load photos")
                                                st.markdown("---")
                                    else:
                                        st.warning(f"No hotels found near {place}")
                                except Exception as e:
                                    st.error(f"Error fetching hotels: {str(e)}")
                            else:
                                st.warning("RapidAPI key missing - cannot show hotel recommendations")

                    # Display other sections
                    st.header("🍽️ Food Recommendations")
                    for food in travel_plan.get("food_outlets", []):
                        st.write(f"- {food}")

                    st.header("👕 Packing Advice")
                    st.info(travel_plan.get("clothing_advice", ""))

                    st.header("🚦 Crowd Management Tips")
                    st.warning(travel_plan.get("rush_info", ""))

                    # Crowd Calendar Visualization
                    st.header("📅 Estimated Crowd Calendar")
                    dates = pd.date_range(start=datetime.today(), periods=30, freq='D')
                    df = pd.DataFrame({
                        "Date": dates,
                        "Crowd Level": np.random.randint(20, 100, size=len(dates))
                    })
                    chart = alt.Chart(df).mark_line().encode(
                        x='Date:T',
                        y='Crowd Level:Q',
                        tooltip=['Date', 'Crowd Level']
                    ).interactive()
                    st.altair_chart(chart, use_container_width=True)

                else:
                    st.error("Failed to generate valid travel plan")

            except json.JSONDecodeError:
                st.error("Failed to parse travel plan response")
            except Exception as e:
                st.error(f"Error generating plan: {str(e)}")