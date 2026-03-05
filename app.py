import os
import json
from flask import Flask, render_template, request, redirect, url_for
import google.generativeai as genai

app = Flask(__name__)

# --- Gemini API Configuration ---
# Load the API key from an environment variable
try:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set.")
    
    genai.configure(api_key=api_key)
    
    # Define the JSON schema for the expected API response
    # This helps ensure we get structured, usable data from the model
    
    # This is the Python-equivalent of the JSON schema we want back
    # It makes rendering the data in HTML much easier and more reliable
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "careers": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "title": {
                            "type": "STRING",
                            "description": "The name of the career (e.g., 'Data Analyst')"
                        },
                        "match_reason": {
                            "type": "STRING",
                            "description": "A 1-2 sentence explanation of why this is a good match for the user."
                        },
                        "roadmap": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"},
                            "description": "A list of 3-4 actionable steps for this career path."
                        }
                    },
                    "required": ["title", "match_reason", "roadmap"]
                }
            }
        },
        "required": ["careers"]
    }
    
    # We only set the model name here. The full config will be in the request.
    model = genai.GenerativeModel("gemini-2.5-flash-preview-09-2025")
    
except ValueError as e:
    print(e)
    model = None
except Exception as e:
    print(f"An unexpected error occurred during Gemini configuration: {e}")
    model = None

# --- Flask Routes ---

@app.route("/")
def index():
    """Renders the landing page."""
    return render_template("index.html")

@app.route("/assessment")
def assessment():
    """Renders the assessment form page (Feature 1)."""
    return render_template("assessment.html")

@app.route("/results", methods=["POST"])
def results():
    """
    Handles the assessment form data, calls the Gemini API,
    and renders the results page (Features 2 & 3).
    """
    if not model:
        # Handle the case where the model failed to initialize
        return "Error: Gemini API is not configured. Please check your GEMINI_API_KEY.", 500
        
    try:
        # 1. Get data from the form
        subjects = request.form.get("subjects", "")
        hobbies = request.form.get("hobbies", "")
        style = request.form.get("style", "")
        value = request.form.get("value", "")

        # 2. Construct a detailed prompt for the Gemini API
        prompt = f"""
        Act as an expert, encouraging, and insightful career counselor for a high school or early college student.
        
        The student has provided the following information:
        - Favorite Subjects: {subjects}
        - Hobbies and Interests: {hobbies}
        - Preferred Work Style: {style}
        - What they value in a job: {value}

        Based *only* on this information, generate their "Top 3 Career Matches". 
        
        For each of the 3 careers, you must provide:
        1.  `title`: The job title.
        2.  `match_reason`: A 1-2 sentence, encouraging explanation of *why* it's a good match based on their inputs.
        3.  `roadmap`: A list of 3-4 simple, actionable steps a student could take to start exploring this path (e.g., "Join a coding club," "Take an online course in...", "Volunteer for...").

        Return *only* a valid JSON object adhering to the required schema. Do not include any other text or markdown formatting outside the JSON structure.
        """

        # 3. Call the Gemini API
        
        # --- FIX ---
        # Create a single config dictionary for *this specific call*
        # This includes both the MIME type and the required schema.
        request_generation_config = {
            "response_mime_type": "application/json",
            "response_schema": response_schema
        }
        # --- END FIX ---

        chat = model.start_chat()
        
        # Pass the single, combined config dictionary
        response = chat.send_message(
            [prompt],
            generation_config=request_generation_config
        )
        
        # 4. Parse the JSON response
        # The API response text is a JSON string, so we parse it
        response_data = json.loads(response.text)
        careers = response_data.get("careers", [])

        # 5. Render the results template with the data
        return render_template("results.html", careers=careers)
        
    except Exception as e:
        # Basic error handling
        print(f"An error occurred while processing results: {e}")
        return redirect(url_for("error_page", message=str(e)))

@app.route("/error")
def error_page():
    """A generic error page."""
    message = request.args.get("message", "An unknown error occurred.")
    return render_template("error.html", error_message=message)

if __name__ == "__main__":
    app.run(debug=True)