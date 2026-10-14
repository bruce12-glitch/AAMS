"""Disposable browser-test API. Only the neural inference boundary is stubbed."""
import json
import os
import secrets
from pathlib import Path

root = Path(os.environ['AAMS_E2E_DIR'])
credentials = json.loads((root / 'credentials.json').read_text())
os.environ.update(AAMS_ENV='production', ADMIN_EMAIL=credentials['email'],
                  API_ADMIN_PASSWORD=credentials['password'],
                  AAMS_ACCESS_PASSWORD=credentials['member_password'],
                  SESSION_SECRET_KEY=secrets.token_urlsafe(48),
                  QR_SECRET_KEY=secrets.token_urlsafe(48),
                  DATABASE_PATH=str(root / 'showcase.db'))
import numpy as np
import app.vision as vision
embedding = np.linspace(-1, 1, 512)
embedding /= np.linalg.norm(embedding)
vision.analyze_frame = lambda frame: {
    'face_count': 1, 'quality_passed': True, 'quality_reasons': [],
    'embedding': embedding.copy(),
}
import uvicorn
uvicorn.run('app.main:app', host='127.0.0.1', port=8000, log_level='warning')
