import base64
import logging
from contextlib import asynccontextmanager
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from PIL import Image, ImageOps, UnidentifiedImageError
from ultralytics import YOLO

from .rag_service import RAGService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "yolo" / "gateway_best.pt"


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not MODEL_PATH.is_file():
        raise RuntimeError(f"YOLO model file not found: {MODEL_PATH}")
    app.state.model = YOLO(MODEL_PATH)
    app.state.rag = RAGService()
    yield


app = FastAPI(title="Fort Guide API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/chat")
def chat(request: ChatRequest):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question cannot be empty.")

    try:
        return app.state.rag.answer(question)
    except Exception:
        logger.exception("Historical RAG answer failed")
        raise HTTPException(
            status_code=502,
            detail="Could not answer from the historical sources. Please try again.",
        ) from None


@app.post("/api/detect")
async def detect_gateway(
    file: UploadFile = File(...),
    fort_name: str = Form(default="", max_length=120),
    location: str = Form(default="", max_length=120),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Upload an image file.")

    contents = await file.read(MAX_IMAGE_BYTES + 1)
    if len(contents) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image must be 10 MB or smaller.")
    if not contents:
        raise HTTPException(status_code=400, detail="The uploaded image is empty.")

    try:
        with Image.open(BytesIO(contents)) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid image.") from exc

    try:
        prediction = app.state.model.predict(image, conf=0.25, verbose=False)[0]
        annotated = Image.fromarray(prediction.plot()[:, :, ::-1])
        output = BytesIO()
        annotated.save(output, format="JPEG", quality=88)
    except Exception:
        logger.exception("Gateway detection failed")
        raise HTTPException(status_code=500, detail="Image analysis failed. Please try again.") from None

    detections = [
        {
            "class_name": "gateway",
            "confidence": float(box.conf),
            "bbox": {
                "x1": float(box.xyxy[0][0]),
                "y1": float(box.xyxy[0][1]),
                "x2": float(box.xyxy[0][2]),
                "y2": float(box.xyxy[0][3]),
            },
        }
        for box in prediction.boxes
    ]

    return {
        "annotated_image": "data:image/jpeg;base64," + base64.b64encode(output.getvalue()).decode("ascii"),
        "detections": detections,
        "fort_name": fort_name.strip(),
        "location": location.strip(),
    }
