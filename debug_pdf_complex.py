
import os
import sys
import traceback
import tempfile
import logging

# Set up logging to file
logging.basicConfig(filename='debug_pdf_complex.log', level=logging.INFO)

sys.path.append(os.getcwd())

from app.services.selenium_driver import get_pdf_print_driver
from app.resumes.generator import ResumeGenerator

def test_generation_complex():
    try:
        print("Starting complex test...")
        
        generator = ResumeGenerator()
        # Simulate HTML with broken links and complex structure
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Resume Export</title>
            <link rel="stylesheet" href="http://localhost:5000/static/does_not_exist.css">
            <style>
                body { font-family: sans-serif; background: #eee; }
                .content { padding: 20px; color: #333; }
            </style>
        </head>
        <body>
            <div class="content">
                <h1>Complex PDF Test</h1>
                <p>Testing with external links that might fail.</p>
                <img src="http://localhost:5000/static/missing_image.png" alt="Missing">
            </div>
        </body>
        </html>
        """
        output_path = "test_output_complex.pdf"
        
        try:
            success = generator.export_from_raw_html(html_content, output_path)
            if success:
                 print("Export Success")
            else:
                 print("Export Returned False")
                 
        except Exception as e:
            print(f"Export Failed: {e}")
            with open("debug_output_complex.txt", "w") as f:
                f.write(f"Export Failed: {e}\n{traceback.format_exc()}")

    except Exception as e:
        print(f"Global Error: {e}")

if __name__ == "__main__":
    test_generation_complex()
