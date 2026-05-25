from flask import send_file
from flask import Flask, render_template, request, send_file, redirect, session
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import google.generativeai as genai
from io import BytesIO
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

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/generator', methods=['GET', 'POST'])
def generator():
    
    generated_testcases = ""

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

        except Exception as e:
            generated_testcases = f"Error: {str(e)}"

    return render_template(
        'index.html',
        output=generated_testcases
    )
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':

        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            return "Email already exists!"

        new_user = User(
            name=name,
            email=email,
            password=password
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

        return """
<script>
alert('Account not found! Please register first.');
window.location='/register';
</script>
"""

    return render_template('login.html')
@app.route('/dashboard')
def dashboard():

    if 'user_id' not in session:
        return redirect('/login')

    return render_template(
        'dashboard.html',
        name=session['user_name']
    )
@app.route('/logout')
def logout():

    session.clear()

    return redirect('/')
@app.route('/download', methods=['POST'])
def download():

    text = request.form['output']

    buffer = BytesIO()

    buffer.write(text.encode('utf-8'))

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="Generated_Test_Cases.txt",
        mimetype='text/plain'
    )
    
@app.route('/download_pdf')
def download_pdf():

    text = request.args.get("data", "")

    pdf = SimpleDocTemplate("TestCases.pdf")

    styles = getSampleStyleSheet()

    story = []

    title = Paragraph("<b>Generated Test Cases</b>", styles['Title'])

    story.append(title)

    story.append(Spacer(1, 20))

    content = Paragraph(text.replace("\n", "<br/>"), styles['BodyText'])

    story.append(content)

    pdf.build(story)

    return send_file("TestCases.pdf", as_attachment=True)

if __name__ == '__main__':

    with app.app_context():
        db.create_all()

    app.run(debug=True)