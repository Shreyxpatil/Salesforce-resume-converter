# from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Form, APIRouter
# from fastapi.responses import FileResponse, JSONResponse
# from fastapi.staticfiles import StaticFiles
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# import os
# import uuid
# import shutil
# from typing import Optional, Dict, Any, List
# import glob
# import zipfile
# from datetime import datetime
# import asyncio
# from concurrent.futures import ThreadPoolExecutor
# import re 

# # --- UPDATED IMPORTS: Use the new Split Parsers ---
# try:
#     import src.resume_parser_general as parser_gen
#     import src.resume_parser_salesforce as parser_sf
#     import src.docx_converter_general as docx_gen
#     import src.docx_converter_salesforce as docx_sf
# except ImportError:
#     # Fallback if running as module
#     from src import resume_parser_general as parser_gen
#     from src import resume_parser_salesforce as parser_sf
#     from src import docx_converter_general as docx_gen
#     from src import docx_converter_salesforce as docx_sf

# # --- GLOBAL APP DEFINITION (Required for Uvicorn reload) ---
# app = FastAPI(
#     title="Resume Conversion API",
#     description="Convert PDF/DOCX resumes to structured DOCX format using AI",
#     version="3.1.0"
# )

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# router = APIRouter(tags=["Resume Converter"])

# # Create necessary directories
# os.makedirs("output", exist_ok=True)
# os.makedirs("frontend", exist_ok=True)
# os.makedirs("templates", exist_ok=True)

# # Mount static files
# app.mount("/output", StaticFiles(directory="output"), name="output")
# app.mount("/static", StaticFiles(directory="frontend"), name="static")

# # In-memory job status tracking
# job_status = {}

# # Thread pool for parallel processing
# executor = ThreadPoolExecutor(max_workers=4)

# # Template Map
# TEMPLATE_MAP = {
#     "classic": "resume_template_general.jinja2.html",
#     "salesforce": "resume_template_salesforce.jinja2.html"
# }

# class ConversionResponse(BaseModel):
#     job_id: str
#     status: str
#     message: str
#     download_url: Optional[str] = None
#     file_count: Optional[int] = None
#     error: Optional[str] = None

# class JobStatusResponse(BaseModel):
#     job_id: str
#     status: str
#     progress: str
#     total_files: Optional[int] = None
#     completed_files: Optional[int] = None
#     failed_files: Optional[int] = None
#     result: Optional[Dict[str, Any]] = None
#     error: Optional[str] = None

# def cleanup_old_files():
#     """Clean up files older than 24 hours"""
#     try:
#         current_time = datetime.now()
#         for temp_dir in glob.glob("temp_*"):
#             if os.path.exists(temp_dir):
#                 dir_time = datetime.fromtimestamp(os.path.getctime(temp_dir))
#                 if (current_time - dir_time).total_seconds() > 3600:
#                     shutil.rmtree(temp_dir)
        
#         for output_file in glob.glob("output/*.docx") + glob.glob("output/*.zip"):
#             if os.path.exists(output_file):
#                 file_time = datetime.fromtimestamp(os.path.getctime(output_file))
#                 if (current_time - file_time).total_seconds() > 3600:
#                     os.remove(output_file)
#     except Exception as e:
#         print(f"⚠️ Cleanup warning: {e}")

# @app.get("/")
# async def serve_frontend():
#     return FileResponse("frontend/index.html")

# @app.post("/api/convert-resume", response_model=ConversionResponse)
# async def convert_single_resume(
#     background_tasks: BackgroundTasks,
#     resume_file: UploadFile = File(...),
#     template_choice: str = Form("classic"), # 'classic' or 'salesforce'
#     output_name: Optional[str] = Form(None)
# ):
#     cleanup_old_files()
    
#     if not (resume_file.filename.lower().endswith('.pdf') or resume_file.filename.lower().endswith('.docx')):
#         raise HTTPException(status_code=400, detail="File must be PDF or DOCX")
    
