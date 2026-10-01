from fastapi import FastAPI

from transcribe_stream import router as transcribe_router

app = FastAPI()
app.include_router(transcribe_router)
