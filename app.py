from flask import send_file
from flask import Flask, render_template, request, send_file
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import google.generativeai as genai
from io import BytesIO

app = Flask(__name__)

# Configure API Key
import os

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
print("API KEY FOUND:", bool(os.getenv("GEMINI_API_KEY")))
# Load Model
model = genai.GenerativeModel("gemini-1.5-flash")

@app.route('/', methods=['GET', 'POST'])
def home():

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
            print("ERROR:", str(e))
            generated_testcases = f"Error: {str(e)}"

    return render_template(
        'index.html',
        output=generated_testcases
    )
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
    app.run(debug=True)