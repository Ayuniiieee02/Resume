import streamlit as st
import pandas as pd
import base64
import random
import time
import datetime
import re
import os
from supabase import create_client, SupabaseClient
from pyresparser import ResumeParser
from streamlit_tags import st_tags
from Courses import resume_videos, interview_videos
from keywords import it_keywords, software_keywords, multimedia_keywords, science_keywords, math_keywords
import nltk

nltk.download('stopwords')

# Initialize Supabase client
url = "YOUR_SUPABASE_URL"
key = "YOUR_SUPABASE_API_KEY"
supabase: SupabaseClient = create_client(url, key)

def check():
    """Check if the user is logged in and fetch user details."""
    if not st.session_state.get("logged_in"):
        st.warning("Please log in first.")
        return None
    
    if st.session_state.get("user_type", "").lower() != "user":
        st.error("Access denied. This page is for users only.")
        return None
    
    user_email = st.session_state.get("email")
    
    try:
        response = supabase.table('users').select('*').eq('email', user_email).execute()
        user = response.data
        if user:
            return user[0]  # Return the user object
        else:
            st.error("User details not found.")
    except Exception as e:
        st.error(f"Error fetching user details: {e}")

    return None

def display_user_dashboard(user):
    st.markdown(f"<h1 style='text-align: center; color: #021659;'>Welcome, {user['username']}!</h1>", unsafe_allow_html=True)
    st.write(f"Full Name: {user['full_name']}")
    st.write(f"Email: {user['email']}")

def extract_keywords_from_resume(resume_text):
    keywords = []
    patterns = [r"\b(Developer|Engineer|Manager|Tutor|Designer|Analyst)\b", 
                r"\b(Python|Java|SQL|Teaching|Communication|Leadership|Information Technology)\b"]
    for pattern in patterns:
        keywords.extend(re.findall(pattern, resume_text, re.IGNORECASE))
    return set(keywords)

def show_pdf(file_path):
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)

def recommend_jobs_from_database(keywords):
    recommended_jobs = []
    try:
        response = supabase.table('job_listings').select('*').execute()
        all_jobs = response.data

        # Normalize keywords for comparison (all lowercase)
        normalized_keywords = {keyword.strip().lower() for keyword in keywords}  # Use set for fast membership testing

        for job in all_jobs:
            # Normalize job_subject and required_skills (all lowercase)
            job_subject_normalized = {s.strip().lower() for s in job['job_subject'].split(',')}
            job_skills = {s.strip().lower() for s in job['required_skills'].split(',')}  # Use set

            # Check if any keyword matches job_subject or required_skills
            if (job_subject_normalized & normalized_keywords) or (job_skills & normalized_keywords):
                recommended_jobs.append(job)

    except Exception as e:
        st.error(f"Error querying database: {e}")

    return recommended_jobs

def get_table_download_link(df, filename, text):
    """Generates a link allowing the data in a given pandas dataframe to be downloaded."""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'
    return href

def pdf_reader(file):
    from pdfminer3.layout import LAParams
    from pdfminer3.pdfinterp import PDFResourceManager, PDFPageInterpreter
    from pdfminer3.converter import TextConverter
    from pdfminer3.pdfpage import PDFPage
    import io

    resource_manager = PDFResourceManager()
    fake_file_handle = io.StringIO()
    converter = TextConverter(resource_manager, fake_file_handle, laparams=LAParams())
    page_interpreter = PDFPageInterpreter(resource_manager, converter)
    with open(file, 'rb') as fh:
        for page in PDFPage.get_pages(fh, caching=True, check_extractable=True):
            page_interpreter.process_page(page)
        text = fake_file_handle.getvalue()

    # Close open handles
    converter.close()
    fake_file_handle.close()
    return text

def insert_data(name, email, res_score, timestamp, no_of_pages, reco_field, cand_level, skills, recommended_skills):
    """Insert user data into the database."""
    DB_table_name = 'user_data'
    rec_values = {
        "name": name,
        "email": email,
        "res_score": float(res_score),
        "timestamp": timestamp,
        "no_of_pages": int(no_of_pages),
        "reco_field": reco_field,
        "cand_level": cand_level,
        "skills": str(skills),
        "recommended_skills": str(recommended_skills)
    }
    
    try:
        supabase.table(DB_table_name).insert(rec_values).execute()
        print("Data inserted successfully!")
    except Exception as e:
        print(f"Error inserting data: {e}")

