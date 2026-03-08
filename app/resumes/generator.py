import os
import logging
import json
import base64
import tempfile
import time
from jinja2 import Environment, FileSystemLoader
from flask import current_app
from app.services.selenium_driver import get_pdf_print_driver

logger = logging.getLogger(__name__)

class ResumeGenerator:
    """
    Renders structured JSON resumes into ATS-safe formats.
    Supports Jinja2 templating and PDF export via Selenium Headless (Chrome).
    """
    
    def __init__(self, template_dir=None):
        if not template_dir:
            template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        self.env = Environment(loader=FileSystemLoader(template_dir))

    def render_html(self, resume_json, template_name='modern.jinja'):
        """Renders resume JSON into HTML string."""
        try:
            template = self.env.get_template(template_name)
            return template.render(**resume_json)
        except Exception as e:
            logger.error(f"HTML rendering failed: {str(e)}")
            return None

    def render_ats_text(self, resume_json, template_name='ats_clean.jinja'):
        """Renders resume into clean, ATS-parsable plain text."""
        try:
            template = self.env.get_template(template_name)
            return template.render(**resume_json)
        except Exception as e:
            logger.error(f"ATS Text rendering failed: {str(e)}")
            return None

    def export_pdf(self, resume_json, output_path, template_name='modern.jinja'):
        """
        Converts resume JSON to PDF using Selenium Headless Chrome.
        Backwards compatible method using server-side templates.
        """
        try:
            html_content = self.render_html(resume_json, template_name)
            if not html_content:
                return False
            return self.print_html_to_pdf(html_content, output_path)
        except Exception as e:
            logger.error(f"PDF export failed: {str(e)}")
            return False

    def export_from_raw_html(self, raw_html, output_path):
        """
        Exports a PDF directly from a raw HTML string provided by the client.
        This ensures exact WYSIWYG fidelity.
        """
        try:
            with open("debug_generator.log", "a") as f:
                f.write(f"Generator called. Path: {output_path}\n")
        except:
            pass
        return self.print_html_to_pdf(raw_html, output_path)

    def print_html_to_pdf(self, html_content, output_path):
        """
        Internal method to handle the actual printing of an HTML string to PDF via Selenium.
        """
        driver = None
        temp_html_path = None
        
        try:
            logger.info("Starting PDF generation process...")
            # 1. Save to temp file
            # Use delete=False to ensure it persists for the browser to read, and close it immediately.
            with tempfile.NamedTemporaryFile(suffix='.html', delete=False, mode='w', encoding='utf-8') as f:
                f.write(html_content)
                temp_html_path = f.name
            logger.info(f"Temp HTML file created at: {temp_html_path}")
            
            # 2. Initialize Headless Driver
            logger.info("Initializing Selenium Driver...")
            driver = get_pdf_print_driver()
            logger.info("Selenium Driver initialized successfully.")
            
            # 3. Load page
            file_url = f"file:///{temp_html_path.replace(os.sep, '/')}"
            logger.info(f"Loading page: {file_url}")
            driver.get(file_url)
            
            # Allow time for rendering (fonts, layout)
            time.sleep(1)
            
            # 4. Print to PDF using CDP
            # A4 dimensions in inches: 8.27 x 11.7
            print_options = {
                'landscape': False,
                'displayHeaderFooter': False,
                'printBackground': True, # Important for CSS backgrounds
                'preferCSSPageSize': True, # Respect @page CSS
                'marginTop': 0, 
                'marginBottom': 0, 
                'marginLeft': 0, 
                'marginRight': 0
            }
            
            logger.info("Executing CDP Page.printToPDF...")
            result = driver.execute_cdp_cmd("Page.printToPDF", print_options)
            
            if 'data' not in result:
                logger.error("CDP Page.printToPDF returned no data.")
                raise Exception("CDP Page.printToPDF failed to return data")
                
            pdf_bytes = base64.b64decode(result['data'])
            logger.info(f"PDF data received, size: {len(pdf_bytes)} bytes")
            
            # 5. Write to output
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)
            logger.info(f"PDF successfully persisted to {output_path}")
                
            return True
            
        except Exception as e:
            logger.error(f"PDF printing failed with unexpected error: {str(e)}")
            import traceback
            tb = traceback.format_exc()
            logger.error(tb)
            
            # EMERGENCY DEBUG LOGGING
            try:
                debug_path = r"c:\Users\suppo\OneDrive\Desktop\careerjet\pdf_gen_error_full.log"
                with open(debug_path, "w") as f:
                    f.write(f"Error: {str(e)}\n\nTraceback:\n{tb}")
            except:
                pass
                
            return False
                
            return False
            
        finally:
            # Cleanup
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            if temp_html_path and os.path.exists(temp_html_path):
                try:
                    os.remove(temp_html_path)
                except:
                    pass

    def export_markdown(self, resume_json, output_path, template_name='ats_clean.jinja'):
        """Exports to markdown, which is highly ATS-friendly."""
        content = self.render_ats_text(resume_json, template_name)
        if not content:
            return False
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error(f"Markdown export failed: {str(e)}")
            return False
