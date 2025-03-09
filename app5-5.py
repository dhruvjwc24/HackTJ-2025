from flask import Flask, request, render_template_string, send_file
import os, shutil, zipfile, whisper, pypandoc, time
import google.generativeai as genai

# Load Whisper model
model = whisper.load_model("base")

# Configure Gemini API
genai.configure(api_key="AIzaSyDesTqNI6JaPpAml8afwUU-H3LPKGjtn50")  # Replace with your actual Gemini API key

app = Flask(__name__)

# Set the upload folder
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
ZIP_FOLDER = "zipped"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["OUTPUT_FOLDER"] = OUTPUT_FOLDER
app.config["ZIP_FOLDER"] = ZIP_FOLDER

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(ZIP_FOLDER, exist_ok=True)

# Function to transcribe audio
import time

# Function to transcribe audio
def transcribe_audio(file_path):
    result = model.transcribe(file_path)
    return result["text"]

# Function to generate LaTeX from transcription
def generate_latex_from_transcription_gemini(transcription, output_file):
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(
        f"Based on the below transcription, please create nicely formatted LaTeX code that separates the content by topic (bolded) and sub notes (bulleted). Ensure all mathematical equations are formatted properly. Make it in-depth, comprehensive, and comprehensible, and verify that all outputted information comes directily from the transcription.\n\n{transcription}"
    )
    latex_code = response.text.replace("```latex", "").replace("```", "").strip()

    # Save LaTeX file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(latex_code)

    return latex_code, output_file

# Function to convert LaTeX to DOCX
def tex_to_docx(tex_file, docx_file):
    try:
        pypandoc.convert_file(tex_file, 'docx', outputfile=docx_file)
        print(f"✅ Converted {tex_file} to {docx_file}")
        return docx_file
    except Exception as e:
        print(f"❌ Error converting {tex_file} to DOCX: {e}")
        return None

# Function to zip all DOCX files
def zip_docx_files():
    zip_filename = os.path.join(app.config["ZIP_FOLDER"], "all_docs.zip")

    # Remove existing ZIP file if exists
    if os.path.exists(zip_filename):
        os.remove(zip_filename)

    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(OUTPUT_FOLDER):
            for file in files:
                if file.endswith(".docx") and file != "output.docx":  # Skip output.docx
                    zipf.write(os.path.join(root, file), file)

    return zip_filename

@app.route("/")
def upload_form():
    return '''
    <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>NOTEify</title>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');
                
                body {
                    font-family: 'Poppins', sans-serif;
                    background-color: #88BDBC;
                    color: #112D32;
                    margin: 0;
                    padding: 0;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                }

                .title-container {
                    text-align: center;
                    margin-bottom: 20px;
                }

                .title {
                    font-size: 36px;
                    font-weight: 700;
                    color: #112D32;
                }

                .subtitle {
                    font-size: 18px;
                    font-style: italic;
                    color: #254E58;
                }

                .container {
                    background-color: #EDEFEF;
                    padding: 30px;
                    border-radius: 12px;
                    box-shadow: 0px 6px 14px rgba(0, 0, 0, 0.15);
                    max-width: 650px;
                    width: 90%;
                    text-align: center;
                }

                h2 {
                    color: #254E58;
                    font-size: 28px;
                    font-weight: 600;
                    margin-bottom: 20px;
                }

                form {
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                }

                input[type="file"], button, input[type="submit"] {
                    padding: 12px 18px;
                    border: none;
                    border-radius: 6px;
                    font-size: 16px;
                    cursor: pointer;
                    transition: 0.3s ease-in-out;
                    font-weight: 500;
                }

                input[type="file"] {
                    background-color: #6E6658;
                    color: white;
                }

                input[type="file"]:hover {
                    background-color: #4F4A41;
                }

                button, input[type="submit"] {
                    background-color: #254E58;
                    color: white;
                }

                button:hover, input[type="submit"]:hover {
                    background-color: #112D32;
                }

                .download-btn {
                    display: inline-block;
                    background-color: #4F4A41;
                    color: white;
                    padding: 8px 15px;
                    margin: 5px;
                    border-radius: 6px;
                    text-decoration: none;
                    font-size: 14px;
                    font-weight: bold;
                    transition: 0.3s;
                }

                .download-btn:hover {
                    background-color: #6E6658;
                }

                footer {
                    margin-top: 20px;
                    color: #254E58;
                    font-size: 14px;
                }
            </style>
        </head>
        <body>
            <div class="title-container">
                <div class="title">NOTEify</div>
                <div class="subtitle">HackTJ 2025</div>
            </div>

            <h2>Upload Files</h2>
            <form action="/upload" method="post" enctype="multipart/form-data">
                <input type="file" name="files" multiple>
                <input type="submit" value="Upload & Process">
            </form>

            <footer>&copy; 2025 NOTEify</footer>
        </body>
    </html>
    '''

