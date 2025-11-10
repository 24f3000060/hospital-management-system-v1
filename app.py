from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, Admin, Doctor, Patient, Appointment, Treatment, Department, DoctorAvailability
from datetime import datetime, timedelta, date, time as dtime
from sqlalchemy import or_

app = Flask(__name__)
app.config['SECRET_KEY'] = '24f3000060'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_ENABLED'] = False

db.init_app(app)

#Initialization
def init_db():
    with app.app_context():
        db.create_all()
        
        admin = Admin.query.filter_by(username='admin').first()
        if not admin:
            admin = Admin(username='admin', email='admin@hospital.com')
            admin.set_password('admin123')
            db.session.add(admin)
        
        departments_data = [
            {'name': 'Cardiology', 'description': 'Heart and cardiovascular system'},
            {'name': 'Oncology', 'description': 'Cancer treatment and care'},
            {'name': 'Neurology', 'description': 'Brain and nervous system'},
            {'name': 'Orthopedics', 'description': 'Bones, joints, and muscles'},
            {'name': 'Pediatrics', 'description': 'Child healthcare'},
            {'name': 'Gynecology', 'description': 'Women health and reproductive system'},
            {'name': 'Dermatology', 'description': 'Skin, hair, and nails'},
            {'name': 'ENT', 'description': 'Ear, Nose, and Throat'},
        ]
        for dd in departments_data:
            if not Department.query.filter_by(name=dd['name']).first():
                db.session.add(Department(**dd))
        db.session.commit()

#Helpers
def parse_hhmm(s: str) -> dtime:
    h, m = s.split(':')
    return dtime(hour=int(h), minute=int(m))

def time_range_slots(start: str, end: str, step_minutes: int = 30):
    #HH:MM every 30 minutes
    st = parse_hhmm(start)
    en = parse_hhmm(end)
    cur = st
    while (cur.hour, cur.minute) < (en.hour, en.minute):
        yield f"{cur.hour:02d}:{cur.minute:02d}"
        minute = (cur.minute + step_minutes)
        hour = cur.hour + minute // 60
        minute = minute % 60
        cur = dtime(hour=hour, minute=minute)

def slots_for_doctor_date(doctor_id: int, the_date: date):
    #All bookable HH:MM for doctor on a date 
    windows = DoctorAvailability.query.filter_by(doctor_id=doctor_id, date=the_date).all()
    allowed = set()
    for w in windows:
        for s in time_range_slots(w.start_time, w.end_time):
            allowed.add(s)
    # Remove already booked slots
    booked = Appointment.query.filter_by(doctor_id=doctor_id, date=the_date, status='Booked').all()
    booked_times = {a.time for a in booked}
    available = [t for t in allowed if t not in booked_times]
    # If booking for today, hide slots in the past
    if the_date == date.today():
        now_time = datetime.now().time()
        available = [t for t in available if parse_hhmm(t) >= now_time]
    return sorted(available)

def week_slots_for_doctor(doctor_id: int, start_day: date):
    #Seven days of slots
    data = []
    for i in range(7):
        d = start_day + timedelta(days=i)
        data.append({'date': d, 'slots': slots_for_doctor_date(doctor_id, d)})
    return data

#Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        admin = Admin.query.filter(or_(Admin.username == username, Admin.email == username)).first()
        if admin and admin.check_password(password):
            session['user_id'] = admin.id
            session['user_type'] = 'admin'
            session['username'] = admin.username
            return redirect(url_for('admin_dashboard'))
        
        doctor = Doctor.query.filter(or_(Doctor.username == username, Doctor.email == username)).first()
        if doctor and doctor.check_password(password):
            if not doctor.is_active:
                flash('Your account has been deactivated. Contact admin.', 'danger')
                return redirect(url_for('login'))
            session['user_id'] = doctor.id
            session['user_type'] = 'doctor'
            session['username'] = doctor.username
            return redirect(url_for('doctor_dashboard'))
        
        patient = Patient.query.filter(or_(Patient.username == username, Patient.email == username)).first()
        if patient and patient.check_password(password):
            if not patient.is_active:
                flash('Your account has been deactivated. Contact admin.', 'danger')
                return redirect(url_for('login'))
            session['user_id'] = patient.id
            session['user_type'] = 'patient'
            session['username'] = patient.username
            return redirect(url_for('patient_dashboard'))
        
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        if Patient.query.filter_by(username=username).first() or Doctor.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('register'))
        if Patient.query.filter_by(email=email).first():
            flash('Email already exists', 'danger')
            return redirect(url_for('register'))
        patient = Patient(
            username=username,
            email=email,
            name=request.form.get('name'),
            age=request.form.get('age'),
            gender=request.form.get('gender'),
            contact=request.form.get('contact'),
            address=request.form.get('address')
        )
        patient.set_password(request.form.get('password'))
        db.session.add(patient)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

