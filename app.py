import streamlit as st
import json
import os
import requests
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd
import numpy as np
import altair as alt
import calendar
from gtts import gTTS 
import tempfile 
from smallestai.waves import WavesClient
import wikipedia

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")
RAPIDAPI_HOST = "booking-com15.p.rapidapi.com"
SMALLEST_API_KEY = os.environ.get("SMALLEST_API_KEY", "")

st.set_page_config(page_title="Rangyatra: Your Travel Planner", layout="wide")

def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("style.css")

# Page selection in sidebar
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Travel Planner", "Cultural Pulse Dashboard", "Whispering Walls"])

if page == "Travel Planner":
    st.title("✈️ Rangyatra: Your Personalized Travel Planner")
    st.markdown("Plan your next adventure with AI-powered recommendations!")

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
        interest = st.selectbox("🎯 Interest Type", ["Food", "Festivals", "Art", "Nature"])

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
                                        params = {"query": place.split("(")[0].strip()}
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

elif page == "Cultural Pulse Dashboard":
    # Cultural Pulse Dashboard Page
    st.title("🌍 Cultural Pulse Dashboard – Season & Crowd Trends")
    
    # Top Filters Bar
    st.header("Filter Insights")
    col1, col2, col3 = st.columns(3)
    with col1:
        regions = ["Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal"]
        selected_region = st.selectbox("Region", regions)
    with col2:
        months = ["January", "February", "March", "April", "May", "June",
                 "July", "August", "September", "October", "November", "December"]
        selected_month = st.selectbox("Month", months)
    with col3:
        main_interest = st.session_state.get('interest', 'Festivals')
        interests = ["Festivals", "Art", "Food", "Nature"]
        selected_interest = st.selectbox("Interest", interests, 
                                         index=interests.index(main_interest) 
                                         if main_interest in interests else 0)
    
    # Gemini API integration function
    def get_gemini_data(prompt):
        if not GEMINI_API_KEY:
            st.error("Gemini API Key is not set!")
            return None
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{
                "role": "user",
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {"responseMimeType": "application/json"}
        }
        try:
            response = requests.post(f"{GEMINI_API_URL}?key={GEMINI_API_KEY}", headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            if (result.get("candidates") 
                and result["candidates"][0].get("content") 
                and result["candidates"][0]["content"].get("parts")):
                data_text = result["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(data_text)
            else:
                st.error("Invalid response from Gemini API")
        except Exception as e:
            st.error(f"Error fetching data from Gemini API: {str(e)}")
        return None

    # Section 1 – Tourist Footfall using Gemini API
    st.subheader("📈 Tourist Footfall Over the Year")
    with st.spinner("Fetching tourist footfall data..."):
        prompt_fp = f"""
        Provide monthly tourist footfall data for the region "{selected_region}" for the year 2024.
        The data should be a JSON with a key "footfall_data" that is a list of 12 objects.
        Each object must contain:
        - "month": a three-letter abbreviation (e.g., "Jan", "Feb", etc.)
        - "visitors": an integer value representing the number of visitors.
        """
        gemini_fp = get_gemini_data(prompt_fp)
    if gemini_fp and "footfall_data" in gemini_fp:
        footfall_data = pd.DataFrame(gemini_fp["footfall_data"])
        # Sort the months properly
        month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        footfall_data['month'] = pd.Categorical(footfall_data['month'], categories=month_order, ordered=True)
        footfall_data = footfall_data.sort_values('month')
        st.line_chart(footfall_data.set_index("month"), use_container_width=True)
    else:
        st.error("Tourist footfall data not available.")

    # Section 2 – Crowd Comparison using Gemini API
    st.subheader("🏙️ Crowd Distribution Insights")
    col1, col2 = st.columns(2)
    
    # Busy Locations using Gemini API
    with col1:
        st.markdown("**Most Busy Locations**")
        with st.spinner("Fetching most busy locations..."):
            prompt_busy = f"""
            Provide a list of 5 most busy tourist locations in the region "{selected_region}" for people interested in "{selected_interest}".
            The output must be a JSON with a key STRICTLY EQUAL TO "busy_places", which is a list of objects.
            Each object should include:
            - "location": name of the location.
            - "crowd_percentage": an integer indicating the crowd level percentage.
            """
            gemini_busy = get_gemini_data(prompt_busy)
        if gemini_busy and "busy_places" in gemini_busy:
            busy_places = pd.DataFrame(gemini_busy["busy_places"])
            busy_places = busy_places.rename(columns={"location": "Location", "crowd_percentage": "Crowd %"})
            st.bar_chart(busy_places.set_index('Location'))
        else:
            st.error("Busy locations data not available.")
    
    # Quiet Locations using Gemini API
    with col2:
        st.markdown("**Hidden Gems**")
        with st.spinner("Fetching hidden gems..."):
            prompt_quiet = f"""
            Provide a list of 5 lesser-known (hidden gem) tourist locations in the region "{selected_region}" for those interested in "{selected_interest}".
            The output must be a JSON with a key "quiet_places", which is a list of objects.
            Each object should include:
            - "location": name of the location.
            - "crowd_percentage": an integer indicating the crowd level percentage.
            """
            gemini_quiet = get_gemini_data(prompt_quiet)
        if gemini_quiet and "quiet_places" in gemini_quiet:
            quiet_places = pd.DataFrame(gemini_quiet["quiet_places"])
            quiet_places = quiet_places.rename(columns={"location": "Location", "crowd_percentage": "Crowd %"})
            st.bar_chart(quiet_places.set_index('Location'))
        else:
            st.error("Hidden gems data not available.")
    
    # Interaction Note
    st.markdown("""
    <div style='background: #f8f9fa; padding: 15px; border-radius: 10px; margin-top: 20px;'>
        🔍 <strong>Pro Tip:</strong> Adjust the filters above to discover seasonal patterns 
        and optimize your travel timing!
    </div>
    """, unsafe_allow_html=True)

else: # Whispering Walls Page
    st.title("🗣️ Whispering Walls – Audio Stories of Heritage Sites")
    st.markdown("Click on a cultural site to hear its story, narrated like a local guide!")

    cultural_sites_list = [
        "Sanchi Stupa",
        "Hampi",
        "Taj Mahal",
        "Mysore Palace",
        "Qutub Minar",
        "Red Fort",
        "Victoria Memorial (Kolkata)",
        "Konark Sun Temple",
        "Khajuraho Temples",
        "Fatehpur Sikri"
    ]

    selected_site = st.selectbox("Choose or type a cultural site:", cultural_sites_list + [""]) # Add empty string for typing

    if selected_site == "":
        typed_site = st.text_input("Or type the name of a cultural site:", "")
        if typed_site:
            selected_site = typed_site
        else:
            selected_site = None
    elif selected_site is None:
        pass # No site selected yet

    if selected_site:
        st.subheader(f"Exploring {selected_site}")

        # Function to get a simple image URL (very basic, might not always work well)
        def get_image_url(query):
            try:
                page = wikipedia.page(query)
                for img_url in page.images:
                    if img_url.lower().endswith(('.jpg', '.jpeg', '.png')):
                        return img_url
                return None
            except Exception as e:
                print(f"Error fetching image from Wikipedia: {e}")
                return None

        image_url = get_image_url(selected_site)
        if image_url:
            st.image(image_url, caption=selected_site, use_container_width=True)
        else:
            st.warning(f"Could not find a suitable image for {selected_site}.")

        if st.button(f"Listen to the story of {selected_site} 🔊", type="primary"):
            if not GEMINI_API_KEY:
                st.error("Gemini API Key is not set! Please set the GEMINI_API_KEY environment variable.")
            else:
                with st.spinner(f"Generating audio story for {selected_site} using AI..."):
                    try:
                        prompt = f"""
                        As a knowledgeable local guide, tell a short and engaging audio story (around 15 seconds when spoken) about the cultural significance, history, and key features of {selected_site} in a way that would captivate a visitor. Only write raw story text without any additional commentary or instructions.
                        The story should be informative yet concise, suitable for a quick audio narration.
                        """
                        headers = {"Content-Type": "application/json"}
                        payload = {
                            "contents": [{
                                "role": "user",
                                "parts": [{"text": prompt}]
                            }],
                            "generationConfig": {"maxOutputTokens": 500} # Limit the response length
                        }
                        response = requests.post(f"{GEMINI_API_URL}?key={GEMINI_API_KEY}", headers=headers, json=payload)
                        response.raise_for_status()
                        result = response.json()
                        if result.get("candidates") and result["candidates"][0].get("content") and result["candidates"][0]["content"].get("parts"):
                            story_text = result["candidates"][0]["content"]["parts"][0]["text"]

                            # Synthesize audio using WavesClient
                            waves_client = WavesClient(api_key=SMALLEST_API_KEY)
                            waves_client.synthesize(
                                text=story_text,
                                save_as="audio_story.wav",
                            )

                            with open("audio_story.wav", "rb") as audio_file:
                                audio_bytes = audio_file.read()
                            st.audio(audio_bytes, format="audio/wav", start_time=0)
                            os.remove("audio_story.wav")

                            st.success("Enjoy the story!")
                            st.markdown("---")
                            st.subheader("Story Transcript:")
                            st.write(story_text) # Display the generated text as well

                        else:
                            st.error("Failed to generate the audio story.")

                    except requests.exceptions.RequestException as e:
                        st.error(f"Error communicating with Gemini API: {e}")
                    except json.JSONDecodeError:
                        st.error("Failed to decode Gemini API response.")
                    except Exception as e:
                        st.error(f"An unexpected error occurred: {e}")

    st.markdown("""
    <div style='background: #e6f7ff; padding: 15px; border-radius: 10px; margin-top: 20px;'>
        ✨ <strong>Why "Whispering Walls" is unique:</strong><br>
        <ul>
            <li><strong>AI-Powered Stories:</strong> Engaging narratives about heritage sites generated by AI.</li>
            <li><strong>Immersive & Inclusive:</strong> Experience history through audio, great for all users.</li>
            <li><strong>Flexible Exploration:</strong> Discover stories of both well-known and lesser-known sites.</li>
        </ul>
        <br>
    </div>
    """, unsafe_allow_html=True)