#     job_id = str(uuid.uuid4())
#     temp_dir = f"temp_{job_id}"
#     os.makedirs(temp_dir, exist_ok=True)
    
#     file_ext = os.path.splitext(resume_file.filename)[1].lower()
#     resume_path = f"{temp_dir}/uploaded_resume{file_ext}"
    
#     with open(resume_path, "wb") as buffer:
#         shutil.copyfileobj(resume_file.file, buffer)
    
#     # Template Selection
#     template_filename = TEMPLATE_MAP.get(template_choice, "resume_template_general.jinja2.html")
#     template_path = os.path.join("templates", template_filename)
    
#     # Output Filename
#     if output_name:
#         clean = "".join(c for c in output_name if c.isalnum() or c in (' ', '-', '_')).rstrip().replace(' ', '_')
#     else:
#         original = os.path.splitext(resume_file.filename)[0]
#         clean = "".join(c for c in original if c.isalnum() or c in (' ', '-', '_')).rstrip().replace(' ', '_')
    
#     docx_filename = f"converted_resume_{clean}.docx"
#     final_docx_path = f"output/{docx_filename}"
    
#     job_status[job_id] = {
#         "status": "processing",
#         "progress": "Starting...",
#         "resume_path": resume_path,
#         "template_path": template_path,
#         "temp_dir": temp_dir,
#         "final_docx_path": final_docx_path,
#         "docx_filename": docx_filename,
#         "template_choice": template_choice
#     }
    
#     background_tasks.add_task(
#         process_single_resume,
#         job_id, resume_path, template_path, temp_dir, final_docx_path, docx_filename, template_choice
#     )
    
#     return ConversionResponse(
#         job_id=job_id, status="processing", message="Started", download_url=f"/output/{docx_filename}", file_count=1
#     )

# @app.post("/api/convert-resumes-batch", response_model=ConversionResponse)
# async def convert_batch_resumes(
#     background_tasks: BackgroundTasks,
#     resume_files: List[UploadFile] = File(...),
#     template_choice: str = Form("classic"),
#     output_name: Optional[str] = Form(None)
# ):
#     cleanup_old_files()
#     if not resume_files: raise HTTPException(status_code=400, detail="No files")
    
#     job_id = str(uuid.uuid4())
#     temp_dir = f"temp_batch_{job_id}"
#     os.makedirs(temp_dir, exist_ok=True)
    
#     saved_files = []
#     for idx, file in enumerate(resume_files):
#         if not (file.filename.lower().endswith('.pdf') or file.filename.lower().endswith('.docx')): continue
#         ext = os.path.splitext(file.filename)[1].lower()
#         clean = "".join(c for c in os.path.splitext(file.filename)[0] if c.isalnum() or c in (' ', '-', '_')).rstrip().replace(' ', '_')
#         path = f"{temp_dir}/resume_{idx}_{clean}{ext}"
#         with open(path, "wb") as buffer: shutil.copyfileobj(file.file, buffer)
#         saved_files.append({"path": path, "clean_name": clean, "index": idx})
            
#     template_filename = TEMPLATE_MAP.get(template_choice, "resume_template_general.jinja2.html")
#     template_path = os.path.join("templates", template_filename)

#     if output_name:
#         clean_zip = "".join(c for c in output_name if c.isalnum() or c in (' ', '-', '_')).rstrip().replace(' ', '_')
#         zip_filename = f"converted_zip_{clean_zip}.zip"
#     else:
#         zip_filename = f"converted_batch_{job_id[:8]}.zip"
    
#     final_zip_path = f"output/{zip_filename}"
    
#     job_status[job_id] = {
#         "status": "processing",
#         "progress": "Starting batch...",
#         "total_files": len(saved_files),
#         "completed_files": 0,
#         "failed_files": 0,
#         "zip_filename": zip_filename
#     }
    
#     background_tasks.add_task(
#         process_batch_resumes,
#         job_id, saved_files, template_path, temp_dir, final_zip_path, zip_filename, template_choice
#     )
    
