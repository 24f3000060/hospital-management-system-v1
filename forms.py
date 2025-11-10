from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField, TextAreaField, SelectField, DateField
from wtforms.validators import DataRequired, Email, Length, EqualTo


class LoginForm(FlaskForm):
    username = StringField("Username or Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])


class PatientRegistrationForm(FlaskForm):
    username = StringField(
        "Username", validators=[DataRequired(), Length(min=3, max=80)]
    )
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password")]
    )
    name = StringField("Full Name", validators=[DataRequired()])
    age = IntegerField("Age", validators=[DataRequired()])
    gender = SelectField(
        "Gender",
        choices=[("Male", "Male"), ("Female", "Female"), ("Other", "Other")],
        validators=[DataRequired()],
    )
    contact = StringField("Contact Number", validators=[DataRequired()])
    address = TextAreaField("Address", validators=[DataRequired()])


class DoctorForm(FlaskForm):
    username = StringField(
        "Username", validators=[DataRequired(), Length(min=3, max=80)]
    )
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    name = StringField("Full Name", validators=[DataRequired()])
    department_id = SelectField("Department", coerce=int, validators=[DataRequired()])
    specialization = StringField("Specialization", validators=[DataRequired()])
    experience = IntegerField("Years of Experience", validators=[DataRequired()])
    contact = StringField("Contact Number", validators=[DataRequired()])


class PatientUpdateForm(FlaskForm):
    name = StringField("Full Name", validators=[DataRequired()])
    age = IntegerField("Age", validators=[DataRequired()])
    gender = SelectField(
        "Gender",
        choices=[("Male", "Male"), ("Female", "Female"), ("Other", "Other")],
        validators=[DataRequired()],
    )
    contact = StringField("Contact Number", validators=[DataRequired()])
    address = TextAreaField("Address", validators=[DataRequired()])


class AppointmentForm(FlaskForm):
    doctor_id = SelectField("Doctor", coerce=int, validators=[DataRequired()])
    date = DateField("Appointment Date", validators=[DataRequired()])
    time = SelectField("Time Slot", validators=[DataRequired()])


class TreatmentForm(FlaskForm):
    diagnosis = TextAreaField("Diagnosis", validators=[DataRequired()])
    prescription = TextAreaField("Prescription", validators=[DataRequired()])
    notes = TextAreaField("Additional Notes")


class DoctorAvailabilityForm(FlaskForm):
    date = DateField("Date", validators=[DataRequired()])
    start_time = SelectField("Start Time", validators=[DataRequired()])
    end_time = SelectField("End Time", validators=[DataRequired()])
