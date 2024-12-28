import streamlit as st
import pymysql
from Home_test import connect_db

def job_list():
    st.title("📋 Manage Job Listings")

    # Check login status and user type
    if not st.session_state.get("logged_in"):
        st.warning("Please log in first.")
        return

    if st.session_state.get("user_type", "").lower() != "parent":
        st.error("Access denied. This page is for parents only.")
        return

    # Fetch parent's email from session state
    parent_email = st.session_state.get("email")
    conn = connect_db()

    # Fetch job listings for the parent
    jobs = []
    if conn:
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM job_listings WHERE parent_email = %s", (parent_email,))
            jobs = cursor.fetchall()
        except Exception as e:
            st.error(f"Error fetching job listings: {e}")
        finally:
            conn.close()

    # Display job listings
    if not jobs:
        st.info("No job listings found. Use the Upload Job Listing page to add jobs.")
        return

    st.subheader("Your Job Listings")

    for job in jobs:
        st.markdown(f"### {job['job_title']}")
        st.markdown(f"**Description:** {job['job_description']}")

        if 'is_active' in job:
            status_color = "green" if job['is_active'] else "red"
            st.markdown(f"**Status:** <span style='color:{status_color}; font-weight:bold;'>{'Active' if job['is_active'] else 'Inactive'}</span>", unsafe_allow_html=True)
        else:
            st.warning("Status information is not available.")  # Fallback if is_active doesn't exist

        col1, col2 = st.columns(2)
        with col1:
            toggle_label = "Set Active" if not job.get('is_active', False) else "Set Inactive"
            toggle_status = st.button(
                label=f"{toggle_label}",
                key=f"toggle_{job['id']}",
                help=f"Click to {'activate' if not job.get('is_active', False) else 'deactivate'} this job."
            )
        with col2:
            delete_job = st.button(
                label="Delete Job",
                key=f"delete_{job['id']}",
                help="Click to permanently delete this job listing."
            )

        # Handle status toggle
        if toggle_status:
            new_status = not job.get('is_active', False)
            conn = connect_db()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE job_listings SET is_active = %s WHERE id = %s",
                        (new_status, job['id'])
                    )
                    conn.commit()
                    st.success(f"Job status updated to {'Active' if new_status else 'Inactive'}.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error updating job status: {e}")
                finally:
                    conn.close()

        # Handle job deletion
        if delete_job:
            conn = connect_db()
            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM job_listings WHERE id = %s", (job['id'],))
                    conn.commit()
                    st.success("Job deleted successfully.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error deleting job: {e}")
                finally:
                    conn.close()

# Ensure this is only run when the script is directly executed
if __name__ == "__main__":
    job_list()