def run():
    user_id = check()  # Call check to verify login and get user_id
    if user_id is None:
        return

    display_user_dashboard(user_id)
    
    # Main header for the page with enhanced styling
    st.markdown('''
    <h2 style='text-align: center; color: #021659; border-bottom: 2px solid #021659; padding-bottom: 10px;'>Upload Your Resume for Smart Recommendations 💡</h2>
    ''', unsafe_allow_html=True)

    # File uploader for resume with styled button
    pdf_file = st.file_uploader("Choose your Resume (PDF)", type=["pdf"], label_visibility="collapsed")
    
    if pdf_file is not None:
        with st.spinner('Uploading your Resume...'):
            time.sleep(2)  # Reduced wait time for demonstration
        save_image_path = './Uploaded_Resumes/' + pdf_file.name
        with open(save_image_path, "wb") as f:
            f.write(pdf_file.getbuffer())
        
        # Show the uploaded PDF
        show_pdf(save_image_path)
        resume_data = ResumeParser(save_image_path).get_extracted_data()
        
        if resume_data:
            resume_text = pdf_reader(save_image_path)

            st.header("**Resume Analysis**")
            st.success(f"Hello **{resume_data['name']}**")
            st.subheader("**Your Basic Info**")
            st.write(f"**Name:** {resume_data['name']}")
            st.write(f"**Email:** {resume_data['email']}")
            st.write(f"**Contact:** {resume_data['mobile_number']}")
            st.write(f"**Resume pages:** {resume_data['no_of_pages']}")

            # Candidate Level Assessment
            cand_level = ''
            skill_count = len(resume_data.get('skills', []))
            if resume_data['no_of_pages'] == 1 and skill_count < 3:
                cand_level = "Fresher"
                st.markdown('<h4 style="color: #d73b5c; border: 1px solid #d73b5c; padding: 10px; border-radius: 5px;">You are at Fresher level!</h4>', unsafe_allow_html=True)
            elif resume_data['no_of_pages'] == 2 or (resume_data['no_of_pages'] == 1 and skill_count >= 3):
                cand_level = "Intermediate"
                st.markdown('<h4 style="color: #1ed760; border: 1px solid #1ed760; padding: 10px; border-radius: 5px;">You are at Intermediate level!</h4>', unsafe_allow_html=True)
            elif resume_data['no_of_pages'] >= 3:
                cand_level = "Experienced"
                st.markdown('<h4 style="color: #fba171; border: 1px solid #fba171; padding: 10px; border-radius: 5px;">You are at Experienced level!</h4>', unsafe_allow_html=True)

            # Skills input with tagging
            keywords = st_tags(label='### Your Current Skills', text='See our skills recommendations below', value=resume_data['skills'], key='1')
            
            # Normalizing skills
            keywords = [skill.lower().strip() for skill in resume_data['skills']]
            recommended_skills = []
            reco_field = ''
            
            for i in resume_data['skills']:
                if i.lower() in it_keywords:
                    reco_field = 'Information Technology'
                    st.success("**Our analysis suggests you are looking for Information Technology Jobs.**")
                    recommended_skills = ['Database Management', 'Digital Pedagogy', 'System Administration']
                    break
                elif i.lower() in software_keywords:
                    reco_field = 'Software Engineering'
                    st.success("**Our analysis suggests you are looking for Software Engineering Jobs.**")
                    recommended_skills = ['React', 'Usability Testing', 'Node JS']
                    break
                elif i.lower() in multimedia_keywords: 
                    reco_field = 'Multimedia'
                    st.success("**Our analysis suggests you are looking for Multimedia Jobs.**")
                    recommended_skills = ['Motion Graphics', 'Blender', 'User Interface Design']
                    break
                elif i.lower() in science_keywords:
                    reco_field = 'Science'
                    st.success("**Our analysis suggests you are looking for Science Jobs.**")
                    recommended_skills = ['Electrochemistry', 'Biodiversity', 'Science Experiments']
                    break
                elif i.lower() in math_keywords:
                    reco_field = 'Mathematics'
                    st.success("**Our analysis suggests you are looking for Mathematics Jobs.**")
                    recommended_skills = ['Visual Learning in Math', 'Hands-on Math Activities', 'Inquiry-based Learning in Math']
                    break

            # Job recommendations based on extracted keywords
            keywords = extract_keywords_from_resume(resume_text)
            job_recommendations = recommend_jobs_from_database(keywords)
            
            st.subheader("Job Recommendations 💼")
            if job_recommendations:
                for idx, job in enumerate(job_recommendations):
                    st.markdown(f"""
                    <div style="border: 1px solid #021659; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                        <strong>Job Title:</strong> {job['job_title']}<br>
                        <strong>Subject Area:</strong> {job['job_subject']}<br>
                        <strong>Description:</strong> {job['job_description']}<br>
                        <strong>Required Skills:</strong> {job['required_skills']}<br>
                        <strong>Hourly Rate:</strong> RM{job['hourly_rate']}/hour<br>
                    </div>
                    """, unsafe_allow_html=True)
                    # Use a unique key for each button by combining job title and index
                    if st.button(f"Apply for {job['job_title']}", key=f"apply_{job['job_title']}_{idx}"):
                        st.session_state['selected_job_title'] = job['job_title']
                        st.session_state['page'] = "apply"
                        st.rerun()
            else:
                st.warning("No matching jobs found based on your skills and qualifications.")

            # Time and date for the entry
            ts = time.time()
            cur_date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
            cur_time = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
            timestamp = str(cur_date + '_' + cur_time)

            # Resume writing recommendations
            st.subheader("**Resume Tips & Ideas💡**")
            resume_score = 0
            if 'Objective' in resume_text:
                resume_score = resume_score + 20
                st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Objective</h4>''', unsafe_allow_html=True)
            else:
                st.markdown('''<h5 style='text-align: left; color: #000000;'>[-] Please add your career objective, it will give your career intention to the Recruiters.</h4>''', unsafe_allow_html=True)

            if 'Declaration' in resume_text:
                resume_score = resume_score + 20
                st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Declaration</h4>''', unsafe_allow_html=True)
            else:
                st.markdown('''<h5 style='text-align: left; color: #000000;'>[-] Please add Declaration. It will give the assurance that everything written on your resume is true and fully acknowledged by you</h4>''', unsafe_allow_html=True)

            if 'Hobbies' in resume_text or 'Interests' in resume_text:
                resume_score = resume_score + 20
                st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Hobbies</h4>''', unsafe_allow_html=True)
            else:
                st.markdown('''<h5 style='text-align: left; color: #000000;'>[-] Please add Hobbies. It will show your personality to the Recruiters and give the assurance that you are fit for this role or not.</h4>''', unsafe_allow_html=True)

            if 'Achievements' in resume_text:
                resume_score = resume_score + 20
                st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Achievements</h4>''', unsafe_allow_html=True)
            else:
                st.markdown('''<h5 style='text-align: left; color: #000000;'>[-] Please add Achievements. It will show that you are capable for the required position.</h4>''', unsafe_allow_html=True)

            if 'Projects' in resume_text:
                resume_score = resume_score + 20
                st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Projects</h4>''', unsafe_allow_html=True)
            else:
                st.markdown('''<h5 style='text-align: left; color: #000000;'>[-] Please add Projects. It will show that you have done work related to the required position or not.</h4>''', unsafe_allow_html=True)

            st.subheader("**Resume Score📝**")
            st.markdown(
                """
                <style>
                    .stProgress > div > div > div > div {
                        background-color: #d73b5c;
                    }
                </style>""",
                unsafe_allow_html=True,
            )
            my_bar = st.progress(0)
            score = 0
            for percent_complete in range(resume_score):
                score += 1
                time.sleep(0.1)
                my_bar.progress(percent_complete + 1)
            st.success('** Your Resume Writing Score: ' + str(score) + '**')
            st.warning("** Note: This score is calculated based on the content that you have in your Resume. **")
            st.balloons()

            # Inserting data into the database
            insert_data(resume_data['name'], resume_data['email'], resume_score, timestamp,
                        resume_data['no_of_pages'], reco_field, cand_level, str(resume_data['skills']),
                        str(recommended_skills))

            # Bonus Videos
            st.header("**Bonus Video for Resume Writing Tips 💡**")
            resume_vid = random.choice(resume_videos)
            st.video(resume_vid)

            st.header("**Bonus Video for Interview Tips 💡**")
            interview_vid = random.choice(interview_videos)
            st.video(interview_vid)

        else:
            st.error('Something went wrong..')

if __name__ == "__main__":
    run()
