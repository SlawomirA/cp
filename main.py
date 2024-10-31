import uvicorn
from fastapi import FastAPI
from src.pdf.router import router as pdf_router
from src.pdf.crud_router import router as crud_router

app = FastAPI()

app.include_router(pdf_router)
app.include_router(crud_router)


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
