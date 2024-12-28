import streamlit as st
from supabase import create_client, Client
import os
import base64
import json
import datetime

# Add the path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import error handling and other modules
try:
    from Home_test import home
    from pages.login_test import login
    from pages.sign_test import signup
    from feedback import feedback
    from applied_jobs import main as applied_jobs
    from about_us import about_us
except ImportError as e:
    st.error(f"Import error: {e}")
    st.stop()
  
# Supabase Configuration
SUPABASE_URL = "https://your-supabase-url.supabase.co"
SUPABASE_KEY = "your-supabase-key"

# Session State Initialization
def initialize_session():
    defaults = {
        "step": 1,
        "form_data": {},
        "availability_rows": [{"day": "", "time": None}],
        "logged_in": False,
        "email": None,
        "user_id": None,
        "page": "login",
        "selected_job_title": "Unknown Job",
        "selected_job_subject": "Unknown Subject",
        "selected_job_location": "Unknown Location",
        "selected_job_skills": "Not specified",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
          
# Initialize Supabase client
def get_db_connection() -> Client:
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"Error initializing Supabase client: {e}")
        return None
      
# Helper Functions
def save_uploaded_resume(uploaded_file):
    if uploaded_file is not None:
        os.makedirs('uploads', exist_ok=True)
        filename = f"resume_{os.urandom(8).hex()}.pdf"
        file_path = os.path.join('uploads', filename)
        with open(file_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    return None

def display_pdf(file_path):
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)
  
# Helper Functions
def submit_application(user_id):
    availability_json = json.dumps(st.session_state.form_data['availability'])
    supabase = get_db_connection()
    
    if supabase:
        try:
            # Retrieve job details
            job_title = st.session_state.get('selected_job_title', 'Unknown')
            job_query = supabase.table("job_listings").select("*").eq("job_title", job_title).execute()
            
            if job_query.data:
                job = job_query.data[0]
                job_id = job["id"]
                job_city = job["city"]
                job_state = job["state"]
                
                st.session_state['selected_job_location'] = f"{job_city}, {job_state}"
                
                # Check if user already applied
                existing_application = supabase.table("job_applications").select("id").eq("user_id", user_id).eq("job_id", job_id).execute()
                if existing_application.data:
                    st.error("You have already applied for this job.")
                    return
                
                # Insert job application
                new_application = {
                    "user_id": user_id,
                    "job_id": job_id,
                    "resume_path": st.session_state.form_data['resume_path'],
                    "teaching_style": st.session_state.form_data['teaching_style'],
                    "availability": availability_json,
                    "is_confirmed": False,
                    "created_at": datetime.datetime.utcnow().isoformat(),
                    "status": "Pending"
                }
                supabase.table("job_applications").insert(new_application).execute()
                st.success("Application submitted successfully!")
            
            else:
                st.error("Could not find the selected job in the database.")
                return

        except Exception as e:
            st.error(f"Error submitting application: {e}")
# Navigation Functions
def change_step(step_number):
    st.session_state.step = step_number

def change_page(page_name):
    st.session_state.page = page_name

def add_availability_slot():
    st.session_state.availability_rows.append({"day": "", "time": None})

def remove_availability_slot(idx):
    st.session_state.availability_rows.pop(idx)

def sidebar_navigation():
    st.markdown(
        """
        <style>
        [data-testid="stSidebarNav"] {display: none;}
        </style>
        """,
        unsafe_allow_html=True,
    )

