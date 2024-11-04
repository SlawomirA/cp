import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.pdf.router import router as pdf_router
from src.pdf.crud_router import router as crud_router

app = FastAPI()

app.include_router(pdf_router)
app.include_router(crud_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Update this to your frontend origin
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (POST, GET, OPTIONS, etc.)
    allow_headers=["*"],  # Allows all headers
)

@app.get("/", tags=["Health check"])
async def health_check():
    return {
        "name": "Data scraping API",
        "type": "scraper-api",
        "description": "The software that scrapes quotes on request",
        "documentation": "/docs"
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
