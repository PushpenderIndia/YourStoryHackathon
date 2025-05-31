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
import pymongo
import uuid
import urllib.parse
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")
RAPIDAPI_KEY_1 = os.environ.get("RAPIDAPI_KEY_1", "")
RAPIDAPI_KEY_2 = os.environ.get("RAPIDAPI_KEY_2", "")
RAPIDAPI_KEYS = [RAPIDAPI_KEY, RAPIDAPI_KEY_1, RAPIDAPI_KEY_2] 
RAPIDAPI_HOST = "booking-com15.p.rapidapi.com"
SMALLEST_API_KEY = os.environ.get("SMALLEST_API_KEY", "")
MONGO_CONNECTION_STRING = os.environ.get("MONGODB_URI", "")
CURRENT_HOST = os.environ.get("BASE_URL", "http://localhost:8501").rstrip('/')

st.set_page_config(page_title="Rangyatra: Discover India's Hidden Colors of Culture.", layout="wide")
params = st.query_params

@st.cache_resource
def init_connection():
    """Initializes a connection to MongoDB and returns the database object."""
    try:
        client = pymongo.MongoClient(MONGO_CONNECTION_STRING)
        client.admin.command('ping') # Verify connection
        db = client.rangyatra # Select the database
        # st.success("Successfully connected to MongoDB!")
        return db
    except Exception as e:
        st.error(f"Failed to connect to MongoDB: {e}")
        return None

db = init_connection() # Initialize connection when the app starts

def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# local_css("style.css")

# --- Authentication State ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# --- Database Collections (ensure db is initialized) ---
users_collection = None
responses_collection_survey = None # Renamed to avoid conflict if you have other 'responses'
surveys_collection = None

if db:
    users_collection = db["users"]
    responses_collection_survey = db["social_survey_responses"] # Specific name for survey responses
    surveys_collection = db["surveys"]
else:
    st.error("Database connection failed. User authentication and survey features will not work.")
    # Optionally, stop the app or disable features if db is critical
    # st.stop()


# --- SIGNUP LOGIC ---
def signup_user(username, password):
    if not users_collection:
        st.error("Database not available for signup.")
        return
    if users_collection.find_one({"username": username}):
        st.error("Username already exists. Please choose a different one.")
    else:
        hashed_password = generate_password_hash(password)
        users_collection.insert_one({"username": username, "password": hashed_password})
        st.session_state.logged_in = True
        st.session_state.username = username
        st.success("Signup successful! You are now logged in.")
        st.experimental_rerun() # Rerun to reflect login state

# --- LOGIN LOGIC ---
def login_user(username, password):
    if not users_collection:
        st.error("Database not available for login.")
        return
    user = users_collection.find_one({"username": username})
    if user and check_password_hash(user["password"], password):
        st.session_state.logged_in = True
        st.session_state.username = username
        st.success("Logged in successfully!")
        st.experimental_rerun() # Rerun to reflect login state
    else:
        st.error("Invalid username or password")

# --- LOGOUT LOGIC ---
def logout_user():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.success("You have been logged out.")
    st.experimental_rerun()

# Page selection in sidebar
st.sidebar.title("Navigation")
page_options = ["Travel Planner", "Cultural Pulse Dashboard", "Whispering Walls", "Arts & Culture Hub", "Social Survey"]
if st.session_state.logged_in:
    st.sidebar.success(f"Logged in as {st.session_state.username}")
    if st.sidebar.button("Logout"):
        logout_user()
else:
    st.sidebar.info("Please login or signup to access all features.")

page = st.sidebar.radio("Go to", page_options)
selected_page = params.get("page") or page


# --- Centralized Login/Signup UI (shown if not logged in and trying to access certain pages) ---
def display_login_signup_forms():
    st.warning("You need to log in or sign up to access this feature.")
    login_tab, signup_tab = st.tabs(["Login", "Signup"])
    with login_tab:
        st.subheader("Login")
        login_username = st.text_input("Username", key="login_username_main")
        login_password = st.text_input("Password", type="password", key="login_password_main")
        if st.button("Login", key="login_button_main"):
            login_user(login_username, login_password)
    with signup_tab:
        st.subheader("Create Account")
        signup_username = st.text_input("Username", key="signup_username_main")
        signup_password = st.text_input("Password", type="password", key="signup_password_main")
        if st.button("Signup", key="signup_button_main"):
            signup_user(signup_username, signup_password)

