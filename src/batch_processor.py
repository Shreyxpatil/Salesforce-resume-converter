import os
import time
import zipfile
import shutil
from werkzeug.utils import secure_filename
from resume_parser_general import extract_resume_data
from docx_converter_general import convert_resume_to_docx

# Configuration
TEMPLATE_PATH = "src/templates/resume_template_general.jinja2.html"
OUTPUT_DIR = "processed_resumes"
ZIP_NAME = "converted_resumes.zip"

def ensure_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)

def create_zip_archive(source_dir, output_filename):
    """Zips all .docx files in the directory"""
    zip_path = os.path.join(source_dir, output_filename)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(source_dir):
            for file in files:
                if file.endswith('.docx'):
                    file_path = os.path.join(root, file)
                    arcname = os.path.basename(file_path)
                    zipf.write(file_path, arcname)
    return zip_path

def process_batch(input_file_paths):
    """
    input_file_paths: List of full paths to the uploaded PDF/DOCX files
    """
    ensure_directory(OUTPUT_DIR)
    
    successful_files = []
    failed_files = []

    print(f"🚀 Starting Batch Process for {len(input_file_paths)} files...")

    for index, file_path in enumerate(input_file_paths):
        filename = os.path.basename(file_path)
        print(f"\nProcessing {index + 1}/{len(input_file_paths)}: {filename}")

        # 1. Define paths
        base_name = os.path.splitext(filename)[0]
        # Sanitize filename to prevent issues
        safe_name = secure_filename(base_name)
        
        temp_html_path = os.path.join(OUTPUT_DIR, f"{safe_name}_temp.html")
        final_docx_path = os.path.join(OUTPUT_DIR, f"Converted_{safe_name}.docx")

        try:
            # 2. Extract Data (Gemini)
            # We add a small delay before starting to help avoid 429 errors on the first hit
            if index > 0: 
                print("⏳ Cooling down API (5s)...")
                time.sleep(5) 

            extraction_success = extract_resume_data(file_path, TEMPLATE_PATH, temp_html_path)

            if extraction_success:
                # 3. Convert HTML to DOCX
                convert_resume_to_docx(temp_html_path, final_docx_path)
                print(f"✅ Converted: {final_docx_path}")
                successful_files.append(final_docx_path)
                
                # Cleanup HTML to keep folder clean
                if os.path.exists(temp_html_path):
                    os.remove(temp_html_path)
            else:
                print(f"❌ Failed to parse: {filename}")
                failed_files.append(filename)

        except Exception as e:
            print(f"❌ Error processing {filename}: {str(e)}")
            failed_files.append(filename)

    # 4. Create ZIP if we have results
    if successful_files:
        print(f"\n📦 Zipping {len(successful_files)} documents...")
        zip_path = create_zip_archive(OUTPUT_DIR, ZIP_NAME)
        print(f"🎉 Batch Complete! Download here: {zip_path}")
        return zip_path, failed_files
    else:
        print("\n❌ No files were successfully converted.")
        return None, failed_files