import uvicorn

if __name__ == "__main__":
    uvicorn.run("backend.main:app", port=8000, reload=True)
