import streamlit as st
from supabase import create_client
from datetime import datetime
import os

def create_supabase_client():
    # Replace with your actual Supabase URL and API Key
    SUPABASE_URL = "https://your-supabase-url.supabase.co"
    SUPABASE_KEY = "your-supabase-key"
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_applications(user_email):
    """Fetch all applications for jobs posted by the parent"""
    supabase = create_supabase_client()
    try:
        response = supabase.from_("job_applications")
            .select("id as application_id, job_listings(job_title, job_subject), users(full_name), resume_path, status")
            .eq("job_listings.parent_email", user_email)
            .execute()
        return response.get("data", [])
    except Exception as e:
        st.error(f"Error fetching applications: {e}")
        return []

def update_application_status(application_id, status):
    """Update the status of an application"""
    supabase = create_supabase_client()
    try:
        response = supabase.from_("job_applications")
            .update({"status": status, "updated_at": datetime.now().isoformat()})
            .eq("id", application_id)
            .execute()
        return response.get("status_code") == 204
    except Exception as e:
        st.error(f"Error updating application status: {e}")
        return False

def download_resume(resume_path):
    """Handle resume download"""
    try:
        with open(resume_path, 'rb') as file:
            return file.read()
    except Exception as e:
        st.error(f"Error downloading resume: {e}")
        return None

def application_overview():
    st.title("Application Overview")

    if not st.session_state.get("logged_in"):
        st.warning("Please log in to view applications.")
        return

    # Get the email from the session state
    user_email = st.session_state.get("email")
    if not user_email:
        st.error("Unable to retrieve your email. Please log in again.")
        return

    # Fetch applications for jobs posted by this user
    applications = fetch_applications(user_email)

    if applications:
        # Prepare data for display
        for app in applications:
            app_id = app["application_id"]
            job_title = app["job_listings"]["job_title"]
            job_subject = app["job_listings"]["job_subject"]
            full_name = app["users"]["full_name"]
            resume_path = app.get("resume_path")
            status = app.get("status", "Pending")

            # Create a container for each application
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 3])

                with col1:
                    st.write(f"**Name:** {full_name}")
                with col2:
                    st.write(f"**Job Title:** {job_title}")
                with col3:
                    st.write(f"**Subject:** {job_subject}")
                with col4:
                    if resume_path and os.path.exists(resume_path):
                        resume_content = download_resume(resume_path)
                        if resume_content:
                            st.download_button(
                                label="Download Resume",
                                data=resume_content,
                                file_name=f"resume_{full_name}.pdf",
                                mime="application/pdf",
                                key=f"download_{app_id}"  # Unique key for each download button
                            )
                with col5:
                    st.write(f"**Status:** {status}")
                    if status == 'Pending':
                        col5_1, col5_2 = st.columns(2)
                        with col5_1:
                            if st.button(f"Accept", key=f"accept_{app_id}"):
                                if update_application_status(app_id, "Accepted"):
                                    st.success("Application accepted!")
                                    st.experimental_rerun()
                        with col5_2:
                            if st.button(f"Reject", key=f"reject_{app_id}"):
                                if update_application_status(app_id, "Rejected"):
                                    st.success("Application rejected!")
                                    st.experimental_rerun()

                st.divider()
    else:
        st.info("No applications found for your jobs.")

def main():
    application_overview()

if __name__ == "__main__":
    main()