#     return ConversionResponse(
#         job_id=job_id, status="processing", message="Batch started", download_url=f"/output/{zip_filename}", file_count=len(saved_files)
#     )

# @app.get("/api/job-status/{job_id}", response_model=JobStatusResponse)
# async def get_job_status(job_id: str):
#     if job_id not in job_status: raise HTTPException(status_code=404, detail="Job not found")
#     data = job_status[job_id]
    
#     resp = JobStatusResponse(
#         job_id=job_id, status=data["status"], progress=data["progress"],
#         total_files=data.get("total_files"), completed_files=data.get("completed_files"), failed_files=data.get("failed_files")
#     )
    
#     if data["status"] == "completed":
#         dl = data.get("zip_filename") or data.get("docx_filename")
#         resp.result = {"download_url": f"/output/{dl}"}
#         if data.get("failed_details"): resp.result["failed_details"] = data["failed_details"]
#     elif data["status"] == "error":
#         resp.error = data.get("error")
        
#     return resp

# @app.get("/output/{filename}")
# async def download_file(filename: str):
#     path = os.path.join("output", filename)
#     if not os.path.exists(path): raise HTTPException(status_code=404, detail="File not found")
#     return FileResponse(path=path, filename=filename)

# # --- WORKER FUNCTIONS ---

# async def process_single_resume(job_id, resume_path, template_path, temp_dir, final_path, filename, choice):
#     try:
#         job_status[job_id]["progress"] = "Extracting Data..."
#         temp_html = os.path.join(temp_dir, "temp.html")
        
#         # === SWITCH LOGIC ===
#         if choice == "salesforce":
#             print(f"🔹 Using Salesforce Parser for Job {job_id}")
#             success = parser_sf.extract_resume_data(resume_path, template_path, temp_html)
#         else:
#             print(f"🔹 Using General Parser for Job {job_id}")
#             success = parser_gen.extract_resume_data(resume_path, template_path, temp_html)
            
#         if not success: raise Exception("Extraction Failed")
        
#         job_status[job_id]["progress"] = "Creating DOCX..."
        
#         # === SWITCH CONVERTER ===
#         if choice == "salesforce":
#             docx_sf.convert_salesforce_resume(temp_html, final_path)
#         else:
#             docx_gen.convert_resume_to_docx(temp_html, final_path)
            
#         job_status[job_id]["status"] = "completed"
#         job_status[job_id]["progress"] = "Done"
#     except Exception as e:
#         job_status[job_id]["status"] = "error"
#         job_status[job_id]["error"] = str(e)

# def process_single_resume_sync(file_info, template_path, temp_dir, job_id, choice):
#     try:
#         path = file_info["path"]
#         name = file_info["clean_name"]
#         idx = file_info["index"]
#         temp_html = f"{temp_dir}/temp_{idx}.html"
        
#         if choice == "salesforce":
#             success = parser_sf.extract_resume_data(path, template_path, temp_html)
#         else:
#             success = parser_gen.extract_resume_data(path, template_path, temp_html)
            
#         if not success: return {"success": False, "name": name, "error": "Extraction Failed"}
        
#         docx_path = f"{temp_dir}/converted_{name}.docx"
        
#         if choice == "salesforce":
#             docx_sf.convert_salesforce_resume(temp_html, docx_path)
#         else:
#             docx_gen.convert_resume_to_docx(temp_html, docx_path)
            
#         return {"success": True, "name": name, "docx_path": docx_path}
#     except Exception as e:
#         return {"success": False, "name": file_info["clean_name"], "error": str(e)}

# async def process_batch_resumes(job_id, saved_files, template_path, temp_dir, final_zip, zip_name, choice):
#     try:
#         job_status[job_id]["progress"] = f"Processing {len(saved_files)} files..."
#         loop = asyncio.get_event_loop()
#         tasks = [loop.run_in_executor(executor, process_single_resume_sync, f, template_path, temp_dir, job_id, choice) for f in saved_files]
#         results = await asyncio.gather(*tasks)
        