#Admin routes
@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('user_type') != 'admin':
        return redirect(url_for('login'))
    
    total_doctors = Doctor.query.filter_by(is_active=True).count()
    total_patients = Patient.query.filter_by(is_active=True).count()
    total_appointments = Appointment.query.count()
    upcoming_appointments = Appointment.query.filter(
        Appointment.date >= date.today(),
        Appointment.status == 'Booked'
    ).order_by(Appointment.date, Appointment.time).all()
    
    registered_patients = Patient.query.order_by(Patient.created_at.desc()).all()
    registered_doctors = Doctor.query.order_by(Doctor.created_at.desc()).all()
    
    search_query = request.args.get('search', '')
    search_results = {'patients': [], 'doctors': []}
    if search_query:
        search_results['patients'] = Patient.query.filter(
            or_(Patient.name.ilike(f'%{search_query}%'), 
                Patient.username.ilike(f'%{search_query}%'), 
                Patient.contact.ilike(f'%{search_query}%'))).all()
        search_results['doctors'] = Doctor.query.join(Department).filter(
            or_(Doctor.name.ilike(f'%{search_query}%'), 
                Doctor.username.ilike(f'%{search_query}%'), 
                Department.name.ilike(f'%{search_query}%'))).all()
    
    return render_template('admin_dashboard.html',
                           total_doctors=total_doctors,
                           total_patients=total_patients,
                           total_appointments=total_appointments,
                           upcoming_appointments=upcoming_appointments,
                           registered_patients=registered_patients,
                           registered_doctors=registered_doctors,
                           search_query=search_query,
                           search_results=search_results)

