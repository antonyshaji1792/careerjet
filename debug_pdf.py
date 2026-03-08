
import os
import sys
import traceback
import tempfile
import logging

# Set up logging to file
logging.basicConfig(filename='debug_pdf.log', level=logging.INFO)

sys.path.append(os.getcwd())

from app.services.selenium_driver import get_pdf_print_driver
from app.resumes.generator import ResumeGenerator

def test_generation():
    try:
        print("Starting test...")
        # Test 1: Driver Initialization
        print("Testing Driver Init...")
        try:
            driver = get_pdf_print_driver()
            print("Driver Init Success")
            driver.quit()
        except Exception as e:
            print(f"Driver Init Failed: {e}")
            with open("debug_output.txt", "w") as f:
                f.write(f"Driver Init Failed: {e}\n{traceback.format_exc()}")
            return

        # Test 2: ResumeGenerator.export_from_raw_html
        print("Testing Export...")
        generator = ResumeGenerator()
        html_content = "<html><body><h1>Test PDF</h1><p>This is a test.</p></body></html>"
        output_path = "test_output.pdf"
        
        try:
            success = generator.export_from_raw_html(html_content, output_path)
            if success:
                 print("Export Success")
                 with open("debug_output.txt", "w") as f:
                     f.write("SUCCESS")
            else:
                 print("Export Returned False")
                 with open("debug_output.txt", "w") as f:
                     f.write("Export returned False (check app logs if possible, or see below)\n")
                     # We can't easily see internal logs unless we redirect logging
        except Exception as e:
            print(f"Export Failed: {e}")
            with open("debug_output.txt", "w") as f:
                f.write(f"Export Failed: {e}\n{traceback.format_exc()}")

    except Exception as e:
        print(f"Global Error: {e}")
        with open("debug_output.txt", "w") as f:
            f.write(f"Global Error: {e}\n{traceback.format_exc()}")

if __name__ == "__main__":
    test_generation()