#         successful = []
#         failed = []
#         for res in results:
#             if res["success"]:
#                 successful.append(res)
#                 job_status[job_id]["completed_files"] += 1
#             else:
#                 failed.append(res)
#                 job_status[job_id]["failed_files"] += 1
#                 if "failed_details" not in job_status[job_id]: job_status[job_id]["failed_details"] = []
#                 job_status[job_id]["failed_details"].append(res)
        
#         if successful:
#             with zipfile.ZipFile(final_zip, 'w', zipfile.ZIP_DEFLATED) as z:
#                 for res in successful: z.write(res["docx_path"], arcname=os.path.basename(res["docx_path"]))
#             job_status[job_id]["status"] = "completed"
#             job_status[job_id]["progress"] = "Done"
#         else:
#             job_status[job_id]["status"] = "error"
#             job_status[job_id]["error"] = "All files failed"
#     except Exception as e:
#         job_status[job_id]["status"] = "error"
#         job_status[job_id]["error"] = str(e)

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)



from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Form, APIRouter
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import uuid
import shutil
from typing import Optional, Dict, Any, List
import glob
import zipfile
from datetime import datetime
import asyncio
import time 

# --- IMPORTS ---
try:
    import src.resume_parser_general as parser_gen
    import src.resume_parser_salesforce as parser_sf
    import src.docx_converter_general as docx_gen
    import src.docx_converter_salesforce as docx_sf
except ImportError:
    # Fallback if running as module
    from src import resume_parser_general as parser_gen
    from src import resume_parser_salesforce as parser_sf
    from src import docx_converter_general as docx_gen
    from src import docx_converter_salesforce as docx_sf

