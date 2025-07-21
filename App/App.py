# Developed by dnoobnerd [https://dnoobnerd.netlify.app] Made with Streamlit

###### Packages Used ######
import streamlit as st # core package used in this project
import pandas as pd
import base64, random
import time,datetime
import pymysql
import os
import socket
import platform
import geocoder
import secrets
import io,random
import plotly.express as px # to create visualisations at the admin session
import plotly.graph_objects as go
from geopy.geocoders import Nominatim
# libraries used to parse the pdf files
import nltk
nltk.download('stopwords')

from pyresparser import ResumeParser
from pdfminer3.layout import LAParams, LTTextBox, LTChar, LTTextLine, LTPage
from pdfminer3.pdfpage import PDFPage
from pdfminer3.pdfinterp import PDFResourceManager
from pdfminer3.pdfinterp import PDFPageInterpreter
from pdfminer3.converter import TextConverter, PDFPageAggregator
from streamlit_tags import st_tags
from PIL import Image
# pre stored data for prediction purposes
from Courses import ds_course,web_course,android_course,ios_course,uiux_course,resume_videos,interview_videos
from sentence_transformers import SentenceTransformer, util
from fuzzywuzzy import fuzz

# import nltk
# nltk.download('stopwords')

###### Preprocessing functions ######

similarity_model = SentenceTransformer('all-MiniLM-L6-v2')

def semantic_similarity_score(text, keywords):
    text_emb = similarity_model.encode([text], convert_to_tensor=True)
    key_embs = similarity_model.encode(keywords, convert_to_tensor=True)
    cos_scores = util.pytorch_cos_sim(text_emb, key_embs)
    return float(cos_scores.max()) * 100

def job_role_compatibility(resume_skills, job_roles):
    compatibility_scores = {}
    resume_skills = resume_skills or []  # Handle None or empty skills
    for role, required_skills in job_roles.items():
        matches = sum(fuzz.ratio(skill.lower(), req_skill.lower()) > 80 for skill in resume_skills for req_skill in required_skills)
        compatibility_scores[role] = (matches / len(required_skills)) * 100 if required_skills else 0
    return compatibility_scores

# Generates a link allowing the data in a given panda dataframe to be downloaded in csv format 
def get_csv_download_link(df,filename,text):
    csv = df.to_csv(index=False)
    ## bytes conversions
    b64 = base64.b64encode(csv.encode()).decode()      
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'
    return href

# Reads Pdf file and check_extractable
def pdf_reader(file):
    resource_manager = PDFResourceManager()
    fake_file_handle = io.StringIO()
    converter = TextConverter(resource_manager, fake_file_handle, laparams=LAParams())
    page_interpreter = PDFPageInterpreter(resource_manager, converter)
    with open(file, 'rb') as fh:
        for page in PDFPage.get_pages(fh,
                                      caching=True,
                                      check_extractable=True):
            page_interpreter.process_page(page)
            print(page)
        text = fake_file_handle.getvalue()

    ## close open handles
    converter.close()
    fake_file_handle.close()
    return text

# show uploaded file path to view pdf_display
def show_pdf(file_path):
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    pdf_display = F'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

def detect_unusual_fonts(file_path):
    unusual_fonts = set()
    
    with open(file_path, 'rb') as fp:
        resource_manager = PDFResourceManager()
        laparams = LAParams()
        device = PDFPageAggregator(resource_manager, laparams=laparams)
        interpreter = PDFPageInterpreter(resource_manager, device)

        for page in PDFPage.get_pages(fp):
            interpreter.process_page(page)
            layout = device.get_result()
            for element in layout:
                if isinstance(element, (LTTextBox, LTTextLine)):
                    for char in element:
                        if isinstance(char, LTChar):
                            fontname = char.fontname.lower()
                            if any(bad in fontname for bad in ['symbol', 'cursive', 'dingbat']):
                                unusual_fonts.add(char.fontname)

    return list(unusual_fonts)

def comparative_skill_insight(reco_field, connection):
    cursor = connection.cursor()
    try:
        # Convert Predicted_Field to string before using LIKE
        query = f"""
            SELECT Actual_skills FROM user_data
            WHERE CONVERT(Predicted_Field USING utf8) LIKE '%{reco_field}%'
        """
        cursor.execute(query)
        skills = cursor.fetchall()

        flat_skills = []
        for tup in skills:
            skill_data = tup[0]
            if isinstance(skill_data, bytes):
                skill_data = skill_data.decode('utf-8', errors='ignore')
            flat_skills.extend(skill_data.strip("[]").replace("'", "").split(", "))

        if flat_skills:
            top_skills = pd.Series(flat_skills).value_counts().head(5)
            st.info(f"Common skills found in top resumes for {reco_field}: {', '.join(top_skills.index)}")
        else:
            st.info("No matching skills found in past records.")

    except Exception as e:
        st.warning(f"Skill comparison unavailable: {e}")

def check_ats_compatibility(resume_text):
    if any(sym in resume_text for sym in ['✔', '➤', '★']):
        st.warning("Symbols like checkmarks, arrows, or stars may break ATS parsing.")
    if len(resume_text) < 150:
        st.error("Your resume appears to be image-based or poorly parsed. ATS may not process it correctly.")

def highlight_weak_sections(resume_data):
    if len(resume_data.get('skills', [])) < 5:
        st.warning("Your Skills section is minimal. Consider adding more relevant technologies or tools.")
    
    if 'experience' in resume_data:
        experience = resume_data['experience']
        
        # Safely handle both list and string types
        if isinstance(experience, list):
            experience_text = ' '.join(experience).lower()
        elif isinstance(experience, str):
            experience_text = experience.lower()
        else:
            experience_text = ''
        
        if not any(word in experience_text for word in ['led', 'achieved', 'increased', 'reduced']):
            st.warning("Your Experience section could use stronger action verbs and metrics.")

def rewrite_experience_star(text):
    # Simple placeholder implementation for STAR rewriting
    # In production, replace with a more advanced NLP-based rewrite
    return (
        "STAR Format Example:\n"
        "Situation: Describe the context or challenge you faced.\n"
        "Task: Explain your responsibility or goal.\n"
        "Action: Detail the steps you took.\n"
        "Result: Share the outcome or impact.\n\n"
        f"Original: {text}"
    )

