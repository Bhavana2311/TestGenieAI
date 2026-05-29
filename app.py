from flask import send_file
from flask import Flask, render_template, request, send_file, redirect, session
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import google.generativeai as genai
from io import BytesIO
import time

from flask_sqlalchemy import SQLAlchemy
import os


app = Flask(__name__)

app.secret_key = "testgenie_secret_key"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///testgenie.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Configure API Key

api_key = os.getenv("GEMINI_API_KEY")
print("API KEY FOUND:", bool(api_key))
genai.configure(api_key=api_key)

# Load Model
model = genai.GenerativeModel("gemini-2.5-flash")
class User(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)

    email = db.Column(db.String(100), unique=True, nullable=False)

    password = db.Column(db.String(100), nullable=False)

    age = db.Column(db.String(10))

    gender = db.Column(db.String(20))

    phone = db.Column(db.String(20))
class TestCase(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        nullable=False
    )

    requirement = db.Column(
        db.Text,
        nullable=False
    )

    generated_output = db.Column(
        db.Text,
        nullable=False
    )


class Download(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, nullable=False)

    filename = db.Column(db.String(200), nullable=False)

    filetype = db.Column(db.String(20), nullable=False)

    created_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp()
    )
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/generator', methods=['GET', 'POST'])
def generator():
    
    generated_testcases = ""
    requirement = ""

    if request.method == 'POST':

        requirement = request.form['requirement']

        prompt = f"""
Generate software testing test cases for:

{requirement}

Include:
1. Functional Test Cases
2. Negative Test Cases
3. Edge Cases

Format:
- Test Case ID
- Scenario
- Expected Result
"""

        try:
            response = model.generate_content(prompt)
            generated_testcases = response.text
            if 'user_id' in session:
                testcase = TestCase(
                    user_id=session['user_id'],

                    requirement=requirement,

                    generated_output=generated_testcases
               ) 
                db.session.add(testcase)
                db.session.commit()

        except Exception as e:

            if "quota" in str(e).lower():
               generated_testcases = """
        ⚠ Daily AI Limit Reached.
        Please try again later
        OR use another Gemini API Key.
      """
            else:
               generated_testcases = f"Error: {str(e)}"

    return render_template(
    'index.html',
    output=generated_testcases,
    requirement=requirement
)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']

        email = request.form['email']

        password = request.form['password']

        age = request.form['age']

        gender = request.form['gender']

        phone = request.form['phone']

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            return "Email already exists!"

        new_user = User(
            name=name,
            email=email,
            password=password,
            age=age,
            gender=gender,
            phone=phone
        )

        db.session.add(new_user)
        db.session.commit()
        return redirect('/login')

    return render_template('register.html')
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(
            email=email,
            password=password
        ).first()

        if user:

            session['user_id'] = user.id
            session['user_name'] = user.name

            return redirect('/dashboard')

        return render_template(

    'login.html',

    error="Account not found! Please register first."
)

    return render_template('login.html')
@app.route('/dashboard')
def dashboard():

    if 'user_id' not in session:
        return redirect('/login')

    testcases = TestCase.query.filter_by(
        user_id=session['user_id']
    ).all()

    return render_template(

        'dashboard.html',

        name=session['user_name'],

        testcases=testcases
    )
@app.route('/email_settings', methods=['GET', 'POST'])
def email_settings():

    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])

    if request.method == 'POST':

        new_email = request.form['email']

        user.email = new_email

        db.session.commit()

        return redirect('/dashboard')

    return render_template(
        'email_settings.html',
        user=user
    )
@app.route('/downloads_page')
def downloads_page():

    if 'user_id' not in session:
        return redirect('/login')

    downloads = Download.query.filter_by(
        user_id=session['user_id']
    ).all()

    return render_template(
        'downloads.html',
        downloads=downloads
    )
@app.route('/account_settings')
def account_settings():

    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])

    return render_template(
        'account_settings.html',
        user=user
    )
@app.route('/clear_history', methods=['POST'])
def clear_history():

    if 'user_id' not in session:
        return redirect('/login')

    TestCase.query.filter_by(
        user_id=session['user_id']
    ).delete()

    db.session.commit()

    return redirect('/dashboard')
@app.route('/manage_history')
def manage_history():

    if 'user_id' not in session:
        return redirect('/login')

    testcases = TestCase.query.filter_by(
        user_id=session['user_id']
    ).all()

    return render_template(
        'manage_history.html',
        testcases=testcases
    )
