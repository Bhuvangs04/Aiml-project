<p><small>Best View in <a href="https://github.com/settings/appearance">Light Mode</a> and Desktop Site (Recommended)</small></p><br/>

<div align="center">
  <h1>AI RESUME ANALYZER</h1>
  <p>A Tool for Resume Analysis, Predictions and Recommendations</p>
  
  <!--links-->
  <h4>
    <a href="#preview-">View Demo</a>
    <span> · </span>
    <a href="#setup--installation-">Installation</a>
    <span> · </span>
  </h4>
</div><br/><br/>

## About the Project 🥱
<div align="center">
    <br/>
    <p align="justify"> 
      A tool which parses information from a resume using natural language processing and finds the keywords, cluster them onto sectors based on their keywords. 
      And lastly show recommendations, predictions, analytics to the applicant / recruiter based on keyword matching.
    </p>
</div>

## Scope 😲
i. It can be used for getting all the resume data into a structured tabular format and csv as well, so that the organization can use those data for analytics purposes

ii. By providing recommendations, predictions and overall score user can improve their resume and can keep on testing it on our tool

iii. And it can increase more traffic to our tool because of user section

iv. It can be used by colleges to get insight of students and their resume before placements

v. Also, to get analytics for roles which users are mostly looking for

vi. To improve this tool by getting feedbacks

<!-- TechStack -->
## Tech Stack 🍻
<details>
<summary>Python version</summary>
<p><a href="https://apps.microsoft.com/detail/9mssztt1n39l?hl=en-us&gl=IN&ocid=pdpshare">Download python version 8</a></p>
</details>
<details>
  <summary>Frontend</summary>
  <ul>
    <li><a href="https://streamlit.io/">Streamlit</a></li>
    <li><a href="https://developer.mozilla.org/en-US/docs/Learn/HTML">HTML</a></li>
    <li><a href="https://developer.mozilla.org/en-US/docs/Web/CSS">CSS</a></li>
    <li><a href="https://developer.mozilla.org/en-US/docs/Learn/JavaScript">JavaScript</a></li>
  </ul>
</details>

<details>
  <summary>Backend</summary>
  <ul>
    <li><a href="https://streamlit.io/">Streamlit</a></li>
    <li><a href="https://www.python.org/">Python</a></li>
  </ul>
</details>

<details>
<summary>Database</summary>
  <ul>
    <li><a href="https://www.mysql.com/">MySQL</a></li>
  </ul>
</details>

<details>
<summary>Modules</summary>
  <ul>
    <li><a href="https://pandas.pydata.org/">pandas</a></li>
    <li><a href="https://github.com/OmkarPathak/pyresparser">pyresparser</a></li>
    <li><a href="https://pypi.org/project/pdfminer3/">pdfminer3</a></li>
    <li><a href="https://plotly.com/">Plotly</a></li>
    <li><a href="https://www.nltk.org/">NLTK</a></li>
  </ul>
</details>

<!-- Features -->
## Features 🤦‍♂️
### Client: -
- Fetching Location and Miscellaneous Data
-Using Parsing Techniques to fetch
- Basic Info
- Skills
- Keywords

Using logical programs, it will recommend
- Skills that can be added
- Predicted job role
- Course and certificates
- Resume tips and ideas
- Overall Score
- Interview, Resume tip videos, coursera & udemy  



### Feedback: -
- Form filling
- Rating from 1 – 5
- Show overall ratings pie chart
- Past user comments history 


### 🔧 Upcoming Feature: Admin Dashboard

The Admin Dashboard will provide comprehensive tools to manage applicant data efficiently. **(Coming Soon)**

**Planned Features:**

- View all applicant data in a tabular format  
- Download user data as a CSV file  
- Access all uploaded resumes from the **Uploaded Resume** folder  
- View user feedback and ratings  

**Data Visualization (via Pie Charts):**

- ⭐ User Ratings  
- 🧠 Predicted Field / Role  
- 💼 Experience Level  
- 📄 Resume Score  
- 👤 User Count  
- 🌆 City Distribution  
- 🗺️ State Distribution  
- 🌍 Country Distribution


## Requirements
### Have these things installed to make your process smooth 
1) Python (3.9.12 or 3.8) https://www.python.org/downloads/release/python-3912/
2) MySQL https://www.mysql.com/downloads/

## Setup & Installation 👀

To run this project, perform the following tasks 😨

Download the code file manually or via git
```bash
git clone https://github.com/Bhuvangs04/Aiml-project.git
```

Create a virtual environment and activate it **(recommended)**

Open your command prompt and change your project directory to ```AI-Resume-Analyzer``` and run the following command 
```bash
python -m venv venvapp

cd venvapp/Scripts

./activate

```

Downloading packages from ```new_requirements.txt``` inside ``App`` folder
```bash
cd../..

cd App

pip install -r new_requirements.txt

python -m spacy download en_core_web_sm

```

After installation is finished create a Database ```cv```

Run the ```App.py``` file using
```bash
streamlit run App.py

```



## Usage
- After the setup it will do stuff's automatically
- You just need to upload a resume and see it's magic
<!-- - Try first with my resume uploaded in ``Uploaded_Resumes`` folder
- Admin userid is ``admin`` and password is ``admin@resume-analyzer`` -->