if selected_page == "Travel Planner":
    st.markdown("<h1 style='font-size:38px; text-align: center;'>Rangyatra: Discover India’s Hidden Colors of Culture.</h1>", unsafe_allow_html=True)
    st.markdown("<div style='text-align: center;'>Plan your next adventure with AI-powered recommendations!<br>Made with ❤️ by Team Malaai (Machine Learning And AI)</div>", unsafe_allow_html=True)
    st.markdown("<div style='display: flex; justify-content: center; padding-top: 20px; padding-bottom: 20px;'>"
                "<img src='https://i.ibb.co/gFZvVT9r/india-map.png' width='350'></div>", unsafe_allow_html=True)
    
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
                    if (result.get("candidates") and result["candidates"][0].get("content") and 
                        result["candidates"][0]["content"].get("parts")):
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
                                
                                if RAPIDAPI_KEYS:  # List of API keys
                                    success = False
                                    for api_key in RAPIDAPI_KEYS:
                                        try:
                                            # Search hotels
                                            url = f"https://{RAPIDAPI_HOST}/api/v1/hotels/searchDestination"
                                            params = {"query": place.split("(")[0].strip()}
                                            headers = {
                                                "x-rapidapi-key": api_key,
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
                                            success = True
                                            break  # Exit loop on success
                                        except Exception as e:
                                            pass 
                                    
                                    if not success:
                                        st.error("All RapidAPI keys failed. Unable to fetch hotel recommendations.")
                                else:
                                    st.warning("RapidAPI key(s) missing - cannot show hotel recommendations")

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

elif selected_page == "Cultural Pulse Dashboard":
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

    # Section 1 – Tourist Footfall using Gemini APIAdd commentMore actions
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

    st.subheader("🇮🇳 India's Cultural Grid – State-by-State Comparison")
    st.markdown("Explore cultural statistics and trends across Indian states!")
    st.markdown("This section provides a structured comparison of cultural data across various states in India, focusing on endangered art forms, festivals, tourist footfall, cultural revenue, accessibility scores, and government schemes.")
    # get_gemini_data is already defined in this scope, so no need to redefine
    with st.spinner("Fetching cultural comparison data..."):
        prompt_grid = """
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
        Do not include any additional commentary.Add commentMore actions
        """
        grid_data = get_gemini_data(prompt_grid)

    if grid_data and "states_data" in grid_data:
        df_grid = pd.DataFrame(grid_data["states_data"])
        df_grid = df_grid.rename(columns={
            "state_region": "State/Region",
            "endangered_art_form": "Endangered Art Form",
            "festival_upcoming": "Festival (Upcoming)",
            "tourist_footfall": "Tourist Footfall",
            "cultural_revenue": "Cultural Revenue (₹ Cr)",
            "accessibility_score": "Accessibility Score",
            "govt_scheme_active": "Govt. Scheme Active"
        })
        st.table(df_grid)
    else:
        st.error("Failed to retrieve cultural comparison data for the grid.")

elif selected_page == "Whispering Walls":
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

    selected_site = st.selectbox("Choose or type a cultural site:", cultural_sites_list + [""])
    if selected_site == "":
        typed_site = st.text_input("Or type the name of a cultural site:", "")
        if typed_site:
            selected_site = typed_site
        else:
            selected_site = None
    elif selected_site is None:
        pass

    if selected_site:
        st.subheader(f"Exploring {selected_site}")

        def get_main_wikipedia_image_url(query):
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
                
                response = requests.get(api_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                pages = data.get("query", {}).get("pages", {})
                for page_id in pages:
                    page_info = pages[page_id]
                    if "thumbnail" in page_info:
                        return page_info["thumbnail"]["source"]
                    elif "original" in page_info.get("pageimageinfo", {}):
                        return page_info["pageimageinfo"]["original"]["url"]
                return None

            except wikipedia.exceptions.DisambiguationError as e:
                st.warning(f"Multiple results found for '{query}'. Trying the first option: {e.options[0]}.")
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
                            "generationConfig": {"maxOutputTokens": 500}
                        }
                        response = requests.post(f"{GEMINI_API_URL}?key={GEMINI_API_KEY}", headers=headers, json=payload)
                        response.raise_for_status()
                        result = response.json()
                        if (result.get("candidates") and result["candidates"][0].get("content") 
                            and result["candidates"][0]["content"].get("parts")):
                            story_text = result["candidates"][0]["content"]["parts"][0]["text"]

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
                            st.write(story_text)
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
    </div>
    """, unsafe_allow_html=True)

elif selected_page == "Arts & Culture Hub":
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

        language = st.selectbox("Select Language", ["English", "Hindi", "Tamil", "Telugu", "Bengali"])

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
                if (result.get("candidates") and result["candidates"][0].get("content") and 
                    result["candidates"][0]["content"].get("parts")):
                    data_text = result["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(data_text)
                else:
                    st.error("Invalid response from Gemini API")
            except Exception as e:
                st.error(f"Error fetching data from Gemini API: {e}")
            return None

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

elif selected_page == "Social Survey":
    st.title("Social Survey")

    if not db: # db was already checked, but good practice if this section is standalone
        st.error("Database connection not available. Social Survey cannot function.")
        st.stop()

    # Collections are already defined globally: surveys_collection, responses_collection_survey

    if not st.session_state.logged_in:
        display_login_signup_forms()
    else:
        st.success(f"Welcome to the Social Survey, {st.session_state.username}!")
        # Add Logout button specific to this page if required by task
        if st.button("Logout from Survey Page", key="logout_survey_button"):
            logout_user()

        BANNED_WORDS = ["badword1", "profanity2", "exampleabuse3", "hate", "violence"]

    survey_id_from_url = None
    if "survey_id" in params:
        survey_id_from_url = params.get("survey_id")[0] if isinstance(params.get("survey_id"), list) else params.get("survey_id")

    question_from_url = None
    if "question" in params:
        raw_question = params.get("question")[0] if isinstance(params.get("question"), list) else params.get("question")
        if raw_question:
            question_from_url = urllib.parse.unquote(raw_question)

    if survey_id_from_url and question_from_url:
        st.subheader("Respond to Survey")
        st.markdown(f"**Question:** {question_from_url}")

        if not st.session_state.logged_in:
            st.warning("Please log in or sign up to respond to this survey.")
            # display_login_signup_forms() is already called if not logged_in at the start of "Social Survey" page.
            # So, just the message is sufficient here, or we can call it again if more direct context is needed.
            # For now, assuming the top-level call to display_login_signup_forms is adequate.
        else:
            user_response = st.text_area("Your Response:", помощи=f"Responding as {st.session_state.username}", key=f"response_area_{survey_id_from_url}")

            if st.button("Submit Response", type="primary", key=f"submit_response_{survey_id_from_url}"):
                if not user_response.strip():
                    st.warning("Please enter a response.")
                else:
                    response_text = user_response.strip()
                response_lower = response_text.lower()
                contains_banned_word = False
                for word in BANNED_WORDS:
                    if word.lower() in response_lower:
                        contains_banned_word = True
                        break

                if contains_banned_word:
                    st.error("Your response contains inappropriate language and cannot be submitted. Please revise your response.")
                else:
                    response_doc = {
                        "survey_id": survey_id_from_url,
                        "response_text": response_text,
                    "responded_at": datetime.utcnow(),
                    "responder_username": st.session_state.username # Associate user with response
                    }
                    try:
                        # Ensure responses_collection_survey is used
                        if responses_collection_survey is not None:
                            responses_collection_survey.insert_one(response_doc)
                            st.success("Your response has been submitted successfully!")
                        else:
                            st.error("Response collection not available.")
                    except Exception as e:
                        st.error(f"Failed to submit response: {e}")
    # Create new survey part - only if logged in
    # This section is already within the `else` block of `if not st.session_state.logged_in:`.
    # Now, we refine it to ensure the form for creating surveys is also explicitly under this condition.

        # Survey Creation Form
        st.subheader("Create a New Social Survey")
        # The following form elements were already here and correctly placed under the login check.
        # No need to move them, just confirming their placement.
        location_xyz = st.text_input("Enter a location (e.g., 'your city', 'a nearby park') for {XYZ} placeholder:")
        date_abc = st.text_input("Enter a date or event (e.g., 'next weekend', 'tomorrow evening') for {ABC} placeholder (optional):")

        templates = [
            "Asking for suggestions for unexplored and local places around {XYZ}.",
            "I am planning to visit {XYZ} on {ABC}. If anyone is nearby, let's catch up!",
            "What's your favorite hidden gem in {XYZ}?",
            "Share your recommendations for must-try street food in {XYZ}."
        ]
        selected_template = st.selectbox("Choose a message template:", templates)

        generate_button_disabled = False
        if "{XYZ}" in selected_template and not location_xyz:
            st.warning("Please enter a location for {XYZ} to use this template.")
            generate_button_disabled = True

        if st.button("Generate Survey Link", type="primary", disabled=generate_button_disabled):
            if not location_xyz and "{XYZ}" in selected_template:
                st.error("Location {XYZ} is required for this template. Please fill it.")
            else:
                final_question = selected_template
                if location_xyz:
                    final_question = final_question.replace("{XYZ}", location_xyz)

                if "{ABC}" in final_question:
                    if date_abc:
                        final_question = final_question.replace("{ABC}", date_abc)
                    else:
                        final_question = final_question.replace("on {ABC}", "").replace("{ABC}", "soon")

                survey_id = str(uuid.uuid4())

                try:
                    survey_doc = {
                        "survey_id": survey_id,
                        "question": final_question,
                        "created_at": datetime.utcnow(),
                        "creator_username": st.session_state.username # Associate user with survey
                    }
                    surveys_collection.insert_one(survey_doc)

                    encoded_question = urllib.parse.quote(final_question)

                    st.success("Survey Link Generated!")
                    st.markdown(f"**Survey Question:** {final_question}")
                    st.markdown(f"**Shareable URL:**")
                    st.code(f"{CURRENT_HOST}/?page=Social+Survey&survey_id={survey_id}&question={encoded_question}", language=None)
                    st.caption("Append these parameters to your current app's URL (e.g., your-streamlit-app-url/?page=Social+Survey&survey_id=...&question=...).")
                    st.info("Note: To properly test the survey link, you'll need to open it in a new browser tab or window, appending the parameters to the base URL of your Streamlit application followed by `&page=Social+Survey` if not already part of your base URL structure for pages.")

                except Exception as e:
                    st.error(f"Error saving survey to database: {e}")

        st.markdown("---")
        st.subheader("Past Survey Responses")

        if not st.session_state.logged_in:
            st.info("Log in to see your surveys and responses.")
        else:
            try:
                # Filter surveys by the logged-in user
                username = st.session_state.username
                all_surveys_cursor = surveys_collection.find({"creator_username": username}).sort("created_at", -1)
                all_surveys = list(all_surveys_cursor)
            except Exception as e:
                st.error(f"Error fetching your surveys: {e}")
                all_surveys = []

            if not all_surveys:
                st.info("You have not created any surveys yet.")
            else:
                items_per_page = 5
            total_surveys = len(all_surveys)
            total_pages = (total_surveys + items_per_page - 1) // items_per_page
            if total_pages == 0: total_pages = 1

            current_page = st.number_input("Page", min_value=1, max_value=total_pages, value=1, key="pagination_survey_list", help=f"Showing {items_per_page} surveys per page.")

            start_idx = (current_page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            surveys_to_display = all_surveys[start_idx:end_idx]

            if not surveys_to_display:
                st.info("No surveys on this page.")
            else:
                for survey in surveys_to_display:
                    st.markdown("---")
                    survey_question = survey.get('question', 'N/A')
                    survey_id_display = survey.get('survey_id', 'N/A')
                    created_at_display = survey.get('created_at')
                    creator_username_display = survey.get('creator_username') # Get creator username

                    st.markdown(f"#### Survey Question: {survey_question}")
                    caption_text = f"Survey ID: {survey_id_display}"
                    if created_at_display:
                        caption_text += f" | Created: {created_at_display.strftime('%Y-%m-%d %H:%M:%S UTC')}"
                    if creator_username_display:
                        caption_text += f" | By: {creator_username_display}"
                    else:
                        caption_text += " | By: Anonymous (older survey)" # Handle older surveys
                    st.caption(caption_text)

                    try:
                        # Ensure responses_collection_survey is used
                        if responses_collection_survey is not None:
                            survey_responses_cursor = responses_collection_survey.find({"survey_id": survey_id_display}).sort("responded_at", -1)
                            survey_responses = list(survey_responses_cursor)
                        else:
                            survey_responses = []
                            st.error("Response collection not available.")
                    except Exception as e:
                        st.error(f"Error fetching responses for survey ID {survey_id_display}: {e}")
                        survey_responses = []

                    if not survey_responses:
                        st.markdown("_No responses yet for this survey._")
                    else:
                        with st.expander(f"View {len(survey_responses)} Response(s) for survey: '{survey_question[:50]}...'"):
                            for i, response in enumerate(survey_responses):
                                response_text = response.get('response_text', 'N/A')
                                responded_at_display = response.get('responded_at')
                                responder_username_display = response.get('responder_username')

                                response_label = f"**Response {i+1}"
                                if responder_username_display:
                                    response_label += f" by {responder_username_display}"
                                response_label += ":**"
                                st.markdown(f"{response_label} {response_text}")

                                caption_response_text = ""
                                if responded_at_display:
                                    caption_response_text = f"Responded at: {responded_at_display.strftime('%Y-%m-%d %H:%M:%S UTC')}"
                                else:
                                    caption_response_text = "Responded at: N/A"
                                st.caption(caption_response_text)

                                if i < len(survey_responses) - 1:
                                    st.markdown("---")