@app.route('/delete_selected', methods=['POST'])
def delete_selected():

    selected = request.form.getlist('selected')

    for testcase_id in selected:

        testcase = TestCase.query.get(testcase_id)

        if testcase:
            db.session.delete(testcase)

    db.session.commit()

    return redirect('/dashboard')
@app.route('/delete_all')
def delete_all():

    if 'user_id' not in session:
        return redirect('/login')

    TestCase.query.filter_by(
        user_id=session['user_id']
    ).delete()

    db.session.commit()

    return redirect('/dashboard')
@app.route('/downloads')
def downloads():

        if 'user_id' not in session:
            return redirect('/login')

        files = Download.query.filter_by(
            user_id=session['user_id']
        ).all()

        return render_template(
            'downloads.html',
            files=files
        )
@app.route('/logout')
def logout():

    session.clear()

    return redirect('/')
@app.route('/download', methods=['POST'])
def download():

    text = request.form['output']

    requirement = request.form['requirement']

    safe_name = requirement.replace(" ", "_")

    filename = safe_name + ".txt"

    filepath = os.path.join(
        "saved_downloads",
        filename
    )

    with open(filepath, "w", encoding="utf-8") as file:
        file.write(text)

    if 'user_id' in session:

        new_download = Download(
            user_id=session['user_id'],
            filename=filename,
            filetype="TXT"
        )

        db.session.add(new_download)

        db.session.commit()

    return send_file(
        filepath,
        as_attachment=True
    )
    
@app.route('/download_pdf')
def download_pdf():

    text = request.args.get("data", "")

    requirement = request.args.get("requirement", "TestCase")

    safe_name = requirement.replace(" ", "_")

    filename = safe_name + ".pdf"

    filepath = os.path.join(
        "saved_downloads",
        filename
    )

    pdf = SimpleDocTemplate(filepath)

    styles = getSampleStyleSheet()

    story = []

    title = Paragraph(
        "<b>Generated Test Cases</b>",
        styles['Title']
    )

    story.append(title)

    story.append(Spacer(1, 20))

    content = Paragraph(
        text.replace("\n", "<br/>"),
        styles['BodyText']
    )

    story.append(content)

    pdf.build(story)

    if 'user_id' in session:

        new_download = Download(
            user_id=session['user_id'],
            filename=filename,
            filetype="PDF"
        )

        db.session.add(new_download)

        db.session.commit()

    return send_file(
        filepath,
        as_attachment=True
    )
    
@app.route('/open_download/<filename>')
def open_download(filename):
        filepath = os.path.join(
        "saved_downloads",
        filename
    )
        return send_file(filepath)
@app.route('/delete_download/<int:file_id>')
def delete_download(file_id):

    file = Download.query.get(file_id)

    if file:

        filepath = os.path.join(
            "saved_downloads",
            file.filename
        )

        if os.path.exists(filepath):
            os.remove(filepath)

        db.session.delete(file)
        db.session.commit()

    return redirect('/downloads')
@app.route('/share_download/<filename>')
def share_download(filename):

    return f"""
    <h2>📤 Share File</h2>

    <p>Copy this link to share:</p>

    <input value="http://127.0.0.1:5000/open_download/{filename}"
    style="width:400px;padding:10px;">

    <br><br>

    <a href="/downloads">
    Back
    </a>
    """
@app.route('/edit_download/<int:file_id>', methods=['GET', 'POST'])
def edit_download(file_id):

    file = Download.query.get(file_id)

    if request.method == 'POST':

        new_name = request.form['new_name']

        old_path = os.path.join(
            "saved_downloads",
            file.filename
        )

        extension = file.filename.split(".")[-1]

        new_filename = new_name + "." + extension

        new_path = os.path.join(
            "saved_downloads",
            new_filename
        )

        os.rename(old_path, new_path)

        file.filename = new_filename

        db.session.commit()

        return redirect('/downloads')

    return f"""
    <h2>Edit File Name</h2>

    <form method='POST'>

    <input type='text'
    name='new_name'
    placeholder='Enter new name'
    required>

    <button type='submit'>
    Save
    </button>

    </form>
    """
if __name__ == '__main__':

    if not os.path.exists("saved_downloads"):
        os.makedirs("saved_downloads")

    with app.app_context():
        db.create_all()

    app.run(debug=True)
   