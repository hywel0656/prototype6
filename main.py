import streamlit as st
import openai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import statistics

# --- CONFIG ---
openai.api_key = st.secrets["openai_api_key"]
google_sheets_creds = st.secrets["gcp_service_account"]

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_sheets_creds, scope)
client = gspread.authorize(creds)
sheet = client.open("Translation Scores").sheet1

# --- APP STATE ---
if "student_scores" not in st.session_state:
    st.session_state.student_scores = {}

# --- FUNCTIONS ---
def check_translation(student_text, reference_text):
    """Send the translation to the AI for scoring."""
    prompt = f"""
    You are a grading assistant. Compare the student's translation to the reference translation.
    Reference: {reference_text}
    Student: {student_text}
    Give a score from 0 to 100, and explain briefly why.
    Format: 'Score: X\nFeedback: ...'
    """
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    output = response.choices[0].message["content"]

    # Extract score
    try:
        score_line = [line for line in output.split("\n") if "Score:" in line][0]
        score = int(score_line.split(":")[1].strip())
    except:
        score = 0
    return score, output

def save_final_score(name, number, scores):
    """Save only one final average score per student per session."""
    avg_score = round(statistics.mean(scores), 1)
    sheet.append_row([name, number, avg_score])

# --- UI ---
st.title("AI Translation Game")

student_name = st.text_input("Your Name")
student_number = st.text_input("Your Student Number")
reference_text = "The cat sat on the mat."
student_translation = st.text_area("Enter your translation here:")

col1, col2, col3 = st.columns(3)

# --- Try Translation ---
if col1.button("Try Translation"):
    if student_translation.strip():
        score, feedback = check_translation(student_translation, reference_text)
        st.info(f"Feedback (Try Only):\n\n{feedback}")
    else:
        st.warning("Please enter your translation first.")

# --- Submit Translation ---
if col2.button("Submit Translation"):
    if student_translation.strip() and student_name.strip() and student_number.strip():
        score, feedback = check_translation(student_translation, reference_text)
        # Store score in session state
        st.session_state.student_scores.setdefault(student_number, []).append(score)
        st.success(f"Feedback (Submitted):\n\n{feedback}")
    else:
        st.warning("Please fill in your name, number, and translation.")

# --- Finish Session ---
if col3.button("Finish Session"):
    if student_number in st.session_state.student_scores:
        scores = st.session_state.student_scores[student_number]
        save_final_score(student_name, student_number, scores)
        st.success(f"Final average score saved for {student_name} ({student_number}).")
        st.session_state.student_scores[student_number] = []  # Clear after saving
    else:
        st.warning("No submitted scores found for this session.")