@app.route("/upload", methods=["POST"])
def upload_files():
    if "files" not in request.files:
        return "No files part"

    files = request.files.getlist("files")
    if not files or all(file.filename == "" for file in files):
        return "No selected files"

    output_links = []
    
    for file in files:
        original_filename = os.path.splitext(file.filename)[0]  # Get file name without extension
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
        file.save(file_path)

        # Transcribe audio
        transcription = transcribe_audio(file_path)

        # Generate LaTeX filename
        latex_file_path = os.path.join(OUTPUT_FOLDER, f"{original_filename}.tex")
        latex_code, latex_file = generate_latex_from_transcription_gemini(transcription, latex_file_path)

        # Convert LaTeX to DOCX
        docx_file_path = os.path.join(OUTPUT_FOLDER, f"{original_filename}.docx")
        docx_file = tex_to_docx(latex_file, docx_file_path)

        # Append formatted download buttons
        output_links.append(f"""
        <li>
            <span class="file-name">{original_filename}</span>
        </li>
        """)

    # Generate ZIP file
    zip_file_path = zip_docx_files()

    return render_template_string(f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>NOTEify</title>
        <style>
            /* 🌊 Brighter & Bluer UI */
            @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap');

            body {{
                font-family: 'Poppins', sans-serif;
                background-color: #88BDBC;
                color: #112D32;
                margin: 0;
                padding: 0;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
            }}

            .container {{
                background-color: #88BDBC;
                padding: 40px;
                border-radius: 12px;
                width: 60%;
                text-align: center;
                margin: auto;
            }}

            .title {{
                font-size: 36px;
                font-weight: 700;
                color: #112D32;
                margin-bottom: 10px;
            }}

            .subtitle {{
                font-size: 18px;
                font-style: italic;
                color: #254E58;
                margin-bottom: 20px;
            }}

            .button-container {{
                display: flex;
                justify-content: center;
                gap: 15px;
                margin-bottom: 20px;
            }}

            .download-btn {{
                background-color: #112D32;
                color: #88BDBC;
                padding: 10px 18px;
                border-radius: 6px;
                text-decoration: none;
                font-size: 14px;
                font-weight: bold;
                transition: 0.3s;
                text-align: center;
            }}

            .download-btn:hover {{
                background-color: #EDEFEF;
                color: #254E58;
            }}

            ul {{
                list-style: none;
                padding: 0;
                width: 100%;
            }}

            li {{
                background-color: #6E6658;
                margin: 12px 0;
                padding: 15px;
                border-radius: 8px;
                display: flex;
                flex-direction: column;
                align-items: center;
                color: #EDEFEF;
            }}

            .file-name {{
                font-weight: bold;
                font-size: 16px;
                text-align: center;
                margin-bottom: 5px;
            }}

            .download-all {{
                display: inline-block;
                background-color: #112D32;
                color: white;
                padding: 14px 20px;
                border-radius: 8px;
                font-size: 18px;
                font-weight: bold;
                box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.3);
                transition: all 0.3s ease-in-out;
                margin-top: 15px;
                text-align: center;
            }}

            .download-all:hover {{
                background-color: #112D32;
                color: #88BDBC;
                transform: scale(1.05);
            }}

            button {{
                background-color: #112D32;
                color: white;
                padding: 12px 18px;
                border: none;
                border-radius: 6px;
                font-size: 18px;
                font-weight: bold;
                box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.3);
                cursor: pointer;
                transition: 0.3s ease-in-out;
                font-weight: 500;
                text-align: center;
            }}

            button:hover {{
                background-color: #112D32;
                color: #88BDBC;
                transform: scale(1.05);
            }}

            footer {{
                margin-top: 20px;
                color: #254E58;
                font-size: 14px;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="title">NOTEify</div>
            <div class="subtitle">HackTJ 2025</div>

            <h2>Files noteified!</h2>
            <ul>{''.join(output_links)}</ul>
            <br>
            <a href='/download?file={zip_file_path}' class="download-all">📥 Download All DOCX (ZIP)</a>
            <br><br>
            <a href="/"><button>⬅️ Upload More Files</button></a>

            <footer>&copy; 2025 NOTEify</footer>
        </div>
    </body>
    </html>
    """)

@app.route("/download")
def download_file():
    file_path = request.args.get("file")
    return send_file(file_path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)