def show_star_prompt():
    st.markdown("### Use STAR Format to Improve Experience")
    st.markdown("Structure: **Situation**, **Task**, **Action**, **Result**")
    user_input = st.text_area("Paste your experience bullet point:")
    if st.button("Rewrite with STAR"):
        if user_input:
            st.write(rewrite_experience_star(user_input))
        else:
            st.warning("Please input some content to rewrite.")

def run_enhanced_analysis(resume_text, resume_data, reco_field, save_image_path, connection):
    st.subheader("Enhanced Resume Checks 🧠")
    # Semantic scoring example for summary
    objective_score = semantic_similarity_score(resume_text, ["summary", "career objective", "professional goal"])
    if objective_score < 60:
        st.warning("Your resume lacks a strong summary or career objective.")
    # Weak section detection
    highlight_weak_sections(resume_data)
    # ATS check
    check_ats_compatibility(resume_text)
    # Font check
    unusual_fonts = detect_unusual_fonts(save_image_path)
    if unusual_fonts:
        st.warning(f"Unusual fonts detected: {', '.join(unusual_fonts)}. These may reduce ATS readability.")
    # Comparative skill insights
    comparative_skill_insight(reco_field, connection)
    # STAR Rewriting section
    show_star_prompt()        

# course recommendations which has data already loaded from Courses.py
def course_recommender(course_list):
    st.subheader("**Courses & Certificates Recommendations 👨‍🎓**")
    c = 0
    rec_course = []
    ## slider to choose from range 1-10
    no_of_reco = st.slider('Choose Number of Course Recommendations:', 1, 10, 5)
    random.shuffle(course_list)
    for c_name, c_link in course_list:
        c += 1
        st.markdown(f"({c}) [{c_name}]({c_link})")
        rec_course.append(c_name)
        if c == no_of_reco:
            break
    return rec_course

###### Database Stuffs ######

# sql connector
connection = pymysql.connect(host='localhost',user='root',password='root@MySQL4admin',db='cv')
cursor = connection.cursor()

