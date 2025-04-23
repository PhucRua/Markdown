# main.py
import os
import tempfile
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from pydantic import BaseModel
from typing import Optional

try:
    from markitdown import MarkItDown
    MARKITDOWN_AVAILABLE = True
except ImportError:
    MARKITDOWN_AVAILABLE = False
    print("Warning: MarkItDown is not available. Using fallback mode.")
    import fitz  # PyMuPDF as a fallback

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

class ConversionResponse(BaseModel):
    markdown: str
    filename: str

@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/convert/")
async def convert_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            # Write the uploaded file to the temporary file
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        # Convert PDF to markdown
        if MARKITDOWN_AVAILABLE:
            # Use MarkItDown for conversion
            md = MarkItDown(enable_plugins=False)
            result = md.convert(temp_path)
            markdown_text = result.text_content
        else:
            # Fallback to PyMuPDF
            markdown_text = convert_pdf_with_pymupdf(temp_path)
        
        # Remove temporary file
        os.unlink(temp_path)
        
        return ConversionResponse(
            markdown=markdown_text,
            filename=file.filename.replace(".pdf", ".md")
        )
        
    except Exception as e:
        # If temp file still exists, remove it
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

def convert_pdf_with_pymupdf(pdf_path):
    """Fallback conversion using PyMuPDF"""
    try:
        doc = fitz.open(pdf_path)
        markdown_content = []
        
        for page in doc:
            # Extract text
            text = page.get_text()
            # Add page delimiter
            markdown_content.append(f"## Page {page.number + 1}\n\n{text}")
        
        doc.close()
        return "\n\n".join(markdown_content)
        
    except Exception as e:
        raise Exception(f"Failed to convert PDF: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
