# susadmin2
Sustainability Admin Application

A Flask-based sustainability administration platform with multi-agent AI chatbot, project management, billing tracking, and staffing tools.

## Features
- Role-based access control (Admin, Director, Manager)
- Multi-agent AI chatbot for data analysis
- Project and billing management
- Staffing entry tracking with Gantt charts
- Vercel Blob storage support for production deployment

## Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure environment (`.env`):
   ```bash
   JSON_DB_BACKEND=local
   OPENAI_API_KEY=your_openai_key
   ```

3. Run the application:
   ```bash
   python app.py
   ```

4. Access at: `http://localhost:5000`

## Vercel Deployment

### 1. Prepare Environment Variables
Set these in your Vercel project settings:

```bash
JSON_DB_BACKEND=vercel_blob
BLOB_READ_WRITE_TOKEN=your_vercel_blob_token
VERCEL_BLOB_ACCESS=private
VERCEL_BLOB_BASE_URL=https://your-blob-url.vercel-storage.com
VERCEL_BLOB_PREFIX=
VERCEL_BLOB_TIMEOUT_SECONDS=10
OPENAI_API_KEY=your_openai_key
```

### 2. Upload Data to Blob Storage
Before deploying, sync your local JSON data files to Vercel Blob:

```bash
# Make sure .env has BLOB_READ_WRITE_TOKEN set
python sync_data_to_blob.py
```

This uploads all files from `data/*.json` to your Vercel Blob store under the `data/` folder.

### 3. Deploy to Vercel
```bash
# Install Vercel CLI if you haven't
npm i -g vercel

# Deploy
vercel
```

## Data Storage

The application supports two storage backends:

- **Local** (development): JSON files in `data/` directory
- **Vercel Blob** (production): Private blob storage in Vercel

The backend is automatically selected based on the `JSON_DB_BACKEND` environment variable.

## File Structure
- `app.py` - Main Flask application
- `utils/json_db.py` - Dual storage backend (local/blob)
- `data/` - Local JSON data files (gitignored)
- `templates/` - Jinja2 HTML templates
- `static/` - CSS and JavaScript assets

