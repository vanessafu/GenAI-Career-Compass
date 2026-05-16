from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware 
from fastapi.responses import RedirectResponse
import logging
from backend.cv_parser import extract_text_from_pdf_bytes, parse_cv_to_pydantic
from backend.cv_schema import CVData

app = FastAPI(title="Career Compass API")
logger = logging.getLogger("CareerCompass.API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # Allows requests from the local React server
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods (GET, POST, etc.)
    allow_headers=["*"], # Allows all headers
)

@app.get("/", include_in_schema=False)
async def root():
    """Redirect the base URL directly to the API documentation."""
    return RedirectResponse(url="/docs")

@app.post("/api/v1/parse-cv", response_model=CVData)
async def upload_and_parse_cv(file: UploadFile = File(...)):
    """Endpoint for uploading and parsing a PDF file."""
    
    # 1. Validate file format
    if not file.filename.endswith(".pdf") and file.content_type != "application/pdf":
        logger.warning(f"Falsches Dateiformat abgelehnt: {file.filename}")
        raise HTTPException(status_code=400, detail="Es sind nur PDF-Dateien erlaubt.")
    
    # 2. Read file and extract text
    try:
        file_bytes = await file.read()
        raw_text = extract_text_from_pdf_bytes(file_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    if not raw_text:
        raise HTTPException(status_code=400, detail="Das PDF enthält keinen lesbaren Text.")

    # 3. LLM parsing
    try:
        parsed_data = await parse_cv_to_pydantic(raw_text)
        return parsed_data
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)