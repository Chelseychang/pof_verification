# POF Verification System

A full-stack demonstration of Proof of Face (POF) verification system with facial recognition, liveness detection, and identity document validation.

## Overview

This project provides a complete implementation of a face verification system that includes:

- **Backend API**: FastAPI-based verification service with InsightFace integration
- **Frontend H5**: Browser-based user interface with camera integration
- **Face Recognition**: Facial similarity scoring using deep learning models
- **Liveness Detection**: Anti-spoofing verification
- **Document OCR**: ID card and document text extraction
- **Quality Checks**: Image quality validation for verification accuracy

## Features

- Real-time face capture and verification
- Multi-scenario testing (approval, rejection, manual review)
- RESTful API with OpenAPI documentation
- CORS-enabled for cross-origin requests
- Confidence scoring and similarity matching
- Automated decision making with manual review fallback
- Attribute extraction (age, gender, ethnicity)

## Project Structure

```
pof_verification/
├── backend/          # FastAPI verification service
│   ├── main.py      # Core API implementation
│   ├── requirements.txt
│   └── run.sh       # Start script
├── frontend/        # H5 user interface
│   ├── index.html   # Main page
│   ├── main.js      # JavaScript logic
│   ├── style.css    # Styling
│   └── sdk/         # Browser SDK
├── docs/            # API documentation
│   └── API_NOTES.md
└── README.md
```

## Technology Stack

### Backend
- **Framework**: FastAPI
- **Face Recognition**: InsightFace
- **Computer Vision**: OpenCV
- **OCR**: Tesseract / PaddleOCR
- **Image Processing**: NumPy, PIL

### Frontend
- **HTML5**: Camera API integration
- **JavaScript**: ES6+ with async/await
- **CSS3**: Responsive design

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Webcam or camera device
- Modern web browser (Chrome, Firefox, Safari)

### Backend Setup

1. Create and activate virtual environment:
```bash
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r backend/requirements.txt
```

3. Start the API server:
```bash
cd backend
python3.11 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Or use the provided script:
```bash
cd backend
bash run.sh
```

4. Verify the server is running:
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### Frontend Setup

**Option 1: Direct file access**
- Simply open `frontend/index.html` in your browser

**Option 2: Local server (recommended)**
```bash
cd frontend
python -m http.server 5173
```
Then open: http://localhost:5173

### Configuration

The frontend is configured to connect to `http://localhost:8000` by default. To change the API endpoint, modify the API_BASE_URL in `frontend/main.js`.

## API Endpoints

### Core Verification

**POST /verify**
- Primary verification endpoint
- Accepts: `selfie_photo`, `id_photo`, optional `user_id`
- Returns: verification decision, confidence scores, similarity metrics

### Testing Scenarios

**POST /verify-scenario**
- Test different verification outcomes
- Query parameter: `scenario` (auto, approved, manual_review, quality_failed, liveness_failed, face_mismatch, attribute_mismatch)

### Health Check

**GET /health**
- Server status and uptime
- Returns: status and timestamp

## Usage Example

### Via Frontend
1. Open the H5 page in your browser
2. Allow camera permissions
3. Upload or capture your selfie
4. Upload your ID document photo
5. Click "Verify" and wait for results

### Via API
```bash
curl -X POST "http://localhost:8000/verify" \
  -F "selfie_photo=@selfie.jpg" \
  -F "id_photo=@id_card.jpg" \
  -F "user_id=user_12345"
```

### Test Scenarios
```bash
curl -X POST "http://localhost:8000/verify-scenario?scenario=approved" \
  -F "selfie_photo=@selfie.jpg" \
  -F "id_photo=@id_card.jpg"
```

## Response Format

```json
{
  "user_id": "user_12345",
  "decision": "approved",
  "confidence_score": 0.95,
  "similarity_score": 0.92,
  "liveness_score": 0.88,
  "quality_score": 0.90,
  "reason": "Verification successful",
  "user_message": "Your identity has been verified successfully.",
  "review_eta_minutes": null,
  "attributes": {
    "age": 28,
    "gender": "male",
    "ethnicity": "asian"
  },
  "processing_time_ms": 1234
}
```

## Decision Types

- **approved**: Verification passed all checks
- **rejected**: Verification failed critical checks
- **manual_review**: Uncertain results, requires human review

## Development

### Running Tests
```bash
# Backend tests
pytest backend/tests/

# Frontend tests
# Open frontend/index.html in browser and test manually
```

### Adding New Features
1. Backend: Extend `main.py` with new endpoints
2. Frontend: Update `main.js` for new UI logic
3. Documentation: Update API_NOTES.md

## Troubleshooting

### Camera Access Issues
- Ensure HTTPS or localhost is used (browser security requirement)
- Check browser permissions for camera access
- Try a different browser if issues persist

### Backend Errors
- Verify Python version is 3.11+
- Check all dependencies are installed: `pip list`
- Review server logs for detailed error messages

### CORS Issues
- Backend is configured to allow all origins (`allow_origins=["*"]`)
- For production, restrict to specific domains

## Important Notes

- This is a **demonstration/mock system** for testing and development
- Not intended for production use without additional security measures
- Verification scores are simulated for SDK/H5 integration testing
- Real production systems require:
  - Enhanced security (authentication, rate limiting)
  - Encrypted data transmission
  - Compliance with data protection regulations
  - Production-grade face recognition models
  - Robust anti-spoofing mechanisms

## Security Considerations

For production deployment:
- [ ] Implement API authentication (OAuth2, JWT)
- [ ] Add rate limiting and DDoS protection
- [ ] Use HTTPS for all communications
- [ ] Sanitize and validate all inputs
- [ ] Implement proper error handling (don't expose internals)
- [ ] Add logging and monitoring
- [ ] Comply with GDPR/CCPA data regulations
- [ ] Secure file storage and deletion policies

## License

This project is provided as-is for demonstration purposes.

## Contributing

This is a demo project. For production use cases, please implement proper security measures and comply with relevant regulations.

## Support

For issues or questions:
- Check the `/docs` folder for API documentation
- Review FastAPI docs at http://localhost:8000/docs
- Open an issue on the GitHub repository

---

**Disclaimer**: This is a demonstration system. Do not use in production without implementing proper security measures, compliance checks, and robust verification algorithms.
