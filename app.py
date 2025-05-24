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
from fpdf import FPDF
import io

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

# local_css("style.css")

# Page selection in sidebar
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Travel Planner", "Cultural Pulse Dashboard", "Whispering Walls", "Arts & Culture Hub", "India's Cultural Grid"])

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
    
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "Cultural Pulse Dashboard Report", ln=1, align="C")
        pdf.ln(5)
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, f"Region: {selected_region}", ln=1)
        pdf.cell(0, 10, f"Month: {selected_month}", ln=1)
        pdf.cell(0, 10, f"Interest: {selected_interest}", ln=1)
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "1. Tourist Footfall Over the Year", ln=1)
        pdf.set_font("Arial", size=12)
        if gemini_fp and "footfall_data" in gemini_fp:
            for row in gemini_fp["footfall_data"]:
                pdf.cell(0, 8, f"{row.get('month', '')}: {row.get('visitors', '')} visitors", ln=1)
        else:
            pdf.cell(0, 8, "No data available", ln=1)
        pdf.ln(8)
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "2. Most Busy Locations", ln=1)
        pdf.set_font("Arial", size=12)
        if gemini_busy and "busy_places" in gemini_busy:
            for item in gemini_busy["busy_places"]:
                pdf.cell(0, 8, f"{item.get('location', '')}: {item.get('crowd_percentage', '')}% crowd", ln=1)
        else:
            pdf.cell(0, 8, "No data available", ln=1)
        pdf.ln(8)
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "3. Hidden Gems", ln=1)
        pdf.set_font("Arial", size=12)
        if gemini_quiet and "quiet_places" in gemini_quiet:
            for item in gemini_quiet["quiet_places"]:
                pdf.cell(0, 8, f"{item.get('location', '')}: {item.get('crowd_percentage', '')}% crowd", ln=1)
        else:
            pdf.cell(0, 8, "No data available", ln=1)
            
        # Generate PDF in memory
        pdf_output = pdf.output(dest='S').encode('latin1')
        st.markdown("<div style='padding-top:20px'>", unsafe_allow_html=True)
        st.download_button("Download PDF Report", data=pdf_output, file_name="cultural_pulse_report.pdf")
        st.markdown("</div>", unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error generating PDF: {e}")

elif page == "Whispering Walls":
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
        def get_main_wikipedia_image_url(query):
            try:
                # Step 1: Search for the page to get the exact title
                search_results = wikipedia.search(query, results=1)
                if not search_results:
                    return None
                
                page_title = search_results[0]
                
                # Step 2: Use MediaWiki API to get page images (more robust than wikipedia.page.images)
                # This API call often returns a 'thumbnail' or 'original' URL if available.
                api_url = "https://en.wikipedia.org/w/api.php"
                params = {
                    "action": "query",
                    "format": "json",
                    "titles": page_title,
                    "prop": "pageimages",
                    "pithumbsize": 500, # Request a thumbnail of this size
                    "redirects": 1 # Follow redirects
                }
                
                response = requests.get(api_url, params=params)
                response.raise_for_status() # Raise an exception for HTTP errors
                data = response.json()
                
                pages = data.get("query", {}).get("pages", {})
                for page_id in pages:
                    page_info = pages[page_id]
                    if "thumbnail" in page_info:
                        return page_info["thumbnail"]["source"]
                    elif "original" in page_info.get("pageimageinfo", {}): # Sometimes image info is nested differently
                        return page_info["pageimageinfo"]["original"]["url"]
                return None

            except wikipedia.exceptions.DisambiguationError as e:
                st.warning(f"Multiple results found for '{query}'. Trying the first option: {e.options[0]}.")
                # Try to get image for the first option
                return get_main_wikipedia_image_url(e.options[0])
            except wikipedia.exceptions.PageError:
                st.warning(f"No Wikipedia page found for '{query}'.")
                return None
            except requests.exceptions.RequestException as e:
                st.error(f"Network error while fetching image: {e}")
                return None
            except Exception as e:
                st.error(f"An unexpected error occurred while fetching image: {e}")
                return None

        image_url = get_main_wikipedia_image_url(selected_site)
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
                                voice_id="raj",
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

elif page == "Arts & Culture Hub":
    # India Arts & Culture Map
    st.header("🖼️ India Arts & Culture Map")
    state_names = [
        "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
        "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
        "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
        "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana",
        "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal"
    ]
    
    st.markdown("### Select a state to explore its Arts & Culture")
    selected_state = st.selectbox("Select a state", [""] + state_names)
    if selected_state:
        st.subheader(f"Famous Arts & Culture in {selected_state}")

        # Add language dropdown
        language = st.selectbox("Select Language", ["English", "Hindi", "Tamil", "Telugu", "Bengali"])

        # Define a function to call Gemini API
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
                st.error(f"Error fetching data from Gemini API: {e}")
            return None

        # Define a helper to fetch Wikipedia image
        def get_wikipedia_image_url(query):
            try:
                search_results = wikipedia.search(query, results=1)
                if not search_results:
                    return None
                page_title = search_results[0]
                api_url = "https://en.wikipedia.org/w/api.php"
                params = {
                    "action": "query",
                    "format": "json",
                    "titles": page_title,
                    "prop": "pageimages",
                    "pithumbsize": 500,
                    "redirects": 1
                }
                resp = requests.get(api_url, params=params)
                resp.raise_for_status()
                data = resp.json()
                pages = data.get("query", {}).get("pages", {})
                for page_id in pages:
                    page_info = pages[page_id]
                    if "thumbnail" in page_info:
                        return page_info["thumbnail"]["source"]
                return None
            except Exception as e:
                st.error(f"Error fetching image from Wikipedia: {e}")
                return None

        # Create the prompt for Gemini API to get arts and culture details with language preference
        arts_prompt = f"""
        You are an expert on Indian arts and culture. Provide a structured JSON response 
        with the famous arts, cultural events, and heritage highlights for the state "{selected_state}" in {language}.
        The JSON must have:
        - "description": a brief overview of the state's arts and culture.
        - "highlights": a list of 3 to 5 strings naming famous landmarks, cultural festivals or art forms.
        Do not include any extra commentary.
        """
        with st.spinner(f"Fetching arts & culture info for {selected_state}..."):
            culture_data = get_gemini_data(arts_prompt)

        if culture_data:
            st.write(culture_data.get("description", "No description available."))

            highlights = culture_data.get("highlights", [])
            if highlights:
                st.markdown("### Highlights")
                for item in highlights:
                    image_url = get_wikipedia_image_url(item)
                    if image_url:
                        st.image(image_url, caption=item, use_container_width=True)
                    else:
                        st.write(f"- {item}")
            else:
                st.warning("No highlights information found.")
        else:
            st.error("Failed to retrieve arts & culture details.")

elif page == "India's Cultural Grid":
    # Gemini API integration for cultural comparison
    st.title("🇮🇳 India's Cultural Grid – State-by-State Comparison")
    st.markdown("Explore cultural statistics and trends across Indian states!")
    st.markdown("This section provides a structured comparison of cultural data across various states in India, focusing on endangered art forms, festivals, tourist footfall, cultural revenue, accessibility scores, and government schemes.")
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
            if (result.get("candidates") and 
                result["candidates"][0].get("content") and 
                result["candidates"][0]["content"].get("parts")):
                data_text = result["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(data_text)
            else:
                st.error("Invalid response from Gemini API")
        except Exception as e:
            st.error(f"Error fetching data from Gemini API: {e}")
        return None

    with st.spinner("Fetching cultural comparison data..."):
        prompt = """
        You are an expert on cultural statistics and trends in India. Provide a structured JSON response containing a list of cultural comparison data for various states/regions.
        Each entry must include:
        - "state_region": name of the state or region.
        - "endangered_art_form": an endangered art form prevalent in that region.
        - "festival_upcoming": name of an upcoming festival.
        - "tourist_footfall": an estimated number of tourists.
        - "cultural_revenue": cultural revenue in crore rupees (₹ Cr).
        - "accessibility_score": a score from 1 to 10 representing cultural accessibility.
        - "govt_scheme_active": "Yes" or "No" indicating if a relevant government scheme is active.
        The JSON should have a single key "states_data" which is an array of these objects.
        Do not include any additional commentary.
        """
        data = get_gemini_data(prompt)

    if data and "states_data" in data:
        df = pd.DataFrame(data["states_data"])
        df = df.rename(columns={
            "state_region": "State/Region",
            "endangered_art_form": "Endangered Art Form",
            "festival_upcoming": "Festival (Upcoming)",
            "tourist_footfall": "Tourist Footfall",
            "cultural_revenue": "Cultural Revenue (₹ Cr)",
            "accessibility_score": "Accessibility Score",
            "govt_scheme_active": "Govt. Scheme Active"
        })
        st.table(df)
    else:
        st.error("Failed to retrieve cultural comparison data.")