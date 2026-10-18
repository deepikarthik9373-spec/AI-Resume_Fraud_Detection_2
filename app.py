from flask import Flask, render_template, request
import os
import re
from werkzeug.utils import secure_filename
from pypdf import PdfReader

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def calculate_fraud_score(text):
    score = 0

    suspicious_words = [
        "fake", "fraud", "scam", "urgent",
        "verify immediately", "guaranteed",
        "100% job", "pay money", "payment required",
        "fake experience", "forged", "duplicate",
        "certificate available", "guaranteed placement"
    ]

    text_lower = text.lower()

    for word in suspicious_words:
        if word in text_lower:
            score += 8

    # Suspicious email patterns
    if re.search(r"example\.com|test@gmail\.com", text_lower):
        score += 10

    # Unusually large number of numeric sequences
    numbers = re.findall(r"\d+", text)

    if len(numbers) > 15:
        score += 5

    score = min(score, 100)

    if score >= 50:
        result = "High Fraud Risk"
    elif score >= 25:
        result = "Suspicious Resume"
    else:
        result = "Low Fraud Risk"

    return score, result


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_resume():

    if "resume" not in request.files:
        return "No resume selected", 400

    resume = request.files["resume"]

    if resume.filename == "":
        return "Please select a resume", 400

    if not resume.filename.lower().endswith(".pdf"):
        return "Please upload a PDF resume.", 400

    filename = secure_filename(resume.filename)

    if not filename:
        return "Invalid filename.", 400

    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )

    resume.save(file_path)

    try:
        reader = PdfReader(file_path)

        if reader.is_encrypted:
            return "This PDF is password-protected. Upload an unlocked PDF.", 400

        text_parts = []

        for page in reader.pages:
            page_text = page.extract_text()

            if page_text:
                text_parts.append(page_text)

        text = "\n".join(text_parts).strip()

    except Exception as e:
        app.logger.exception("PDF reading error")
        return "Unable to read this PDF. Please upload a valid PDF.", 400

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    if not text:
        return (
            "No readable text found in this PDF. "
            "Please upload a text-based PDF instead of a scanned image."
        ), 400

    score, result = calculate_fraud_score(text)

    return render_template(
        "result.html",
        filename=filename,
        score=score,
        result=result
    )


if __name__ == "__main__":
    app.run(debug=True)