# Apply Page Functionality
def apply():
    if not st.session_state.get("logged_in"):
        st.error("Please log in to apply for a job.")
        return

    user_id = st.session_state.get("user_id")
    if not user_id:
        st.error("No user ID found. Please log in again.")
        return
        
    st.title("Job Application Form")

    # STEP 1: Upload Resume
    if st.session_state.step == 1:
        st.header("Step 1: Upload Resume")
        uploaded_resume = st.file_uploader("Upload your Resume (PDF)", type=['pdf'], key="resume_uploader")
        
        if uploaded_resume:
            resume_path = save_uploaded_resume(uploaded_resume)
            st.session_state.form_data['resume_path'] = resume_path
            
            st.subheader("Resume Preview")
            display_pdf(resume_path)
            
            st.button("Proceed to Next Step", key="next_step_1", on_click=change_step, args=(2,))

    # STEP 2: Add Details
    elif st.session_state.step == 2:
        st.header("Step 2: Additional Details")

        teaching_style = st.text_area("Briefly explain your teaching style", key="teaching_style_input")

        st.subheader("Availability")
        for idx, row in enumerate(st.session_state.availability_rows):
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                default_day = row["day"] if row["day"] else "Monday"
                row["day"] = st.selectbox(f"Day {idx + 1}", 
                    ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                    index=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].index(default_day),
                    key=f"day_{idx}")
            with col2:
                default_time = row["time"] if row["time"] is not None else datetime.time(9, 0)
                row["time"] = st.time_input(f"Time {idx + 1}", value=default_time, key=f"time_{idx}")
            with col3:
                st.button("Delete", key=f"delete_{idx}", on_click=remove_availability_slot, args=(idx,))

        st.button("Add Another Availability Slot", on_click=add_availability_slot)

        st.session_state.form_data['teaching_style'] = teaching_style
        st.session_state.form_data['availability'] = [
            {"day": row["day"], "time": row["time"].strftime('%H:%M') if row["time"] else None} 
            for row in st.session_state.availability_rows
        ]

        col1, col2 = st.columns(2)
        with col1:
            st.button("Back to Resume Upload", key="back_to_resume", on_click=change_step, args=(1,))
        
        with col2:
            if teaching_style and st.session_state.form_data['availability']:
                st.button("Proceed to Review", key="proceed_to_review", on_click=change_step, args=(3,))
            else:
                st.warning("Please fill in all fields")

    # STEP 3: Review and Submit
    elif st.session_state.step == 3:
        st.header("Step 3: Review Application")
        
        st.subheader("Uploaded Resume")
        display_pdf(st.session_state.form_data['resume_path'])
        
        st.subheader("Application Details")
        st.write(f"**Teaching Style:** {st.session_state.form_data['teaching_style']}")

        availability_list = st.session_state.form_data['availability']
        formatted_availability = [f"{entry['day']} at {entry['time']}" for entry in availability_list]
        st.write("**Availability:**")
        st.write(", ".join(formatted_availability))
        
        confirmation = st.checkbox("I confirm that the information provided is accurate and complete to the best of my knowledge.", key="confirmation_checkbox")
        
        st.warning("*Double-check your details before submission. Changes cannot be made after submission.*")
        
        col1, col2 = st.columns(2)
        with col1:
            st.button("Back to Details", key="back_to_details", on_click=change_step, args=(2,))
        
        with col2:
            if confirmation:
                if st.button("Submit Application", key="submit_application"):
                    submit_application(user_id)
                    change_page("applied_jobs")

def login():
    st.title("Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Log In"):
        user_id = handle_login(email, password)
        if user_id:
            st.session_state["logged_in"] = True
            st.session_state["email"] = email
            st.session_state["user_id"] = user_id
            st.session_state["page"] = "home"

# Authentication Example
def handle_login(email, password):
    supabase = get_db_connection()
    if not supabase:
        return None
    
    try:
        user_query = supabase.table("users").select("id").eq("email", email).eq("password", password).execute()
        if user_query.data:
            return user_query.data[0]["id"]
        else:
            st.error("Invalid credentials.")
            return None
    except Exception as e:
        st.error(f"Error during login: {e}")
        return None
def main():
    initialize_session()
    sidebar_navigation()

    page = st.session_state["page"]
    if page == "home":
        home()
    elif page == "login":
        login()
    elif page == "signup":
        signup()
    elif page == "feedback":
        feedback()
    elif page == "applied_jobs":
        applied_jobs()
    elif page == "about_us":
        about_us()
    elif page == "apply":
        apply()
    else:
        st.error("Page not found. Please check your navigation.")

if __name__ == "__main__":
    main()
