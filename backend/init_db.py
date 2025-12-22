from app import app, db
from models import Patient, Doctor, Appointment, MedicalRecord
from datetime import datetime, timedelta

def init_database():
    with app.app_context():
        # Create all tables
        db.create_all()
        print("✅ Database tables created")
        
        # Add sample data if tables are empty
        if Patient.query.count() == 0:
            # Sample patients
            patients = [
                Patient(
                    patient_id="P001",
                    name="John Smith",
                    age=45,
                    gender="Male",
                    condition="Hypertension",
                    doctor_assigned="Dr. Wilson",
                    status="Active",
                    created_by="system"
                ),
                Patient(
                    patient_id="P002",
                    name="Emma Johnson",
                    age=32,
                    gender="Female",
                    condition="Diabetes Type 2",
                    doctor_assigned="Dr. Brown",
                    status="Active",
                    created_by="system"
                ),
                Patient(
                    patient_id="P003",
                    name="Michael Davis",
                    age=58,
                    gender="Male",
                    condition="Cardiac Arrhythmia",
                    doctor_assigned="Dr. Wilson",
                    status="Recovering",
                    created_by="system"
                )
            ]
            
            # Sample doctors
            doctors = [
                Doctor(
                    doctor_id="D001",
                    name="Dr. Sarah Wilson",
                    specialty="Cardiology",
                    email="swilson@hospital.com",
                    phone="+1-555-0101",
                    department="Cardiology",
                    years_experience=15,
                    status="Active",
                    created_by="system"
                ),
                Doctor(
                    doctor_id="D002",
                    name="Dr. James Brown",
                    specialty="Neurology",
                    email="jbrown@hospital.com",
                    phone="+1-555-0102",
                    department="Neurology",
                    years_experience=10,
                    status="Active",
                    created_by="system"
                ),
                Doctor(
                    doctor_id="D003",
                    name="Dr. Maria Martinez",
                    specialty="Obstetrics",
                    email="mmartinez@hospital.com",
                    phone="+1-555-0103",
                    department="Obstetrics & Gynecology",
                    years_experience=12,
                    status="Active",
                    created_by="system"
                )
            ]
            
            # Sample appointments
            appointments = [
                Appointment(
                    appointment_id="A001",
                    patient_id="P001",
                    doctor_id="D001",
                    appointment_date=datetime.utcnow() + timedelta(days=1),
                    reason="Follow-up consultation",
                    status="Scheduled",
                    notes="Regular checkup",
                    created_by="system"
                ),
                Appointment(
                    appointment_id="A002",
                    patient_id="P002",
                    doctor_id="D002",
                    appointment_date=datetime.utcnow() + timedelta(days=2),
                    reason="Neurology consultation",
                    status="Scheduled",
                    notes="New patient",
                    created_by="system"
                )
            ]
            
            # Add all to database
            for patient in patients:
                db.session.add(patient)
            
            for doctor in doctors:
                db.session.add(doctor)
                
            for appointment in appointments:
                db.session.add(appointment)
            
            db.session.commit()
            print("✅ Sample data added to database")
        
        print("📊 Database Statistics:")
        print(f"   Patients: {Patient.query.count()}")
        print(f"   Doctors: {Doctor.query.count()}")
        print(f"   Appointments: {Appointment.query.count()}")

if __name__ == '__main__':
    init_database()