# --- APP SETUP ---
app = FastAPI(
    title="Resume Conversion API",
    description="Convert PDF/DOCX resumes to structured DOCX format (Single & Batch)",
    version="4.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
os.makedirs("output", exist_ok=True)
os.makedirs("frontend", exist_ok=True)
os.makedirs("templates", exist_ok=True)

app.mount("/output", StaticFiles(directory="output"), name="output")
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# State
job_status = {}

# Templates
TEMPLATE_MAP = {
    "classic": "resume_template_general.jinja2.html",
    "salesforce": "resume_template_salesforce.jinja2.html"
}

# --- MODELS ---
class ConversionResponse(BaseModel):
    job_id: str
    status: str
    message: str
    download_url: Optional[str] = None
    file_count: Optional[int] = None

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: str
    total_files: Optional[int] = None
    completed_files: Optional[int] = None
    failed_files: Optional[int] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# --- UTILS ---
def cleanup_old_files():
    """Deletes files older than 1 hour"""
    try:
        current_time = datetime.now()
        for temp_dir in glob.glob("temp_*"):
            if os.path.exists(temp_dir):
                if (current_time - datetime.fromtimestamp(os.path.getctime(temp_dir))).total_seconds() > 3600:
                    shutil.rmtree(temp_dir)
        for f in glob.glob("output/*"):
            if (current_time - datetime.fromtimestamp(os.path.getctime(f))).total_seconds() > 3600:
                os.remove(f)
    except Exception: pass

# --- ROUTES ---

@app.get("/")
async def serve_frontend():
    return FileResponse("frontend/index.html")

@app.post("/api/convert-resume", response_model=ConversionResponse)
async def convert_single_resume(
    background_tasks: BackgroundTasks,
    resume_file: UploadFile = File(...),
    template_choice: str = Form("classic"), 
    output_name: Optional[str] = Form(None)
):
    cleanup_old_files()
    
    # 1. Setup Job
    job_id = str(uuid.uuid4())
    temp_dir = f"temp_{job_id}"
    os.makedirs(temp_dir, exist_ok=True)
    
    # 2. Save File
    file_ext = os.path.splitext(resume_file.filename)[1].lower()
    resume_path = f"{temp_dir}/uploaded_resume{file_ext}"
    with open(resume_path, "wb") as buffer: shutil.copyfileobj(resume_file.file, buffer)
    
    # 3. Determine Output Name
    if output_name:
        clean = "".join(c for c in output_name if c.isalnum() or c in (' ', '-', '_')).rstrip().replace(' ', '_')
    else:
        original = os.path.splitext(resume_file.filename)[0]
        clean = "".join(c for c in original if c.isalnum() or c in (' ', '-', '_')).rstrip().replace(' ', '_')
    
    docx_filename = f"converted_resume_{clean}.docx"
    final_path = f"output/{docx_filename}"
    template_path = os.path.join("templates", TEMPLATE_MAP.get(template_choice, "resume_template_general.jinja2.html"))

    # 4. Initialize Status
    job_status[job_id] = {
        "status": "processing",
        "progress": "Starting...",
        "file_count": 1,
        "docx_filename": docx_filename
    }
    
    # 5. Background Task
    background_tasks.add_task(
        worker_single_process,
        job_id, resume_path, template_path, temp_dir, final_path, template_choice
    )
    
    return ConversionResponse(job_id=job_id, status="processing", message="Started", download_url=f"/output/{docx_filename}", file_count=1)

@app.post("/api/convert-resumes-batch", response_model=ConversionResponse)
async def convert_batch_resumes(
    background_tasks: BackgroundTasks,
    resume_files: List[UploadFile] = File(...),
    template_choice: str = Form("classic"),
    output_name: Optional[str] = Form(None)
):
    cleanup_old_files()
    if not resume_files: raise HTTPException(status_code=400, detail="No files")
    
    # 1. Setup Job
    job_id = str(uuid.uuid4())
    temp_dir = f"temp_batch_{job_id}"
    os.makedirs(temp_dir, exist_ok=True)
    
    # 2. Save All Files
    saved_files = []
    for idx, file in enumerate(resume_files):
        ext = os.path.splitext(file.filename)[1].lower()
        clean = "".join(c for c in os.path.splitext(file.filename)[0] if c.isalnum() or c in (' ', '-', '_')).rstrip().replace(' ', '_')
        path = f"{temp_dir}/resume_{idx}_{clean}{ext}"
        with open(path, "wb") as buffer: shutil.copyfileobj(file.file, buffer)
        saved_files.append({"path": path, "clean_name": clean, "index": idx})
            
    template_path = os.path.join("templates", TEMPLATE_MAP.get(template_choice, "resume_template_general.jinja2.html"))

    # 3. Output Zip Name
    if output_name:
        clean_zip = "".join(c for c in output_name if c.isalnum() or c in (' ', '-', '_')).rstrip().replace(' ', '_')
        zip_filename = f"{clean_zip}.zip"
    else:
        zip_filename = f"converted_batch_{job_id[:8]}.zip"
    
    final_zip_path = f"output/{zip_filename}"
    
    # 4. Initialize Status
    job_status[job_id] = {
        "status": "processing",
        "progress": "Starting batch...",
        "total_files": len(saved_files),
        "completed_files": 0,
        "failed_files": 0,
        "zip_filename": zip_filename
    }
    
    # 5. Background Task
    background_tasks.add_task(
        worker_batch_process,
        job_id, saved_files, template_path, temp_dir, final_zip_path, template_choice
    )
    
    return ConversionResponse(job_id=job_id, status="processing", message="Batch started", download_url=f"/output/{zip_filename}", file_count=len(saved_files))

@app.get("/api/job-status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    if job_id not in job_status: raise HTTPException(status_code=404, detail="Job not found")
    data = job_status[job_id]
    
    resp = JobStatusResponse(
        job_id=job_id, status=data["status"], progress=data["progress"],
        total_files=data.get("total_files"), completed_files=data.get("completed_files"), failed_files=data.get("failed_files")
    )
    
    if data["status"] == "completed":
        dl = data.get("zip_filename") or data.get("docx_filename")
        resp.result = {"download_url": f"/output/{dl}"}
        if data.get("failed_details"): resp.result["failed_details"] = data["failed_details"]
    elif data["status"] == "error":
        resp.error = data.get("error")
        
    return resp

@app.get("/output/{filename}")
async def download_file(filename: str):
    path = os.path.join("output", filename)
    if not os.path.exists(path): raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=path, filename=filename)

# --- WORKERS (THE BRAINS) ---

async def worker_single_process(job_id, resume_path, template_path, temp_dir, final_path, choice):
    """Handles Single File Conversion"""
    try:
        job_status[job_id]["progress"] = "Extracting Data..."
        temp_html = os.path.join(temp_dir, "temp.html")
        
        # 1. Parse
        if choice == "salesforce":
            success = parser_sf.extract_resume_data(resume_path, template_path, temp_html)
        else:
            success = parser_gen.extract_resume_data(resume_path, template_path, temp_html)
            
        if not success: raise Exception("AI Extraction Failed")
        
        job_status[job_id]["progress"] = "Generating DOCX..."
        
        # 2. Convert
        if choice == "salesforce":
            docx_sf.convert_salesforce_resume(temp_html, final_path)
        else:
            docx_gen.convert_resume_to_docx(temp_html, final_path)
            
        job_status[job_id]["status"] = "completed"
        job_status[job_id]["progress"] = "Done"
    except Exception as e:
        job_status[job_id]["status"] = "error"
        job_status[job_id]["error"] = str(e)

async def worker_batch_process(job_id, saved_files, template_path, temp_dir, final_zip, choice):
    """Handles Multiple Files Sequentially"""
    try:
        successful = []
        
        # === SEQUENTIAL LOOP (Prevents 429 Errors) ===
        for i, file_info in enumerate(saved_files):
            name = file_info["clean_name"]
            job_status[job_id]["progress"] = f"Processing {i+1}/{len(saved_files)}: {name}"
            
            # Rate Limit Delay
            if i > 0: 
                print("⏳ Cooling down API (3s)...")
                time.sleep(3) 

            # Paths
            temp_html = f"{temp_dir}/temp_{i}.html"
            docx_path = f"{temp_dir}/Converted_{name}.docx"
            
            try:
                # 1. Parse
                if choice == "salesforce":
                    ok = parser_sf.extract_resume_data(file_info["path"], template_path, temp_html)
                else:
                    ok = parser_gen.extract_resume_data(file_info["path"], template_path, temp_html)
                
                if ok:
                    # 2. Convert
                    if choice == "salesforce":
                        docx_sf.convert_salesforce_resume(temp_html, docx_path)
                    else:
                        docx_gen.convert_resume_to_docx(temp_html, docx_path)
                    
                    successful.append(docx_path)
                    job_status[job_id]["completed_files"] += 1
                else:
                    job_status[job_id]["failed_files"] += 1
                    _log_failure(job_id, name, "Extraction failed")

            except Exception as e:
                job_status[job_id]["failed_files"] += 1
                _log_failure(job_id, name, str(e))

        # === ZIPPING ===
        if successful:
            job_status[job_id]["progress"] = "Zipping files..."
            with zipfile.ZipFile(final_zip, 'w', zipfile.ZIP_DEFLATED) as z:
                for f in successful: 
                    z.write(f, arcname=os.path.basename(f))
            job_status[job_id]["status"] = "completed"
            job_status[job_id]["progress"] = "Done"
        else:
            job_status[job_id]["status"] = "error"
            job_status[job_id]["error"] = "All files failed."
            
    except Exception as e:
        job_status[job_id]["status"] = "error"
        job_status[job_id]["error"] = str(e)

def _log_failure(job_id, name, reason):
    if "failed_details" not in job_status[job_id]: 
        job_status[job_id]["failed_details"] = []
    job_status[job_id]["failed_details"].append({"name": name, "error": reason})

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=True)