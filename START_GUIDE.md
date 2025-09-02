# 🏥 Healthcare Care Gap Automation - Startup Guide

Complete guide to start your healthcare automation system with Angular frontend, FastAPI backend, and AutoGen agents.

## 🚀 Quick Start (Recommended)

### Option 1: Start Everything at Once
```bash
cd /Users/shivanshusaxena/Documents/care-gap/healthcare-care-gap-automation
./start-all.sh
```

This will start both backend and frontend services automatically.

### Option 2: Start Services Individually

#### Start Backend Only
```bash
cd /Users/shivanshusaxena/Documents/care-gap/healthcare-care-gap-automation
./start-backend.sh
```

#### Start Frontend Only
```bash
cd /Users/shivanshusaxena/Documents/care-gap/healthcare-care-gap-automation
./start-frontend.sh
```

## 📋 Prerequisites

### Required Software
- **Python 3.8+**: For FastAPI backend
- **Node.js 16+**: For Angular frontend
- **PostgreSQL**: Database server
- **Git**: Version control

### Install Prerequisites on macOS
```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install required software
brew install python@3.11 node postgresql

# Install Angular CLI globally
npm install -g @angular/cli
```

## 🔧 Manual Setup Instructions

### 1. Backend Setup (FastAPI + AutoGen)

```bash
# Navigate to project directory
cd /Users/shivanshusaxena/Documents/care-gap/healthcare-care-gap-automation/backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment (macOS/Linux)
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Set environment variables (optional)
export DEBUG=true
export LOG_LEVEL=INFO

# Start FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Backend will be available at:**
- Main API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### 2. Frontend Setup (Angular)

```bash
# Open new terminal and navigate to frontend
cd /Users/shivanshusaxena/Documents/care-gap/healthcare-care-gap-automation/frontend

# Install Node.js dependencies
npm install

# Start Angular development server
ng serve --host 0.0.0.0 --port 4200
```

**Frontend will be available at:**
- Main Application: http://localhost:4200
- Accessible from any browser

### 3. Database Setup (PostgreSQL)

```bash
# Start PostgreSQL service
brew services start postgresql

# Connect to PostgreSQL
psql postgres

# Create database and user
CREATE DATABASE healthcare_care_gap;
CREATE USER postgres WITH PASSWORD 'user';
GRANT ALL PRIVILEGES ON DATABASE healthcare_care_gap TO postgres;
```

## 🌐 Access Points

Once everything is running:

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend Dashboard** | http://localhost:4200 | Main healthcare management interface |
| **Backend API** | http://localhost:8000 | FastAPI REST API |
| **API Documentation** | http://localhost:8000/docs | Interactive API documentation |
| **System Health** | http://localhost:8000/health | Backend health check |
| **Agent Metrics** | http://localhost:8000/api/v1/agents/health | AutoGen agent status |

## 🔍 Troubleshooting CORS Issues

### If you see "Error 0: Unknown error" or CORS errors:

1. **Check Backend is Running**
   ```bash
   curl http://localhost:8000/health
   ```

2. **Verify CORS Configuration**
   - Backend allows all origins (`*`) for development
   - All HTTP methods are permitted
   - All headers are allowed

3. **Clear Browser Cache**
   ```bash
   # Open browser developer tools and:
   # 1. Right-click refresh button
   # 2. Select "Empty Cache and Hard Reload"
   ```

4. **Check Network Tab**
   - Open browser DevTools → Network tab
   - Look for failed requests
   - Check if preflight OPTIONS requests succeed

## 🐛 Common Issues & Solutions

### Backend Issues

**Issue: `ModuleNotFoundError: No module named 'app'`**
```bash
# Make sure you're in the backend directory and venv is activated
cd backend
source venv/bin/activate
```

**Issue: Database connection errors**
```bash
# Check PostgreSQL is running
brew services status postgresql

# Start if not running
brew services start postgresql
```

### Frontend Issues

**Issue: `ng: command not found`**
```bash
npm install -g @angular/cli
```

**Issue: `Cannot find module` errors**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### CORS Issues

**Issue: CORS errors in browser console**
1. Ensure backend is running on port 8000
2. Clear browser cache completely
3. Try incognito/private browsing mode
4. Check browser console for specific error messages

## 📱 Testing the Application

### 1. Verify Backend is Working
```bash
# Test health endpoint
curl http://localhost:8000/health

# Test patient statistics
curl http://localhost:8000/api/v1/patients/statistics/overview

# Test agent health
curl http://localhost:8000/api/v1/agents/health
```

### 2. Test Frontend Features
1. Open http://localhost:4200
2. Check dashboard loads with metrics
3. Navigate to Patient Management
4. Test "Start Care Gap Workflow" button
5. Verify no CORS errors in browser console

### 3. Test Integration
- Dashboard should show real-time agent status
- Patient list should display patient cards
- Workflow actions should work without errors
- System health indicators should be green

## 🔄 Development Workflow

### Making Changes

**Backend Changes:**
- FastAPI auto-reloads on file changes
- Check logs in terminal for errors
- API docs update automatically at `/docs`

**Frontend Changes:**
- Angular hot-reloads automatically
- Browser refreshes with changes
- Check browser console for errors

### Stopping Services

```bash
# If using start-all.sh
Ctrl+C  # Stops all services

# If running individually
Ctrl+C in each terminal window
```

## 🏗️ Production Deployment

For production deployment:

1. **Update CORS settings** in `backend/app/config/settings.py`
2. **Set production environment variables**
3. **Use production database**
4. **Build frontend for production**: `ng build --prod`
5. **Use production WSGI server**: `gunicorn app.main:app`

## 📞 Support

If you encounter issues:

1. Check the terminal logs for error messages
2. Look at browser developer console
3. Verify all services are running on correct ports
4. Ensure database is accessible
5. Check network connectivity between services

---

## 🎉 Success Indicators

You know everything is working when:
- ✅ Backend responds at http://localhost:8000/health
- ✅ Frontend loads at http://localhost:4200
- ✅ Dashboard shows agent status and metrics
- ✅ No CORS errors in browser console
- ✅ "Start Care Gap Workflow" button works without errors
- ✅ Real-time updates are visible in the interface