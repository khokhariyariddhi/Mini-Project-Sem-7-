import os
import re
import pdfplumber
import docx2txt
import spacy
import pandas as pd
from flask import Flask, request, render_template, redirect, url_for, send_file
from werkzeug.utils import secure_filename

# Initialize Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Load spaCy model
nlp = spacy.load('en_core_web_sm')

# Predefined skill list
required_skills = ['python', 'machine learning', 'data analysis', 'sql', 'opencv', 'django', 'flask']

# Function to extract text from files
def extract_text(file_path):
    if file_path.endswith('.pdf'):
        text = ''
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ''
        return text
    elif file_path.endswith('.docx'):
        return docx2txt.process(file_path)
    else:
        return ''

def extract_email(text):
    email = re.findall(r'\S+@\S+', text)
    return email[0] if email else ''

def extract_phone(text):
    phone = re.findall(r'\+?\d[\d -]{8,12}\d', text)
    return phone[0] if phone else ''

def extract_skills(text):
    text = text.lower()
    return [skill for skill in required_skills if skill in text]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    files = request.files.getlist('resumes')
    candidates = []

    for file in files:
        filename = secure_filename(file.filename)
        if filename:
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)

            text = extract_text(save_path)
            doc = nlp(text)

            name = ''
            for ent in doc.ents:
                if ent.label_ == 'PERSON':
                    name = ent.text
                    break

            email = extract_email(text)
            phone = extract_phone(text)
            skills = extract_skills(text)
            score = len(skills)

            candidates.append({
                'Name': name or 'Unknown',
                'Email': email,
                'Phone': phone,
                'Skills': ', '.join(skills),
                'Score': score
            })

    if not candidates:
        return redirect(url_for('index'))

    # Save to Excel
    df = pd.DataFrame(candidates).sort_values(by='Score', ascending=False)
    result_path = os.path.join(app.config['UPLOAD_FOLDER'], 'screened_candidates.xlsx')
    df.to_excel(result_path, index=False)

    # Prepare data for Chart.js
    chart_labels = [c['Name'] for c in candidates]
    chart_scores = [c['Score'] for c in candidates]

    return render_template(
        'result.html',
        candidates=candidates,
        chart_labels=chart_labels,
        chart_scores=chart_scores
    )

@app.route('/download')
def download_file():
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'screened_candidates.xlsx')
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
