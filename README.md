# LilacBridge – Hospital Management System
## bridging patients, doctors, and data!

LilacBridge is a Flask-based hospital management system (HMS) web application that centralizes hospital operations for admin, doctors, and patients by managing doctors, availability, and appointments in one place.​

---

## 🏥 Project Overview

LilacBridge is a comprehensive hospital management platform that enables:
- **Patients** to register, book appointments with doctors, view appointment history, and reschedule visits
- **Doctors** to manage their availability, view upcoming appointments, complete appointments with diagnosis/prescription, and track their patient records
- **Admins** to manage the entire system, doctors and patients, view all appointments, and look at insights

---

## 🛠 Tech Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | Flask |
| **Frontend** | HTML5, CSS3, Bootstrap 5 |
| **Database** | SQLite |
| **Libraries** | Flask-WTF for form handling, Jinja2 for templating |

---

## 🚀 Setup & Installation

### 1. Prerequisites
- Python 3.7+
- pip (Python package manager)

### 2. Clone the Project
```bash
# clone the repository
git clone https://github.com/24f3000060/hospital-management-system-v1.git

# move into the project folder
cd hospital-management-system-v1
```

### 3. Create a Virtual Environment
```bash
python -m venv venv

# Activate on Windows
venv\Scripts\activate

# Activate on macOS/Linux
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Run the App
```bash
python app.py
```

The app will start on `http://127.0.0.1:5000/`. Open this in your browser.

---

## 🧪 Testing & Validation

### Test Accounts (after initialization)
```
Default Admin:
  Username: admin
  Email: admin@hospital.com
  Password: admin123

Sample Doctor:
  Username: dr_raj
  Email: raj@lilacbridge.com
  Password: Raj@123

Sample Patient:
  Username: arun12
  Email: arun12@pat.com
  Password: Arun@123
```

---

**Happy healthcare management with LilacBridge! 🏥💜✨**