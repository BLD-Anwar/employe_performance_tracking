# Employee Performance Tracking System

## Overview
The Employee Performance Tracking System is a web-based application designed to monitor, manage, and evaluate employee work across multiple departments and job roles.

The system provides a centralized platform for tracking:
- Assigned work
- Completed tasks
- Pending tasks
- Employee performance in real time

This project aims to improve transparency, productivity monitoring, workload management, and performance evaluation for organizations.

---

## Problem Statement
Organizations often struggle to track employee work consistently across different departments such as:
- HR
- Development
- Sales
- Operations
- Support

Existing manual methods create problems like:
- Poor visibility into assigned vs completed work
- Delayed performance evaluation
- Inaccurate reporting
- Difficulty monitoring workload distribution
- Lack of centralized dashboards

The proposed system solves these issues by providing a unified dashboard and detailed work tracking features for managers, HR teams, and employees.

---

## Main Objectives
- Track assigned, completed, pending, and overdue work
- Provide centralized dashboards for HR and managers
- Generate detailed work summaries and reports
- Improve transparency and accountability
- Support multiple departments and job roles
- Enable performance analysis using measurable metrics

---

## Key Features
- Employee and Manager dashboards
- Task assignment and tracking
- Assigned vs Completed vs Remaining analytics
- Work progress monitoring
- Department-wise performance tracking
- Detailed task/work summaries
- Role-based system access
- Performance reporting and analytics
- Real-time or near real-time updates

---

## Planned Tech Stack

### Frontend
- HTML
- CSS
- JavaScript
- Streamlit (Optional)

### Backend
- Python
- Flask / FastAPI

### Database
- MySQL / PostgreSQL

### Visualization
- Plotly
- Chart.js

---

## Future Enhancements
- AI/ML-based performance prediction
- Automated scoring system
- Notification and alert system
- Attendance integration
- Mobile application support
- Advanced analytics and reporting

---

## Project Timeline
**Estimated Development Timeline:** 5 Weeks

---

## Developed By
**Anwarali Mulla**  
Vijaybhoomi University

---

## Setup & How to Run

Follow these instructions to set up the project locally and run it.

### Prerequisites
1. **Python**: Version 3.10 or higher.
2. **Database**: Microsoft SQL Server (e.g., SQL Server Express or LocalDB).
3. **ODBC Driver**: Microsoft ODBC Driver for SQL Server (required for database connectivity via `pyodbc`).

### 1. Installation
1. Create and activate a Python virtual environment:
   ```bash
   # Create environment
   python -m venv .venv

   # Activate on Windows
   .venv\Scripts\activate

   # Activate on macOS/Linux
   source .venv/bin/activate
   ```
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### 2. Environment Setup
1. Create a `.env` file in the project root directory.
2. Configure the database server and token credentials (adjust server and database names as per your SQL Server configuration):
   ```ini
   PHASE1_DB_SERVER=YOUR_SQL_SERVER_NAME_OR_IP
   PHASE1_DB_NAME=FarmerManagement
   PHASE1_DB_TRUSTED=yes

   DB_SERVER=YOUR_SQL_SERVER_NAME_OR_IP
   DB_NAME=FarmerManagement

   JWT_SECRET_KEY=generate_a_secure_random_key_here
   JWT_ALGORITHM=HS256
   JWT_EXPIRE_MINUTES=60
   ```

### 3. Running the Application
Run the FastAPI application using Uvicorn:
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Once the server is running, open your web browser and navigate to:
- **Application Portal**: `http://127.0.0.1:8000/` (Redirects automatically to login page)
- **Direct Login**: `http://127.0.0.1:8000/login.html`
- **Portals**:
  - Employee Portal: `/employee/dashboard.html`
  - Manager Portal: `/manager/manager_dashboard.html`