@app.route('/admin/add_doctor', methods=['GET', 'POST'])
def add_doctor():
    if session.get('user_type') != 'admin':
        return redirect(url_for('login'))
    departments = Department.query.all()
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        if (
            Doctor.query.filter_by(username=username).first()
            or Patient.query.filter_by(username=username).first()
        ):
            flash('Username already exists', 'danger')
            return redirect(url_for('add_doctor'))
        if Doctor.query.filter_by(email=email).first():
            flash('Email already exists', 'danger')
            return redirect(url_for('add_doctor'))
        doctor = Doctor(
            username=username,
            email=email,
            name=request.form.get('name'),
            department_id=request.form.get('department_id'),
            specialization=request.form.get('specialization'),
            experience=request.form.get('experience'),
            contact=request.form.get('contact')
        )
        doctor.set_password(request.form.get('password'))
        db.session.add(doctor)
        db.session.commit()
        flash('Doctor added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('add_doctor.html', departments=departments)

@app.route('/admin/edit_doctor/<int:doctor_id>', methods=['GET', 'POST'])
def edit_doctor(doctor_id):
    if session.get('user_type') != 'admin':
        return redirect(url_for('login'))
    doctor = Doctor.query.get_or_404(doctor_id)
    departments = Department.query.all()
    if request.method == 'POST':
        doctor.name = request.form.get('name')
        doctor.department_id = request.form.get('department_id')
        doctor.specialization = request.form.get('specialization')
        doctor.experience = request.form.get('experience')
        doctor.contact = request.form.get('contact')
        db.session.commit()
        flash('Doctor updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('edit_doctor.html', doctor=doctor, departments=departments)

@app.route('/admin/delete_doctor/<int:doctor_id>')
def delete_doctor(doctor_id):
    if session.get('user_type') != 'admin':
        return redirect(url_for('login'))
    doctor = Doctor.query.get_or_404(doctor_id)
    doctor.is_active = False  #blacklisting
    db.session.commit()
    flash('Doctor deactivated (blacklisted).', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/activate_doctor/<int:doctor_id>')
def activate_doctor(doctor_id):
    if session.get('user_type') != 'admin':
        return redirect(url_for('login'))
    doctor = Doctor.query.get_or_404(doctor_id)
    doctor.is_active = True
    db.session.commit()
    flash('Doctor activated successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/edit_patient/<int:patient_id>', methods=['GET', 'POST'])
def edit_patient(patient_id):
    if session.get('user_type') != 'admin':
        return redirect(url_for('login'))
    patient = Patient.query.get_or_404(patient_id)
    if request.method == 'POST':
        patient.name = request.form.get('name')
        patient.age = request.form.get('age')
        patient.gender = request.form.get('gender')
        patient.contact = request.form.get('contact')
        patient.address = request.form.get('address')
        db.session.commit()
        flash('Patient updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('edit_patient.html', patient=patient)

@app.route('/admin/delete_patient/<int:patient_id>')
def delete_patient(patient_id):
    if session.get('user_type') != 'admin':
        return redirect(url_for('login'))
    patient = Patient.query.get_or_404(patient_id)
    patient.is_active = False
    db.session.commit()
    flash('Patient deactivated (blacklisted).', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/activate_patient/<int:patient_id>')
def activate_patient(patient_id):
    if session.get('user_type') != 'admin':
        return redirect(url_for('login')) 
    patient = Patient.query.get_or_404(patient_id)
    patient.is_active = True
    db.session.commit()
    flash('Patient activated successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/appointments')
def admin_appointments():
    if session.get('user_type') != 'admin':
        return redirect(url_for('login'))
    appointments = (
        Appointment.query
        .order_by(Appointment.date.desc(), Appointment.time.desc())
        .all()
    )
    show_id = request.args.get('show', type=int)
    highlight = Appointment.query.get(show_id) if show_id else None
    return render_template('admin_appointments.html', appointments=appointments, highlight=highlight)

#Doctor routes
@app.route('/doctor/dashboard')
def doctor_dashboard():
    if session.get('user_type') != 'doctor':
        return redirect(url_for('login'))
    doctor = Doctor.query.get(session['user_id'])
    today = date.today()
    next_week = today + timedelta(days=7)
    upcoming_appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor.id,
        Appointment.date >= today,
        Appointment.date <= next_week,
        Appointment.status == 'Booked'
    ).order_by(Appointment.date, Appointment.time).all()
    patient_ids = [pid for (pid,) in db.session.query(
        Appointment.patient_id).filter(Appointment.doctor_id==doctor.id).distinct().all()]
    patients = Patient.query.filter(Patient.id.in_(patient_ids)).all() if patient_ids else []
    return render_template('doctor_dashboard.html', doctor=doctor, 
                           upcoming_appointments=upcoming_appointments, 
                           patients=patients)

@app.route('/doctor/appointments')
def doctor_appointments():
    if session.get('user_type') != 'doctor':
        return redirect(url_for('login'))
    doctor = Doctor.query.get(session['user_id'])
    appointments = (
        Appointment.query.filter_by(doctor_id=doctor.id)
        .order_by(Appointment.date.desc(), Appointment.time.desc())
        .all()
    )
    return render_template('doctor_appointments.html', appointments=appointments)

@app.route('/doctor/complete_appointment/<int:appointment_id>', methods=['GET', 'POST'])
def complete_appointment(appointment_id):
    if session.get('user_type') != 'doctor':
        return redirect(url_for('login'))
    appointment = Appointment.query.get_or_404(appointment_id)
    if request.method == 'POST':
        appointment.status = 'Completed'
        treatment = Treatment.query.filter_by(
            appointment_id=appointment_id
        ).first() or Treatment(appointment_id=appointment_id)
        treatment.diagnosis = request.form.get('diagnosis')
        treatment.prescription = request.form.get('prescription')
        treatment.notes = request.form.get('notes')
        db.session.add(treatment)
        db.session.commit()
        flash('Appointment completed successfully!', 'success')
        return redirect(url_for('doctor_dashboard'))
    return render_template('complete_appointment.html', appointment=appointment)

@app.route('/doctor/cancel_appointment/<int:appointment_id>')
def doctor_cancel_appointment(appointment_id):
    if session.get('user_type') != 'doctor':
        return redirect(url_for('login'))
    appointment = Appointment.query.get_or_404(appointment_id)
    appointment.status = 'Cancelled'
    db.session.commit()
    flash('Appointment cancelled!', 'success')
    return redirect(url_for('doctor_dashboard'))

@app.route('/doctor/patient_history/<int:patient_id>')
def patient_history(patient_id):
    if session.get('user_type') != 'doctor':
        return redirect(url_for('login'))
    doctor = Doctor.query.get(session['user_id'])
    patient = Patient.query.get_or_404(patient_id)
    appointments = Appointment.query.filter_by(patient_id=patient_id, doctor_id=doctor.id, 
                                               status='Completed').order_by(Appointment.date.desc()).all()
    return render_template('patient_history.html', patient=patient, appointments=appointments)

@app.route('/doctor/availability', methods=['GET', 'POST'])
def doctor_availability():
    if session.get('user_type') != 'doctor':
        return redirect(url_for('login'))
    doctor = Doctor.query.get(session['user_id'])
    if request.method == 'POST':
        date_str = request.form.get('date')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        av = DoctorAvailability(
            doctor_id=doctor.id,
            date=datetime.strptime(date_str, '%Y-%m-%d').date(),
            start_time=start_time,
            end_time=end_time
        )
        db.session.add(av)
        db.session.commit()
        flash('Availability added successfully!', 'success')
        return redirect(url_for('doctor_availability'))
    
    today = date.today()
    next_week = today + timedelta(days=7)
    availabilities = (
        DoctorAvailability.query
        .filter(
            DoctorAvailability.doctor_id == doctor.id,
            DoctorAvailability.date >= today,
            DoctorAvailability.date <= next_week
        )
        .order_by(DoctorAvailability.date)
        .all()
    )
    time_slots = [(f"{h:02d}:{m:02d}", f"{h:02d}:{m:02d}") for h in range(6, 24) for m in (0, 30)]
    return render_template('doctor_availability.html', availabilities=availabilities, 
                           time_slots=time_slots)

#Patient routes
@app.route('/patient/dashboard')
def patient_dashboard():
    if session.get('user_type') != 'patient':
        return redirect(url_for('login'))
    patient = Patient.query.get(session['user_id'])
    departments = Department.query.all()
    upcoming_appointments = (
        Appointment.query.filter(
            Appointment.patient_id == patient.id,
            Appointment.date >= date.today(),
            Appointment.status == "Booked",
        )
        .order_by(Appointment.date, Appointment.time)
        .all()
    )
    today = date.today()
    next_week = today + timedelta(days=7)
    doctors_availability = (
        db.session.query(Doctor, DoctorAvailability)
        .join(DoctorAvailability, Doctor.id == DoctorAvailability.doctor_id)
        .filter(
            DoctorAvailability.date >= today,
            DoctorAvailability.date <= next_week,
            Doctor.is_active == True,
        )
        .all()
    )
    search_query = request.args.get('search','')
    search_results = []
    if search_query:
        search_results = (
            Doctor.query.join(Department)
            .filter(
                or_(
                    Doctor.name.ilike(f"%{search_query}%"),
                    Department.name.ilike(f"%{search_query}%"),
                    Doctor.specialization.ilike(f"%{search_query}%"),
                ),
                Doctor.is_active == True,
            )
            .all()
        )
    return render_template('patient_dashboard.html', patient=patient, departments=departments, 
                           upcoming_appointments=upcoming_appointments, doctors_availability=doctors_availability,
                           search_query=search_query, search_results=search_results)

@app.route('/patient/department/<int:dept_id>')
def patient_department(dept_id):
    if session.get('user_type') != 'patient':
        return redirect(url_for('login'))
    dept = Department.query.get_or_404(dept_id)
    doctors = Doctor.query.filter_by(department_id=dept_id, is_active=True).all()
    return render_template('patient_department.html', department=dept, doctors=doctors)

@app.route('/patient/profile', methods=['GET', 'POST'])
def patient_profile():
    if session.get('user_type') != 'patient':
        return redirect(url_for('login'))
    patient = Patient.query.get(session['user_id'])
    if request.method == 'POST':
        patient.name = request.form.get('name')
        patient.age = request.form.get('age')
        patient.gender = request.form.get('gender')
        patient.contact = request.form.get('contact')
        patient.address = request.form.get('address')
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('patient_dashboard'))
    return render_template('patient_profile.html', patient=patient)

@app.route('/patient/book_appointment/<int:doctor_id>', methods=['GET', 'POST'])
def book_appointment(doctor_id):
    if session.get('user_type') != 'patient':
        return redirect(url_for('login'))
    doctor = Doctor.query.get_or_404(doctor_id)
    if not doctor.is_active:
        flash('Doctor is not available for booking at the moment.', 'warning')
        return redirect(url_for('patient_dashboard'))
    patient = Patient.query.get(session['user_id'])
    if request.method == 'POST':
        date_str = request.form.get('date')
        time_str = request.form.get('time')
        the_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        if time_str not in slots_for_doctor_date(doctor_id, the_date):
            flash('Selected slot is no longer available. Please choose another.', 'danger')
            return redirect(url_for('book_appointment', doctor_id=doctor_id))
        ap = Appointment(patient_id=patient.id, doctor_id=doctor_id, date=the_date, time=time_str)
        db.session.add(ap)
        db.session.commit()
        flash('Appointment booked successfully!', 'success')
        return redirect(url_for('patient_dashboard'))
    start_day = date.today()
    week = week_slots_for_doctor(doctor_id, start_day)
    return render_template('book_appointment.html', doctor=doctor, week=week)

@app.route('/patient/cancel_appointment/<int:appointment_id>')
def cancel_appointment(appointment_id):
    if session.get('user_type') != 'patient':
        return redirect(url_for('login'))
    appointment = Appointment.query.get_or_404(appointment_id)
    if appointment.patient_id != session['user_id']:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('patient_dashboard'))
    appointment.status = 'Cancelled'
    db.session.commit()
    flash('Appointment cancelled successfully!', 'success')
    return redirect(url_for('patient_dashboard'))

@app.route('/patient/reschedule_appointment/<int:appointment_id>', methods=['GET', 'POST'])
def reschedule_appointment(appointment_id):
    if session.get('user_type') != 'patient':
        return redirect(url_for('login'))   
    appointment = Appointment.query.get_or_404(appointment_id)   
    if appointment.patient_id != session['user_id']:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('patient_dashboard'))    
    if appointment.status != 'Booked':
        flash('Only booked appointments can be rescheduled.', 'warning')
        return redirect(url_for('appointment_history'))   
    doctor = appointment.doctor    
    if request.method == 'POST':
        new_date_str = request.form.get('date')
        new_time = request.form.get('time')
        new_date = datetime.strptime(new_date_str, '%Y-%m-%d').date()       
        if new_time not in slots_for_doctor_date(doctor.id, new_date):
            flash('Selected slot is no longer available. Please choose another.', 'danger')
            return redirect(url_for('reschedule_appointment', appointment_id=appointment_id))        
        appointment.date = new_date
        appointment.time = new_time
        db.session.commit()
        flash('Appointment rescheduled successfully!', 'success')
        return redirect(url_for('patient_dashboard')) 
    start_day = date.today()
    week = week_slots_for_doctor(doctor.id, start_day)   
    return render_template('reschedule_appointment.html', appointment=appointment, doctor=doctor, week=week)

@app.route('/patient/appointment_history')
def appointment_history():
    if session.get('user_type') != 'patient':
        return redirect(url_for('login'))
    patient = Patient.query.get(session['user_id'])
    appointments = (
        Appointment.query.filter_by(patient_id=patient.id)
        .order_by(Appointment.date.desc(), Appointment.time.desc())
        .all()
    )
    show_id = request.args.get('show', type=int)
    highlight = Appointment.query.get(show_id) if show_id else None
    return render_template('appointment_history.html',appointments=appointments,highlight=highlight)

@app.route('/patient/doctor_profile/<int:doctor_id>')
def doctor_profile(doctor_id):
    if session.get('user_type') != 'patient':
        return redirect(url_for('login'))
    doctor = Doctor.query.get_or_404(doctor_id)
    if not doctor.is_active:
        flash('This doctor is currently unavailable.', 'warning')
        return redirect(url_for('patient_dashboard'))
    today = date.today()
    next_week = today + timedelta(days=7)
    availabilities = DoctorAvailability.query.filter(DoctorAvailability.doctor_id==doctor_id, 
                                                     DoctorAvailability.date>=today, 
                                                     DoctorAvailability.date<=next_week).order_by(DoctorAvailability.date).all()
    return render_template('doctor_profile.html', doctor=doctor, availabilities=availabilities)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