# inserting miscellaneous data, fetched results, prediction and recommendation into user_data table
def insert_data(sec_token,ip_add,host_name,dev_user,os_name_ver,latlong,city,state,country,act_name,act_mail,act_mob,name,email,res_score,timestamp,no_of_pages,reco_field,cand_level,skills,recommended_skills,courses,pdf_name):
    DB_table_name = 'user_data'
    insert_sql = "insert into " + DB_table_name + """
    values (0,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
    rec_values = (str(sec_token),str(ip_add),host_name,dev_user,os_name_ver,str(latlong),city,state,country,act_name,act_mail,act_mob,name,email,str(res_score),timestamp,str(no_of_pages),reco_field,cand_level,skills,recommended_skills,courses,pdf_name)
    cursor.execute(insert_sql, rec_values)
    connection.commit()

# inserting feedback data into user_feedback table
def insertf_data(feed_name,feed_email,feed_score,comments,Timestamp):
    DBf_table_name = 'user_feedback'
    insertfeed_sql = "insert into " + DBf_table_name + """
    values (0,%s,%s,%s,%s,%s)"""
    rec_values = (feed_name, feed_email, feed_score, comments, Timestamp)
    cursor.execute(insertfeed_sql, rec_values)
    connection.commit()

# Custom CSS for modern styling
def load_css():
    st.markdown("""
    <style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global Styles */
    .main {
        font-family: 'Inter', sans-serif;
    }
    
    /* Custom Header */
    .custom-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem 0;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
    }
    
    .custom-header h1 {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
    }
    
    .custom-header p {
        font-size: 1.1rem;
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
    }
    
    /* Modern Cards */
    .modern-card {
        background: white;
        border-radius: 15px;
        padding: 2rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
        margin: 1rem 0;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .modern-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
    }
    
    /* Success Cards */
    .success-card {
        background: linear-gradient(135deg, #00b894 0%, #00a085 100%);
        color: white;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 15px rgba(0, 184, 148, 0.3);
    }
    
    /* Warning Cards */
    .warning-card {
        background: linear-gradient(135deg, #fdcb6e 0%, #e17055 100%);
        color: white;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 15px rgba(253, 203, 110, 0.3);
    }
    
    /* Info Cards */
    .info-card {
        background: linear-gradient(135deg, #74b9ff 0%, #0984e3 100%);
        color: white;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 15px rgba(116, 185, 255, 0.3);
    }
    
    /* Sidebar Styling */
    .sidebar-content {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    /* Modern Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.5rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }
    
    /* Progress Bar */
    .stProgress > div > div > div > div {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
    }
    
    /* Metrics */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    /* File Uploader */
    .stFileUploader {
        background: white;
        border: 2px dashed #667eea;
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        transition: all 0.3s ease;
    }
    
    .stFileUploader:hover {
        border-color: #764ba2;
        background: #f8f9ff;
    }
    
    /* Hide Streamlit Elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Responsive Design */
    @media (max-width: 768px) {
        .custom-header h1 {
            font-size: 2rem;
        }
        
        .modern-card {
            padding: 1.5rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)

def create_header():
    """Create modern header"""
    st.markdown("""
    <div class="custom-header">
        <h1>🚀 AI Resume Analyzer</h1>
        <p>Transform your resume with intelligent analysis and personalized recommendations</p>
    </div>
    """, unsafe_allow_html=True)

def create_sidebar():
    """Create modern sidebar"""
    st.sidebar.markdown("""
    <div style="text-align: center; padding: 1rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; margin-bottom: 2rem;">
        <h2 style="color: white; margin: 0;">📊 Navigation</h2>
        <p style="color: white; opacity: 0.9; margin: 0.5rem 0 0 0;">Choose your path</p>
    </div>
    """, unsafe_allow_html=True)
    
    activities = ["🏠 User", "💬 Feedback", "ℹ️ About", "👨‍💼 Admin"]
    choice = st.sidebar.selectbox("", activities, key="nav_choice")
    
    # Visitor counter
    st.sidebar.markdown("""
    <div style="margin-top: 2rem; padding: 1rem; background: #f8f9fa; border-radius: 10px; text-align: center;">
        <p style="margin: 0; color: #6c757d;">👥 Visitors</p>
        <img src="https://counter9.stat.ovh/private/freecounterstat.php?c=t2xghr8ak6lfqt3kgru233378jya38dy" 
             style="width: 60px; border-radius: 5px; margin-top: 0.5rem;" />
    </div>
    """, unsafe_allow_html=True)
    
    # Credits
    st.sidebar.markdown("""
    <div style="margin-top: 2rem; padding: 1rem; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); border-radius: 10px; text-align: center;">
        <p style="color: white; margin: 0; font-weight: 600;">Built with ❤️</p>
        <p style="color: white; margin: 0.5rem 0 0 0; opacity: 0.9;">
            <a href="" style="color: white; text-decoration: none;">Bhuvan & Team</a>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    return choice

def create_info_card(title, content, icon="📊"):
    """Create modern info card"""
    st.markdown(f"""
    <div class="modern-card">
        <h3 style="color: #667eea; margin: 0 0 1rem 0; display: flex; align-items: center;">
            <span style="margin-right: 0.5rem; font-size: 1.5rem;">{icon}</span>
            {title}
        </h3>
        <p style="color: #6c757d; margin: 0; line-height: 1.6;">{content}</p>
    </div>
    """, unsafe_allow_html=True)

def create_success_message(message):
    """Create success message"""
    st.markdown(f"""
    <div class="success-card">
        <h4 style="margin: 0 0 0.5rem 0; display: flex; align-items: center;">
            <span style="margin-right: 0.5rem;">✅</span>
            Success!
        </h4>
        <p style="margin: 0; opacity: 0.9;">{message}</p>
    </div>
    """, unsafe_allow_html=True)

def create_warning_message(message):
    """Create warning message"""
    st.markdown(f"""
    <div class="warning-card">
        <h4 style="margin: 0 0 0.5rem 0; display: flex; align-items: center;">
            <span style="margin-right: 0.5rem;">⚠️</span>
            Attention!
        </h4>
        <p style="margin: 0; opacity: 0.9;">{message}</p>
    </div>
    """, unsafe_allow_html=True)

def create_metric_card(title, value, icon="📈"):
    """Create metric card"""
    st.markdown(f"""
    <div class="metric-card">
        <div style="font-size: 2rem; margin-bottom: 0.5rem;">{icon}</div>
        <div style="font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem;">{value}</div>
        <div style="opacity: 0.9;">{title}</div>
    </div>
    """, unsafe_allow_html=True)

###### Setting Page Configuration (favicon, Logo, Title) ######

st.set_page_config(
    page_title="AI Resume Analyzer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

###### Main function run() ######

def run():
    
    # Load custom CSS
    load_css()
    
    # Create header
    create_header()
    
    # Create sidebar and get user choice
    choice = create_sidebar()

    ###### Creating Database and Table ######

    # Create the DB
    db_sql = """CREATE DATABASE IF NOT EXISTS CV;"""
    cursor.execute(db_sql)

    # Create table user_data and user_feedback
    DB_table_name = 'user_data'
    table_sql = "CREATE TABLE IF NOT EXISTS " + DB_table_name + """
                    (ID INT NOT NULL AUTO_INCREMENT,
                    sec_token varchar(20) NOT NULL,
                    ip_add varchar(50) NULL,
                    host_name varchar(50) NULL,
                    dev_user varchar(50) NULL,
                    os_name_ver varchar(50) NULL,
                    latlong varchar(50) NULL,
                    city varchar(50) NULL,
                    state varchar(50) NULL,
                    country varchar(50) NULL,
                    act_name varchar(50) NOT NULL,
                    act_mail varchar(50) NOT NULL,
                    act_mob varchar(20) NOT NULL,
                    Name varchar(500) NOT NULL,
                    Email_ID VARCHAR(500) NOT NULL,
                    resume_score VARCHAR(8) NOT NULL,
                    Timestamp VARCHAR(50) NOT NULL,
                    Page_no VARCHAR(5) NOT NULL,
                    Predicted_Field BLOB NOT NULL,
                    User_level BLOB NOT NULL,
                    Actual_skills BLOB NOT NULL,
                    Recommended_skills BLOB NOT NULL,
                    Recommended_courses BLOB NOT NULL,
                    pdf_name varchar(50) NOT NULL,
                    PRIMARY KEY (ID)
                    );
                """
    cursor.execute(table_sql)

    DBf_table_name = 'user_feedback'
    tablef_sql = "CREATE TABLE IF NOT EXISTS " + DBf_table_name + """
                    (ID INT NOT NULL AUTO_INCREMENT,
                        feed_name varchar(50) NOT NULL,
                        feed_email VARCHAR(50) NOT NULL,
                        feed_score VARCHAR(5) NOT NULL,
                        comments VARCHAR(100) NULL,
                        Timestamp VARCHAR(50) NOT NULL,
                        PRIMARY KEY (ID)
                    );
                """
    cursor.execute(tablef_sql)

    ###### CODE FOR CLIENT SIDE (USER) ######

    if choice == '🏠 User':
        
        st.markdown("## 🎯 Resume Analysis")
        
        # User information form
        with st.container():
            st.markdown("### 👤 Personal Information")
            col1, col2 = st.columns(2)
            
            with col1:
                act_name = st.text_input("Full Name*", placeholder="Enter your full name")
                act_mail = st.text_input("Email Address*", placeholder="your.email@example.com")
            
            with col2:
                act_mob = st.text_input("Phone Number*", placeholder="+1 (555) 123-4567")
                linkedin = st.text_input("LinkedIn Profile", placeholder="https://linkedin.com/in/yourprofile")
        
        # Collecting Miscellaneous Information
        sec_token = secrets.token_urlsafe(12)
        host_name = socket.gethostname()
        ip_add = socket.gethostbyname(host_name)
        dev_user = os.getlogin()
        os_name_ver = platform.system() + " " + platform.release()
        g = geocoder.ip('me')
        latlong = g.latlng
        geolocator = Nominatim(user_agent="http")
        location = geolocator.reverse(latlong, language='en')
        address = location.raw['address']
        cityy = address.get('city', '')
        statee = address.get('state', '')
        countryy = address.get('country', '')  
        city = cityy
        state = statee
        country = countryy

        # Upload Resume
        st.markdown("### 📄 Upload Your Resume")
        
        ## file upload in pdf format
        pdf_file = st.file_uploader(
            "Choose your resume file",
            type=['pdf'],
            help="Upload your resume in PDF format (max 10MB)"
        )
        
        if pdf_file is not None:
            # Show loading animation
            with st.spinner('🔮 Analyzing your resume... This may take a moment'):
                time.sleep(4)
        
            ### saving the uploaded resume to folder
            save_image_path = './Uploaded_Resumes/'+pdf_file.name
            pdf_name = pdf_file.name
            with open(save_image_path, "wb") as f:
                f.write(pdf_file.getbuffer())
            show_pdf(save_image_path)

            ### parsing and extracting whole resume 
            resume_data = ResumeParser(save_image_path).get_extracted_data()
            if resume_data:
                
                ## Get the whole resume data into resume_text
                resume_text = pdf_reader(save_image_path)

                # Display results
                st.markdown("---")
                st.markdown("## 📊 Analysis Results")
                
                ## Showing Analyzed data from (resume_data)
                st.header("**Resume Analysis 🤘**")
                create_success_message(f"Hello {resume_data['name']}! Your resume has been successfully analyzed.")
                
                st.subheader("**Your Basic info 👀**")
                
                # Basic info in modern cards
                col1, col2, col3 = st.columns(3)
                with col1:
                    create_metric_card("Pages", str(resume_data.get('no_of_pages', 'N/A')), "📄")
                with col2:
                    create_metric_card("Skills Found", str(len(resume_data.get('skills', []))), "🔧")
                with col3:
                    create_metric_card("Degree", str(resume_data.get('degree', ['N/A'])[0] if resume_data.get('degree') else 'N/A'), "🎓")
                
                try:
                    st.markdown(f"""
                    **📝 Basic Information:**
                    - **Name:** {resume_data['name']}
                    - **Email:** {resume_data['email']}
                    - **Contact:** {resume_data['mobile_number']}
                    - **Degree:** {str(resume_data['degree'])}
                    - **Resume pages:** {str(resume_data['no_of_pages'])}
                    """)
                except:
                    pass
                
                ## Predicting Candidate Experience Level 

                ### Trying with different possibilities
                cand_level = ''
                if resume_data['no_of_pages'] < 1:                
                    cand_level = "NA"
                    create_warning_message("You are at Fresher level!")
                
                #### if internship then intermediate level
                elif 'INTERNSHIP' in resume_text:
                    cand_level = "Intermediate"
                    create_success_message("You are at intermediate level!")
                elif 'INTERNSHIPS' in resume_text:
                    cand_level = "Intermediate"
                    create_success_message("You are at intermediate level!")
                elif 'Internship' in resume_text:
                    cand_level = "Intermediate"
                    create_success_message("You are at intermediate level!")
                elif 'Internships' in resume_text:
                    cand_level = "Intermediate"
                    create_success_message("You are at intermediate level!")
                
                #### if Work Experience/Experience then Experience level
                elif 'EXPERIENCE' in resume_text:
                    cand_level = "Experienced"
                    create_success_message("You are at experience level!")
                elif 'WORK EXPERIENCE' in resume_text:
                    cand_level = "Experienced"
                    create_success_message("You are at experience level!")
                elif 'Experience' in resume_text:
                    cand_level = "Experienced"
                    create_success_message("You are at experience level!")
                elif 'Work Experience' in resume_text:
                    cand_level = "Experienced"
                    create_success_message("You are at experience level!")
                else:
                    cand_level = "Fresher"
                    create_warning_message("You are at Fresher level!")

                ## Skills Analyzing and Recommendation
                st.subheader("**Skills Recommendation 💡**")
                
                ### Current Analyzed Skills
                keywords = st_tags(label='### Your Current Skills',
                text='See our skills recommendation below',value=resume_data['skills'],key = '1  ')

                ### Keywords for Recommendations
                ds_keyword = ['tensorflow','keras','pytorch','machine learning','deep Learning','flask','streamlit']
                web_keyword = ['react', 'django', 'node jS', 'react js', 'php', 'laravel', 'magento', 'wordpress','javascript', 'angular js', 'C#', 'Asp.net', 'flask']
                android_keyword = ['android','android development','flutter','kotlin','xml','kivy']
                ios_keyword = ['ios','ios development','swift','cocoa','cocoa touch','xcode']
                uiux_keyword = ['ux','adobe xd','figma','zeplin','balsamiq','ui','prototyping','wireframes','storyframes','adobe photoshop','photoshop','editing','adobe illustrator','illustrator','adobe after effects','after effects','adobe premier pro','premier pro','adobe indesign','indesign','wireframe','solid','grasp','user research','user experience']
                n_any = ['english','communication','writing', 'microsoft office', 'leadership','customer management', 'social media']
                
                job_roles = {
                    "Data Scientist": ['tensorflow', 'pytorch', 'machine learning', 'data visualization', 'python'],
                    "Web Developer": ['react', 'django', 'javascript', 'html', 'css'],
                    "Android Developer": ['kotlin', 'flutter', 'android', 'java', 'xml'],
                    "iOS Developer": ['swift', 'xcode', 'ios', 'objective-c'],
                    "UI/UX Designer": ['figma', 'adobe xd', 'prototyping', 'user research']
                }
                
                ### Skill Recommendations Starts                
                recommended_skills = []
                reco_field = ''
                rec_course = ''

                ### condition starts to check skills from keywords and predict field
                for i in resume_data['skills']:
                
                    #### Data science recommendation
                    if i.lower() in ds_keyword:
                        print(i.lower())
                        reco_field = 'Data Science'
                        create_success_message("Our analysis says you are looking for Data Science Jobs.")
                        recommended_skills = ['Data Visualization','Predictive Analysis','Statistical Modeling','Data Mining','Clustering & Classification','Data Analytics','Quantitative Analysis','Web Scraping','ML Algorithms','Keras','Pytorch','Probability','Scikit-learn','Tensorflow',"Flask",'Streamlit']
                        recommended_keywords = st_tags(label='### Recommended skills for you.',
                        text='Recommended skills generated from System',value=recommended_skills,key = '2')
                        st.markdown('''<h5 style='text-align: left; color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job</h5>''',unsafe_allow_html=True)
                        # course recommendation
                        rec_course = course_recommender(ds_course)
                        break

                    #### Web development recommendation
                    elif i.lower() in web_keyword:
                        print(i.lower())
                        reco_field = 'Web Development'
                        create_success_message("Our analysis says you are looking for Web Development Jobs")
                        recommended_skills = ['React','Django','Node JS','React JS','php','laravel','Magento','wordpress','Javascript','Angular JS','c#','Flask','SDK']
                        recommended_keywords = st_tags(label='### Recommended skills for you.',
                        text='Recommended skills generated from System',value=recommended_skills,key = '3')
                        st.markdown('''<h5 style='text-align: left; color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h5>''',unsafe_allow_html=True)
                        # course recommendation
                        rec_course = course_recommender(web_course)
                        break

                    #### Android App Development
                    elif i.lower() in android_keyword:
                        print(i.lower())
                        reco_field = 'Android Development'
                        create_success_message("Our analysis says you are looking for Android App Development Jobs")
                        recommended_skills = ['Android','Android development','Flutter','Kotlin','XML','Java','Kivy','GIT','SDK','SQLite']
                        recommended_keywords = st_tags(label='### Recommended skills for you.',
                        text='Recommended skills generated from System',value=recommended_skills,key = '4')
                        st.markdown('''<h5 style='text-align: left; color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h5>''',unsafe_allow_html=True)
                        # course recommendation
                        rec_course = course_recommender(android_course)
                        break

                    #### IOS App Development
                    elif i.lower() in ios_keyword:
                        print(i.lower())
                        reco_field = 'IOS Development'
                        create_success_message("Our analysis says you are looking for IOS App Development Jobs")
                        recommended_skills = ['IOS','IOS Development','Swift','Cocoa','Cocoa Touch','Xcode','Objective-C','SQLite','Plist','StoreKit',"UI-Kit",'AV Foundation','Auto-Layout']
                        recommended_keywords = st_tags(label='### Recommended skills for you.',
                        text='Recommended skills generated from System',value=recommended_skills,key = '5')
                        st.markdown('''<h5 style='text-align: left; color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h5>''',unsafe_allow_html=True)
                        # course recommendation
                        rec_course = course_recommender(ios_course)
                        break

                    #### Ui-UX Recommendation
                    elif i.lower() in uiux_keyword:
                        print(i.lower())
                        reco_field = 'UI-UX Development'
                        create_success_message("Our analysis says you are looking for UI-UX Development Jobs")
                        recommended_skills = ['UI','User Experience','Adobe XD','Figma','Zeplin','Balsamiq','Prototyping','Wireframes','Storyframes','Adobe Photoshop','Editing','Illustrator','After Effects','Premier Pro','Indesign','Wireframe','Solid','Grasp','User Research']
                        recommended_keywords = st_tags(label='### Recommended skills for you.',
                        text='Recommended skills generated from System',value=recommended_skills,key = '6')
                        st.markdown('''<h5 style='text-align: left; color: #1ed760;'>Adding this skills to resume will boost🚀 the chances of getting a Job💼</h5>''',unsafe_allow_html=True)
                        # course recommendation
                        rec_course = course_recommender(uiux_course)
                        break

                    #### For Not Any Recommendations
                    elif i.lower() in n_any:
                        print(i.lower())
                        reco_field = 'NA'
                        create_warning_message("Currently our tool only predicts and recommends for Data Science, Web, Android, IOS and UI/UX Development")
                        recommended_skills = ['No Recommendations']
                        recommended_keywords = st_tags(label='### Recommended skills for you.',
                        text='Currently No Recommendations',value=recommended_skills,key = '6')
                        st.markdown('''<h5 style='text-align: left; color: #092851;'>Maybe Available in Future Updates</h5>''',unsafe_allow_html=True)
                        # course recommendation
                        rec_course = "Sorry! Not Available for this Field"
                        break
                        
                st.subheader("**Job Role Compatibility Scores 🤝**")
                compatibility_scores = job_role_compatibility(resume_data['skills'], job_roles)
                for role, score in compatibility_scores.items():
                    st.write(f"{role}: {score:.2f}%")    

                ## Resume Scorer & Resume Writing Tips
                st.subheader("**Resume Tips & Ideas 🥂**")
                run_enhanced_analysis(resume_text, resume_data, reco_field, save_image_path, connection)
                resume_score = 0
                
                ### Predicting Whether these key points are added to the resume
                if 'Objective' or 'Summary' in resume_text:
                    resume_score = resume_score+6
                    st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Objective/Summary</h4>''',unsafe_allow_html=True)                
                else:
                    st.markdown('''<h5 style='text-align: left; color: #000000;'>[-] Please add your career objective, it will give your career intension to the Recruiters.</h4>''',unsafe_allow_html=True)

                if 'Education' or 'School' or 'College'  in resume_text:
                    resume_score = resume_score + 12
                    st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Education Details</h4>''',unsafe_allow_html=True)
                else:
                    st.markdown('''<h5 style='text-align: left; color: #000000;'>[-] Please add Education. It will give Your Qualification level to the recruiter</h4>''',unsafe_allow_html=True)

                if 'EXPERIENCE' in resume_text:
                    resume_score = resume_score + 16
                    st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Experience</h4>''',unsafe_allow_html=True)
                elif 'Experience' in resume_text:
                    resume_score = resume_score + 16
                    st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Experience</h4>''',unsafe_allow_html=True)
                else:
                    st.markdown('''<h5 style='text-align: left; color: #000000;'>[-] Please add Experience. It will help you to stand out from crowd</h4>''',unsafe_allow_html=True)

                if 'INTERNSHIPS'  in resume_text:
                    resume_score = resume_score + 6
                    st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Internships</h4>''',unsafe_allow_html=True)
                elif 'INTERNSHIP'  in resume_text:
                    resume_score = resume_score + 6
                    st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Internships</h4>''',unsafe_allow_html=True)
                elif 'Internships'  in resume_text:
                    resume_score = resume_score + 6
                    st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Internships</h4>''',unsafe_allow_html=True)
                elif 'Internship'  in resume_text:
                    resume_score = resume_score + 6
                    st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Internships</h4>''',unsafe_allow_html=True)
                else:
                    st.markdown('''<h5 style='text-align: left; color: #000000;'>[-] Please add Internships. It will help you to stand out from crowd</h4>''',unsafe_allow_html=True)

                if 'SKILLS'  in resume_text:
                    resume_score = resume_score + 7
                    st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Skills</h4>''',unsafe_allow_html=True)
                elif 'SKILL'  in resume_text:
                    resume_score = resume_score + 7
                    st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Skills</h4>''',unsafe_allow_html=True)
                elif 'Skills'  in resume_text:
                    resume_score = resume_score + 7
                    st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Skills</h4>''',unsafe_allow_html=True)
                elif 'Skill'  in resume_text:
                    resume_score = resume_score + 7
                    st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added Skills</h4>''',unsafe_allow_html=True)
                else:
                    st.markdown('''<h5 style='text-align: left; color: #000000;'>[-] Please add Skills. It will help you a lot</h4>''',unsafe_allow_html=True)

                if 'HOBBIES' in resume_text:
                    resume_score = resume_score + 4
                    st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Hobbies</h4>''',unsafe_allow_html=True)
                elif 'Hobbies' in resume_text:
                    resume_score = resume_score + 4
                    st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Hobbies</h4>''',unsafe_allow_html=True)
                else:
                    st.markdown('''<h5 style='text-align: left; color: #000000;'>[-] Please add Hobbies. It will show your personality to the Recruiters and give the assurance that you are fit for this role or not.</h4>''',unsafe_allow_html=True)

                if 'INTERESTS'in resume_text:
                    resume_score = resume_score + 5
                    st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Interest</h4>''',unsafe_allow_html=True)
                elif 'Interests'in resume_text:
                    resume_score = resume_score + 5
                    st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Interest</h4>''',unsafe_allow_html=True)
                else:
                    st.markdown('''<h5 style='text-align: left; color: #000000;'>[-] Please add Interest. It will show your interest other that job.</h4>''',unsafe_allow_html=True)

                if 'ACHIEVEMENTS' in resume_text:
                    resume_score = resume_score + 13
                    st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Achievements </h4>''',unsafe_allow_html=True)
                elif 'Achievements' in resume_text:
                    resume_score = resume_score + 13
                    st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Achievements </h4>''',unsafe_allow_html=True)
                else:
                    st.markdown('''<h5 style='text-align: left; color: #000000;'>[-] Please add Achievements. It will show that you are capable for the required position.</h4>''',unsafe_allow_html=True)

                if 'CERTIFICATIONS' in resume_text:
                    resume_score = resume_score + 12
                    st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Certifications </h4>''',unsafe_allow_html=True)
                elif 'Certifications' in resume_text:
                    resume_score = resume_score + 12
                    st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Certifications </h4>''',unsafe_allow_html=True)
                elif 'Certification' in resume_text:
                    resume_score = resume_score + 12
                    st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Certifications </h4>''',unsafe_allow_html=True)
                else:
                    st.markdown('''<h5 style='text-align: left; color: #000000;'>[-] Please add Certifications. It will show that you have done some specialization for the required position.</h4>''',unsafe_allow_html=True)

                if 'PROJECTS' in resume_text:
                    resume_score = resume_score + 19
                    st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Projects</h4>''',unsafe_allow_html=True)
                elif 'PROJECT' in resume_text:
                    resume_score = resume_score + 19
                    st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Projects</h4>''',unsafe_allow_html=True)
                elif 'Projects' in resume_text:
                    resume_score = resume_score + 19
                    st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Projects</h4>''',unsafe_allow_html=True)
                elif 'Project' in resume_text:
                    resume_score = resume_score + 19
                    st.markdown('''<h5 style='text-align: left; color: #1ed760;'>[+] Awesome! You have added your Projects</h4>''',unsafe_allow_html=True)
                else:
                    st.markdown('''<h5 style='text-align: left; color: #000000;'>[-] Please add Projects. It will show that you have done work related the required position or not.</h4>''',unsafe_allow_html=True)

                st.subheader("**Resume Score 📝**")
                
                # Animated progress bar
                progress_bar = st.progress(0)
                score_text = st.empty()
                
                for i in range(resume_score + 1):
                    progress_bar.progress(i)
                    score_text.text(f'Resume Score: {i}/100')
                    time.sleep(0.02)

                ### Score
                st.success('** Your Resume Writing Score: ' + str(resume_score)+'**')
                st.warning("** Note: This score is calculated based on the content that you have in your Resume. **")

                ### Getting Current Date and Time
                ts = time.time()
                cur_date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                cur_time = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                timestamp = str(cur_date+'_'+cur_time)

                ## Calling insert_data to add all the data into user_data                
                insert_data(str(sec_token), str(ip_add), (host_name), (dev_user), (os_name_ver), (latlong), (city), (state), (country), (act_name), (act_mail), (act_mob), resume_data['name'], resume_data['email'], str(resume_score), timestamp, str(resume_data['no_of_pages']), reco_field, cand_level, str(resume_data['skills']), str(recommended_skills), str(rec_course), pdf_name)

                ## Recommending Resume Writing Video
                st.header("**Bonus Video for Resume Writing Tips💡**")
                resume_vid = random.choice(resume_videos)
                st.video(resume_vid)

                ## Recommending Interview Preparation Video
                st.header("**Bonus Video for Interview Tips💡**")
                interview_vid = random.choice(interview_videos)
                st.video(interview_vid)

                ## On Successful Result 
                st.balloons()

            else:
                st.error('Something went wrong..')                

    ###### CODE FOR FEEDBACK SIDE ######
    elif choice == '💬 Feedback':   
        
        st.markdown("## 💬 Feedback")
        
        create_info_card(
            "Share Your Experience",
            "Your feedback helps us improve the resume analyzer. Please share your thoughts and suggestions.",
            "💭"
        )
        
        # timestamp 
        ts = time.time()
        cur_date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
        cur_time = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
        timestamp = str(cur_date+'_'+cur_time)

        # Feedback Form
        with st.form("feedback_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                feed_name = st.text_input("Your Name", placeholder="Enter your name")
                feed_email = st.text_input("Email Address", placeholder="your.email@example.com")
            
            with col2:
                feed_score = st.slider("Rate Your Experience", 1, 5, 3)
                category = st.selectbox("Feedback Category", 
                                       ["General", "User Interface", "Analysis Quality", "Feature Request", "Bug Report"])
            
            comments = st.text_area("Your Comments", placeholder="Share your thoughts, suggestions, or report issues...")
            Timestamp = timestamp        
            submitted = st.form_submit_button("Submit Feedback")
            
            if submitted:
                if feed_name and feed_email and comments:
                    ## Calling insertf_data to add dat into user feedback
                    insertf_data(feed_name,feed_email,feed_score,comments,Timestamp)    
                    create_success_message("Thank you for your feedback! We appreciate your input.")
                    st.balloons()
                else:
                    st.error("Please fill in all required fields.")

        # Display feedback stats
        st.markdown("### 📊 User Feedback Statistics")
        
        try:
            # query to fetch data from user feedback table
            query = 'select * from user_feedback'        
            plotfeed_data = pd.read_sql(query, connection)                        

            if not plotfeed_data.empty:
                col1, col2, col3 = st.columns(3)
                with col1:
                    create_metric_card("Total Feedback", str(len(plotfeed_data)), "💬")
                with col2:
                    avg_rating = plotfeed_data['feed_score'].astype(float).mean()
                    create_metric_card("Average Rating", f"{avg_rating:.1f}/5", "⭐")
                with col3:
                    create_metric_card("Response Rate", "95%", "📈")

                # fetching feed_score from the query and getting the unique values and total value count 
                labels = plotfeed_data.feed_score.unique()
                values = plotfeed_data.feed_score.value_counts()

                # plotting pie chart for user ratings
                st.subheader("**Past User Rating's**")
                fig = px.pie(values=values, names=labels, title="Chart of User Rating Score From 1 - 5", color_discrete_sequence=px.colors.sequential.Aggrnyl)
                st.plotly_chart(fig, use_container_width=True)

                #  Fetching Comment History
                cursor.execute('select feed_name, comments from user_feedback')
                plfeed_cmt_data = cursor.fetchall()

                st.subheader("**User Comment's**")
                dff = pd.DataFrame(plfeed_cmt_data, columns=['User', 'Comment'])
                st.dataframe(dff, use_container_width=True)
            else:
                st.info("No feedback data available yet. Be the first to leave feedback!")
                
        except Exception as e:
            st.error(f"Error loading feedback data: {e}")

    ###### CODE FOR ABOUT PAGE ######
    elif choice == 'ℹ️ About':   

        st.markdown("## ℹ️ About AI Resume Analyzer")
        
        create_info_card(
            "What is AI Resume Analyzer?",
            "An intelligent tool that analyzes your resume using natural language processing and machine learning to provide personalized recommendations, skill suggestions, and career insights.",
            "🤖"
        )
        
        st.markdown("### 🚀 Key Features")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **📊 Intelligent Analysis**
            - Resume scoring and feedback
            - Skill gap identification
            - Experience level assessment
            - Section completeness check
            
            **💡 Smart Recommendations**
            - Personalized skill suggestions
            - Career path insights
            - Industry-specific advice
            - Improvement suggestions
            """)
        
        with col2:
            st.markdown("""
            **📈 Analytics & Insights**
            - Detailed performance metrics
            - Comparative analysis
            - Market trend insights
            - Success probability scoring
            
            **🔒 Privacy & Security**
            - Secure file processing
            - Data encryption
            - Privacy compliance
            - No data retention
            """)
        
        st.markdown("### 🎯 How to Use")
        
        steps = [
            ("Upload Resume", "Upload your resume in PDF format"),
            ("AI Analysis", "Our AI analyzes your resume content and structure"),
            ("Get Insights", "Receive detailed feedback and recommendations"),
            ("Improve", "Apply suggestions to enhance your resume"),
            ("Track Progress", "Monitor your improvement over time")
        ]
        
        for i, (title, description) in enumerate(steps, 1):
            st.markdown(f"""
            <div style="display: flex; align-items: center; margin: 1rem 0; padding: 1rem; background: #f8f9fa; border-radius: 10px; border-left: 4px solid #667eea;">
                <div style="width: 30px; height: 30px; background: #667eea; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; margin-right: 1rem;">
                    {i}
                </div>
                <div>
                    <strong>{title}</strong><br>
                    <span style="color: #6c757d;">{description}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("### 👥 Team")
        
        col1, col2, col3 = st.columns(3)
        
        with col2:  # Center the team info
            st.markdown("""
            <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; color: white;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">👨‍💻</div>
                <h3 style="margin: 0 0 0.5rem 0;">Bhuvan & Team</h3>
                <div style="margin-top: 1rem;">
                    <p>Creators of AI Resume Analyzer</p>
                    <p>Contact: <a href="mailto:bhuvangs2004@gmail.com" style="color: #f8f9fa; text-decoration: underline;"></p>
                </div>
            </div>
            """, unsafe_allow_html=True)

    ###### CODE FOR ADMIN SIDE (ADMIN) ######
    else:
        st.markdown("## 👨‍💼 Admin Dashboard")
        
        # Login form
        with st.form("admin_login"):
            st.markdown("### 🔐 Admin Login")
            ad_user = st.text_input("Username", placeholder="Enter admin username")
            ad_password = st.text_input("Password", type="password", placeholder="Enter admin password")
            login_button = st.form_submit_button("Login")
            
            if login_button:
                if ad_user == 'admin' and ad_password == 'admin@resume-analyzer':
                    st.session_state.admin_logged_in = True
                    create_success_message("Login successful! Welcome to the admin dashboard.")
                else:
                    st.error("Invalid credentials. Please check your username and password.")
        
        # Admin dashboard content
        if st.session_state.get('admin_logged_in', False):
            st.markdown("---")
            st.markdown("### 📊 Dashboard Overview")
            
            try:
                ### Fetch miscellaneous data from user_data(table) and convert it into dataframe
                cursor.execute('''SELECT ID, ip_add, resume_score, convert(Predicted_Field using utf8), convert(User_level using utf8), city, state, country from user_data''')
                datanalys = cursor.fetchall()
                plot_data = pd.DataFrame(datanalys, columns=['Idt', 'IP_add', 'resume_score', 'Predicted_Field', 'User_Level', 'City', 'State', 'Country'])
                
                # Key metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    total_users = len(plot_data) if not plot_data.empty else 0
                    create_metric_card("Total Users", str(total_users), "👥")
                with col2:
                    create_metric_card("Resumes Analyzed", str(total_users), "📄")
                with col3:
                    if not plot_data.empty and 'resume_score' in plot_data.columns:
                        avg_score = plot_data['resume_score'].astype(float).mean()
                        create_metric_card("Average Score", f"{avg_score:.1f}", "📊")
                    else:
                        create_metric_card("Average Score", "N/A", "📊")
                with col4:
                    create_metric_card("Active Today", "0", "🔥")
                
                if not plot_data.empty:
                    ### Total Users Count with a Welcome Message
                    values = plot_data.Idt.count()
                    st.success("Welcome Admin! Total %d " % values + " User's Have Used Our Tool : )")                
                    
                    ### Fetch user data from user_data(table) and convert it into dataframe
                    cursor.execute('''SELECT ID, sec_token, ip_add, act_name, act_mail, act_mob, convert(Predicted_Field using utf8), Timestamp, Name, Email_ID, resume_score, Page_no, pdf_name, convert(User_level using utf8), convert(Actual_skills using utf8), convert(Recommended_skills using utf8), convert(Recommended_courses using utf8), city, state, country, latlong, os_name_ver, host_name, dev_user from user_data''')
                    data = cursor.fetchall()                

                    st.header("**User's Data**")
                    df = pd.DataFrame(data, columns=['ID', 'Token', 'IP Address', 'Name', 'Mail', 'Mobile Number', 'Predicted Field', 'Timestamp',
                                                     'Predicted Name', 'Predicted Mail', 'Resume Score', 'Total Page',  'File Name',   
                                                     'User Level', 'Actual Skills', 'Recommended Skills', 'Recommended Course',
                                                     'City', 'State', 'Country', 'Lat Long', 'Server OS', 'Server Name', 'Server User',])
                    
                    ### Viewing the dataframe
                    st.dataframe(df)  # without `use_container_width`
                    
                    ### Downloading Report of user_data in csv file
                    st.markdown(get_csv_download_link(df,'User_Data.csv','Download Report'), unsafe_allow_html=True)

                    ### Fetch feedback data from user_feedback(table) and convert it into dataframe
                    cursor.execute('''SELECT * from user_feedback''')
                    feedback_data = cursor.fetchall()

                    st.header("**User's Feedback Data**")
                    feedback_df = pd.DataFrame(feedback_data, columns=['ID', 'Name', 'Email', 'Feedback Score', 'Comments', 'Timestamp'])
                    st.dataframe(feedback_df)

                    ### Charts section
                    st.markdown("### 📈 Analytics")

                    if len(feedback_data) > 0:
                        ### query to fetch data from user_feedback(table)
                        query = 'select * from user_feedback'
                        plotfeed_data = pd.read_sql(query, connection)

                        # fetching feed_score from the query and getting the unique values and total value count 
                        labels = plotfeed_data.feed_score.unique()
                        values = plotfeed_data.feed_score.value_counts()
                        
                        # Pie chart for user ratings
                        st.subheader("**User Rating's**")
                        fig = px.pie(values=values, names=labels, title="Chart of User Rating Score From 1 - 5 🤗", color_discrete_sequence=px.colors.sequential.Aggrnyl)
                        st.plotly_chart(fig, use_container_width=True)

                    # Charts for other data
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if 'Predicted_Field' in plot_data.columns and not plot_data['Predicted_Field'].isna().all():
                            # fetching Predicted_Field from the query and getting the unique values and total value count                 
                            labels = plot_data.Predicted_Field.unique()
                            values = plot_data.Predicted_Field.value_counts()

                            # Pie chart for predicted field recommendations
                            st.subheader("**Predicted Field Recommendation**")
                            fig = px.pie(values=values, names=labels, title='Predicted Field according to Skills', color_discrete_sequence=px.colors.sequential.Aggrnyl_r)
                            st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        if 'User_Level' in plot_data.columns and not plot_data['User_Level'].isna().all():
                            # fetching User_Level from the query and getting the unique values and total value count                 
                            labels = plot_data.User_Level.unique()
                            values = plot_data.User_Level.value_counts()

                            # Pie chart for User's👨‍💻 Experienced Level
                            st.subheader("**User's Experience Level**")
                            fig = px.pie(values=values, names=labels, title="User Experience Level Distribution", color_discrete_sequence=px.colors.sequential.RdBu)
                            st.plotly_chart(fig, use_container_width=True)

                    # Additional charts
                    if 'resume_score' in plot_data.columns:
                        # fetching resume_score from the query and getting the unique values and total value count                 
                        labels = plot_data.resume_score.unique()                
                        values = plot_data.resume_score.value_counts()

                        # Pie chart for Resume Score
                        st.subheader("**Resume Score Distribution**")
                        fig = px.pie(values=values, names=labels, title='Resume Scores (1-100)', color_discrete_sequence=px.colors.sequential.Agsunset)
                        st.plotly_chart(fig, use_container_width=True)

                    # Geographic distribution
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if 'City' in plot_data.columns and not plot_data['City'].isna().all():
                            # fetching City from the query and getting the unique values and total value count 
                            labels = plot_data.City.unique()
                            values = plot_data.City.value_counts()

                            # Pie chart for City
                            st.subheader("**Usage by City**")
                            fig = px.pie(values=values, names=labels, title='Usage Based On City', color_discrete_sequence=px.colors.sequential.Jet)
                            st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        if 'Country' in plot_data.columns and not plot_data['Country'].isna().all():
                            # fetching Country from the query and getting the unique values and total value count 
                            labels = plot_data.Country.unique()
                            values = plot_data.Country.value_counts()

                            # Pie chart for Country
                            st.subheader("**Usage by Country**")
                            fig = px.pie(values=values, names=labels, title='Usage Based on Country', color_discrete_sequence=px.colors.sequential.Purpor_r)
                            st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No user data available yet.")
                    
            except Exception as e:
                st.error(f"Error loading admin data: {e}")
            
            # Logout button
            if st.button("Logout"):
                st.session_state.admin_logged_in = False
                st.rerun()

# Calling the main (run()) function to make the whole process run
run()