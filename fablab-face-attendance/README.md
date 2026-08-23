# FacePass FabLab

**Smart Anti-Proxy Facial Access and Attendance System for SRMIST Fab Lab**

## Overview

FacePass FabLab is a complete facial recognition access control system designed for the SRMIST Fabrication Laboratory. It prevents proxy attendance, tracks occupancy, and sends real-time alerts via Telegram.

## Features

- **Facial Recognition**: SCRFD detection + ArcFace embeddings via InsightFace
- **Anti-Spoofing**: Blink detection using Eye Aspect Ratio (EAR)
- **Token + Face Mode**: QR code + face verification (§10)
- **Face-Only Mode**: Direct face recognition (§19)
- **Decision Matrix**: 9-row access policy engine (§11.2)
- **Occupancy Tracking**: Real-time indoor tracking with timeout logic (§14)
- **Telegram Alerts**: Real-time notifications for security events (§15)
- **Daily Reports**: Automated 8 PM summary reports
- **Signed QR Codes**: HMAC-signed tokens for security (§27.3)

## Project Structure

```
fablab-face-attendance/
├── app/                    # Core application modules
│   ├── main.py            # FastAPI entry point
│   ├── config.py          # Configuration loader
│   ├── face_engine.py     # InsightFace wrapper
│   ├── liveness.py        # Blink detection
│   ├── identity.py        # 1:1 and 1:N matching
│   ├── access_policy.py   # Decision matrix
│   ├── occupancy.py       # Occupancy tracking
│   ├── alerts.py          # Telegram integration
│   ├── reports.py         # Report generation
│   ├── scheduler.py       # APScheduler jobs
│   ├── qr_manager.py      # Signed QR codes
│   └── utils.py           # Helper functions
├── api/                    # FastAPI routes
│   ├── routes_entry.py    # Entry processing
│   ├── routes_users.py    # User CRUD
│   ├── routes_alerts.py   # Alert management
│   ├── routes_occupants.py# Occupancy API
│   ├── routes_reports.py  # Reports API
│   ├── routes_dashboard.py# Dashboard stats
│   └── routes_admin.py    # Admin actions
├── enrollment/            # Enrollment scripts
├── scripts/               # Utility scripts
├── tests/                 # Test suite
├── database/              # SQLite database
├── images/                # Image storage
└── frontend/              # HTML dashboard
```

## Installation

### Prerequisites

- Python 3.8+
- Webcam (for face capture)
- Telegram Bot Token (optional, for alerts)

### Setup

1. **Clone and navigate to project:**
   ```bash
   cd fablab-face-attendance
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create environment file:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Initialize database:**
   ```bash
   python -m scripts.create_db
   ```

5. **Seed demo data (optional):**
   ```bash
   python -m scripts.seed_demo_data
   ```

6. **Run the system:**
   ```bash
   python run.py
   ```

The API will start at `http://localhost:8000` with interactive docs at `/docs`.

## Configuration

Edit `config.yaml` to customize:

- **Face Recognition**: Match threshold, min face size, pose limits
- **Camera**: Source, FPS, resolution
- **Liveness**: Timeout seconds, EAR thresholds
- **Occupancy**: Timeout minutes
- **Alerts**: Telegram settings, daily report time
- **Security**: QR secret key

## API Endpoints

### Entry Processing
- `POST /api/entry/process` - Token + Face entry (Mode B)
- `POST /api/entry/face-only` - Face-only entry (Mode A)
- `POST /api/entry/simulate` - Demo simulation

### Users
- `GET /api/users` - List all users
- `POST /api/users` - Add new user
- `PUT /api/users/{user_id}` - Update user
- `DELETE /api/users/{user_id}` - Delete user
- `GET /api/users/{user_id}/qr` - Generate QR pass

### Dashboard
- `GET /api/dashboard/stats` - KPI statistics
- `GET /api/dashboard/activity` - Recent activity
- `GET /api/dashboard/live` - Live camera status
- `GET /api/dashboard/research` - Threshold calibration data

### Reports
- `GET /api/reports/daily` - Daily report
- `GET /api/reports/weekly` - Weekly report
- `GET /api/reports/proxy` - Proxy attempts
- `GET /api/reports/unpaid` - Unpaid attempts
- `GET /api/reports/occupancy` - Occupancy stats

## Testing

Run all tests:
```bash
python -m pytest tests/ -v
```

Individual test modules:
- `test_face_matching.py` - Cosine similarity tests
- `test_proxy_detection.py` - Proxy detection logic
- `test_access_policy.py` - Decision matrix (all 9 rows)
- `test_occupancy.py` - Occupancy tracking
- `test_alerts.py` - Alert formatting

## Enrollment

To enroll a new user:

```bash
python -m enrollment.enroll_user
```

This will:
1. Prompt for user details
2. Capture 5 face poses with quality checks
3. Extract and store 3 embeddings
4. Generate QR token

## Frontend Integration

The existing `frontend/index.html` should be wired to the API:

```javascript
const API = {
    base: 'http://localhost:8000/api',
    async get(path) {
        const r = await fetch(this.base + path);
        return r.json();
    },
    async post(path, body) {
        const r = await fetch(this.base + path, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(body)
        });
        return r.json();
    }
};

// Example: Get dashboard stats
const stats = await API.get('/dashboard/stats');

// Example: Process entry
const result = await API.post('/entry/simulate', {scenario: 'authorized'});
```

## Security Notes

1. **Change default secrets** in `.env` before production
2. **Enable HTTPS** for production deployment
3. **Restrict CORS origins** in `app/main.py`
4. **Regular database backups** using `scripts/backup_db.py`

## Troubleshooting

### InsightFace model download
First run may take time to download models (~500MB). Models are cached in `models/insightface/`.

### Camera not found
Ensure webcam is connected and set correct source in `config.yaml`:
```yaml
camera:
  source: 0  # Try 1, 2, etc. if 0 doesn't work
```

### Telegram alerts not sending
Verify bot token and chat ID in `.env`:
```
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

## License

SRMIST FabLab - Internal Use Only

## Contact

For support, contact the FabLab administration team.
