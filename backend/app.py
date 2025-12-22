# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os
import uuid
from datetime import datetime
from dotenv import load_dotenv

# Import modules
from models import db, Patient, Doctor, Appointment, MedicalRecord
from auth import init_auth, require_auth, require_admin, require_doctor, require_patient
from keycloak_admin import keycloak_admin

from keycloak_admin import keycloak_admin
# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True)

# Configuration
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'secret-key-change-this')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///hospital.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['KEYCLOAK_SERVER_URL'] = os.getenv('KEYCLOAK_SERVER_URL', 'http://localhost:8080')
app.config['KEYCLOAK_REALM'] = os.getenv('KEYCLOAK_REALM', 'hospital-realm')
app.config['KEYCLOAK_ADMIN'] = os.getenv('KEYCLOAK_ADMIN', 'admin')
app.config['KEYCLOAK_ADMIN_PASSWORD'] = os.getenv('KEYCLOAK_ADMIN_PASSWORD', 'admin')
app.config['KEYCLOAK_MASTER_REALM'] = os.getenv('KEYCLOAK_MASTER_REALM', 'master')

# Initialize
db.init_app(app)
init_auth(app)

# Initialize KeycloakAdmin with app context
#keycloak_admin.init_app(app)

# ==================== AUTHENTICATION ENDPOINTS ====================

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Exchange authorization code for tokens"""
    data = request.json
    code = data.get('code')
    redirect_uri = data.get('redirect_uri', 'http://localhost:3000')
    
    if not code:
        return jsonify({'error': 'Authorization code required'}), 400
    
    # Exchange code for tokens
    token_url = f"{app.config['KEYCLOAK_SERVER_URL']}/realms/{app.config['KEYCLOAK_REALM']}/protocol/openid-connect/token"
    
    token_data = {
        'grant_type': 'authorization_code',
        'client_id': 'hospital-frontend',
        'redirect_uri': redirect_uri,
        'code': code
    }
    
    try:
        import requests
        response = requests.post(token_url, data=token_data)
        
        if response.status_code != 200:
            return jsonify({'error': 'Failed to exchange code'}), 400
        
        tokens = response.json()
        access_token = tokens["access_token"]
        
        # Get user info
        from auth import keycloak_auth
        decoded_token = keycloak_auth.verify_token(access_token)
        if not decoded_token:
            return jsonify({'error': 'Invalid token'}), 400
        
        user_roles = keycloak_auth.get_user_roles(access_token)
        
        user_info = {
            'username': decoded_token.get('preferred_username', ''),
            'email': decoded_token.get('email', ''),
            'roles': user_roles
        }
        
        return jsonify({
            'access_token': access_token,
            'refresh_token': tokens.get('refresh_token', ''),
            'user': user_info
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/userinfo', methods=['GET'])
@require_auth()
def userinfo():
    """Get current user info"""
    return jsonify({
        'username': request.user['username'],
        'email': request.user['email'],
        'roles': request.user['roles']
    }), 200

# ==================== USER MANAGEMENT ENDPOINTS ====================

# In app.py, update the user management endpoints:

@app.route('/api/users', methods=['GET'])
@require_admin
def get_users():
    """Get all users from Keycloak (admin only)"""
    try:
        # Get users using keycloak_admin
        users = keycloak_admin.get_users()
        
        if users is None:
            return jsonify({'error': 'Failed to connect to Keycloak admin API'}), 500
        
        # Transform Keycloak users to our format
        formatted_users = []
        for user in users:
            # Get user roles
            user_roles = user.get('roles', [])
            
            # Determine main role
            main_role = 'patient'  # default
            for role in user_roles:
                if isinstance(role, dict) and role.get('name') == 'admin':
                    main_role = 'admin'
                    break
                elif isinstance(role, dict) and role.get('name') == 'doctor':
                    main_role = 'doctor'
            
            # Format created timestamp
            created_timestamp = user.get('createdTimestamp')
            created_date = ''
            if created_timestamp:
                try:
                    # Convert milliseconds to datetime
                    created_date = datetime.fromtimestamp(created_timestamp/1000).isoformat()
                except:
                    created_date = str(created_timestamp)
            
            formatted_users.append({
                'id': user.get('id', ''),
                'username': user.get('username', ''),
                'email': user.get('email', ''),
                'firstName': user.get('firstName', ''),
                'lastName': user.get('lastName', ''),
                'role': main_role,
                'status': 'active' if user.get('enabled', True) else 'inactive',
                'created': created_date,
                'emailVerified': user.get('emailVerified', False)
            })
        
        return jsonify(formatted_users), 200
        
    except Exception as e:
        print(f"❌ Error fetching users: {str(e)}")
        return jsonify({'error': f'Failed to fetch users: {str(e)}'}), 500

@app.route('/api/users', methods=['POST'])
@require_admin
def create_user():
    """Create new user in Keycloak (admin only)"""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['username', 'email', 'password', 'role']
        missing_fields = []
        for field in required_fields:
            if field not in data or not data[field]:
                missing_fields.append(field)
        
        if missing_fields:
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
        
        # Prepare user data for Keycloak
        user_data = {
            'username': data['username'],
            'email': data['email'],
            'firstName': data.get('firstName', ''),
            'lastName': data.get('lastName', ''),
            'password': data['password'],
            'roles': [data['role']]  # Single role for simplicity
        }
        
        # Create user using keycloak_admin
        result = keycloak_admin.create_user(user_data)
        
        if result and result.get('success'):
            return jsonify({
                'message': 'User created successfully',
                'user_id': result.get('id', 'Unknown')
            }), 201
        else:
            return jsonify({'error': 'Failed to create user in Keycloak. Check server logs for details.'}), 400
        
    except Exception as e:
        print(f"❌ Error creating user: {str(e)}")
        return jsonify({'error': f'Failed to create user: {str(e)}'}), 500
    
    
@app.route('/api/users/<user_id>', methods=['PUT'])
@require_admin
def update_user(user_id):
    """Update user in Keycloak (admin only)"""
    try:
        data = request.json
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Prepare update data
        update_data = {}
        if 'email' in data:
            update_data['email'] = data['email']
        if 'username' in data:
            update_data['username'] = data['username']
        if 'firstName' in data:
            update_data['firstName'] = data['firstName']
        if 'lastName' in data:
            update_data['lastName'] = data['lastName']
        if 'status' in data:
            update_data['enabled'] = data['status'] == 'active'
        if 'role' in data:
            update_data['roles'] = [data['role']]
        
        # Update user using keycloak_admin
        result = keycloak_admin.update_user(user_id, update_data)
        
        if result:
            return jsonify({
                'message': 'User updated successfully',
                'user_id': user_id
            }), 200
        else:
            return jsonify({'error': 'Failed to update user in Keycloak'}), 400
        
    except Exception as e:
        print(f"Error updating user: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<user_id>', methods=['DELETE'])
@require_admin
def delete_user(user_id):
    """Delete user from Keycloak (admin only)"""
    try:
        # Delete user using keycloak_admin
        success = keycloak_admin.delete_user(user_id)
        
        if success:
            return jsonify({
                'message': 'User deleted successfully',
                'user_id': user_id
            }), 200
        else:
            return jsonify({'error': 'Failed to delete user from Keycloak'}), 400
        
    except Exception as e:
        print(f"Error deleting user: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<user_id>/reset-password', methods=['POST'])
@require_admin
def reset_user_password(user_id):
    """Reset user password (admin only)"""
    try:
        data = request.json
        new_password = data.get('password')
        
        if not new_password:
            return jsonify({'error': 'New password is required'}), 400
        
        # Reset password using keycloak_admin
        success = keycloak_admin.reset_password(user_id, new_password)
        
        if success:
            return jsonify({
                'message': 'Password reset successfully',
                'user_id': user_id
            }), 200
        else:
            return jsonify({'error': 'Failed to reset password'}), 400
        
    except Exception as e:
        print(f"Error resetting password: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/roles', methods=['GET'])
@require_admin
def get_available_roles():
    """Get all available roles (admin only)"""
    try:
        # Get available roles using keycloak_admin
        roles = keycloak_admin.get_available_roles()
        
        if roles is None:
            return jsonify({'error': 'Failed to get available roles'}), 500
        
        return jsonify(roles), 200
        
    except Exception as e:
        print(f"Error getting roles: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ==================== PATIENT ENDPOINTS ====================

@app.route('/api/patients', methods=['GET'])
@require_auth()  # All authenticated users can view patients
def get_patients():
    """Get all patients (role-based filtering)"""
    try:
        patients = Patient.query.all()
        
        # Role-based data filtering
        user_roles = request.user['roles']
        username = request.user['username']
        
        result = []
        for patient in patients:
            # Patients can only see their own records
            if 'patient' in user_roles:
                # In a real system, you would match patient ID with user
                # For demo, we'll check if username contains 'patient'
                if 'patient' not in username.lower():
                    continue
            
            result.append({
                'id': patient.patient_id,
                'name': patient.name,
                'age': patient.age,
                'gender': patient.gender,
                'condition': patient.condition,
                'doctor': patient.doctor_assigned,
                'admission_date': patient.admission_date.strftime('%Y-%m-%d') if patient.admission_date else None,
                'status': patient.status
            })
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/patients', methods=['POST'])
@require_doctor  # Only doctors and admins can create patients
def create_patient():
    """Create new patient (doctor/admin only)"""
    try:
        data = request.json
        
        # Generate unique patient ID
        patient_id = f"P{str(uuid.uuid4())[:8].upper()}"
        
        patient = Patient(
            patient_id=patient_id,
            name=data['name'],
            age=data['age'],
            gender=data['gender'],
            condition=data['condition'],
            doctor_assigned=data.get('doctor', 'Unassigned'),
            status=data.get('status', 'Active'),
            created_by=request.user['username']
        )
        
        db.session.add(patient)
        db.session.commit()
        
        return jsonify({
            'message': 'Patient created successfully',
            'patient_id': patient_id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/api/patients/<patient_id>', methods=['GET'])
@require_auth()  # All authenticated users can view
def get_patient(patient_id):
    """Get specific patient details"""
    try:
        patient = Patient.query.filter_by(patient_id=patient_id).first()
        
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
        # Role-based access check
        user_roles = request.user['roles']
        if 'patient' in user_roles:
            # Patients can only view their own records
            # In real system, check if patient ID matches user's patient ID
            pass
        
        return jsonify({
            'id': patient.patient_id,
            'name': patient.name,
            'age': patient.age,
            'gender': patient.gender,
            'condition': patient.condition,
            'doctor': patient.doctor_assigned,
            'admission_date': patient.admission_date.strftime('%Y-%m-%d') if patient.admission_date else None,
            'status': patient.status,
            'created_by': patient.created_by
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/patients/<patient_id>', methods=['PUT'])
@require_doctor  # Only doctors and admins can update
def update_patient(patient_id):
    """Update patient information"""
    try:
        patient = Patient.query.filter_by(patient_id=patient_id).first()
        
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
        data = request.json
        
        # Update fields
        if 'name' in data:
            patient.name = data['name']
        if 'age' in data:
            patient.age = data['age']
        if 'condition' in data:
            patient.condition = data['condition']
        if 'doctor' in data:
            patient.doctor_assigned = data['doctor']
        if 'status' in data:
            patient.status = data['status']
        
        db.session.commit()
        
        return jsonify({'message': 'Patient updated successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/api/patients/<patient_id>', methods=['DELETE'])
@require_admin  # Only admin can delete
def delete_patient(patient_id):
    """Delete patient (admin only)"""
    try:
        patient = Patient.query.filter_by(patient_id=patient_id).first()
        
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
        db.session.delete(patient)
        db.session.commit()
        
        return jsonify({'message': 'Patient deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# ==================== DOCTOR ENDPOINTS ====================

@app.route('/api/doctors', methods=['GET'])
@require_auth()  # All authenticated users can view doctors
def get_doctors():
    """Get all doctors"""
    try:
        doctors = Doctor.query.all()
        
        result = []
        for doctor in doctors:
            result.append({
                'id': doctor.doctor_id,
                'name': doctor.name,
                'specialty': doctor.specialty,
                'email': doctor.email,
                'phone': doctor.phone,
                'department': doctor.department,
                'years_experience': doctor.years_experience,
                'status': doctor.status
            })
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/doctors', methods=['POST'])
@require_admin  # Only admin can create doctors
def create_doctor():
    """Create new doctor (admin only)"""
    try:
        data = request.json
        
        doctor_id = f"D{str(uuid.uuid4())[:8].upper()}"
        
        doctor = Doctor(
            doctor_id=doctor_id,
            name=data['name'],
            specialty=data['specialty'],
            email=data['email'],
            phone=data.get('phone', ''),
            department=data.get('department', 'General'),
            years_experience=data.get('years_experience', 0),
            status=data.get('status', 'Active'),
            created_by=request.user['username']
        )
        
        db.session.add(doctor)
        db.session.commit()
        
        return jsonify({
            'message': 'Doctor created successfully',
            'doctor_id': doctor_id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/api/doctors/<doctor_id>', methods=['PUT'])
@require_admin  # Only admin can update doctors
def update_doctor(doctor_id):
    """Update doctor information"""
    try:
        doctor = Doctor.query.filter_by(doctor_id=doctor_id).first()
        
        if not doctor:
            return jsonify({'error': 'Doctor not found'}), 404
        
        data = request.json
        
        # Update fields
        if 'name' in data:
            doctor.name = data['name']
        if 'specialty' in data:
            doctor.specialty = data['specialty']
        if 'email' in data:
            doctor.email = data['email']
        if 'phone' in data:
            doctor.phone = data['phone']
        if 'department' in data:
            doctor.department = data['department']
        if 'status' in data:
            doctor.status = data['status']
        
        db.session.commit()
        
        return jsonify({'message': 'Doctor updated successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# ==================== APPOINTMENT ENDPOINTS ====================

@app.route('/api/appointments', methods=['GET'])
@require_auth()  # All authenticated users can view appointments
def get_appointments():
    """Get all appointments (role-based filtering)"""
    try:
        appointments = Appointment.query.all()
        
        user_roles = request.user['roles']
        username = request.user['username']
        
        result = []
        for appointment in appointments:
            # Role-based filtering
            if 'patient' in user_roles:
                # Patients can only see their own appointments
                # For demo, we'll check if patient_id matches username pattern
                if 'patient' not in username.lower():
                    continue
            
            result.append({
                'id': appointment.appointment_id,
                'patient_id': appointment.patient_id,
                'doctor_id': appointment.doctor_id,
                'appointment_date': appointment.appointment_date.strftime('%Y-%m-%d %H:%M'),
                'reason': appointment.reason,
                'status': appointment.status,
                'notes': appointment.notes,
                'created_by': appointment.created_by
            })
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/appointments', methods=['POST'])
@require_doctor  # Only doctors and admins can create appointments
def create_appointment():
    """Create new appointment"""
    try:
        data = request.json
        
        appointment_id = f"A{str(uuid.uuid4())[:8].upper()}"
        
        appointment = Appointment(
            appointment_id=appointment_id,
            patient_id=data['patient_id'],
            doctor_id=data['doctor_id'],
            appointment_date=datetime.fromisoformat(data['appointment_date'].replace('Z', '+00:00')),
            reason=data.get('reason', ''),
            status=data.get('status', 'Scheduled'),
            notes=data.get('notes', ''),
            created_by=request.user['username']
        )
        
        db.session.add(appointment)
        db.session.commit()
        
        return jsonify({
            'message': 'Appointment created successfully',
            'appointment_id': appointment_id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/api/appointments/<appointment_id>', methods=['PUT'])
@require_doctor  # Only doctors and admins can update appointments
def update_appointment(appointment_id):
    """Update appointment"""
    try:
        appointment = Appointment.query.filter_by(appointment_id=appointment_id).first()
        
        if not appointment:
            return jsonify({'error': 'Appointment not found'}), 404
        
        data = request.json
        
        # Update fields
        if 'patient_id' in data:
            appointment.patient_id = data['patient_id']
        if 'doctor_id' in data:
            appointment.doctor_id = data['doctor_id']
        if 'appointment_date' in data:
            appointment.appointment_date = datetime.fromisoformat(data['appointment_date'].replace('Z', '+00:00'))
        if 'reason' in data:
            appointment.reason = data['reason']
        if 'status' in data:
            appointment.status = data['status']
        if 'notes' in data:
            appointment.notes = data['notes']
        
        db.session.commit()
        
        return jsonify({'message': 'Appointment updated successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/api/appointments/<appointment_id>', methods=['DELETE'])
@require_admin  # Only admin can delete appointments
def delete_appointment(appointment_id):
    """Delete appointment"""
    try:
        appointment = Appointment.query.filter_by(appointment_id=appointment_id).first()
        
        if not appointment:
            return jsonify({'error': 'Appointment not found'}), 404
        
        db.session.delete(appointment)
        db.session.commit()
        
        return jsonify({'message': 'Appointment deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# ==================== MEDICAL RECORDS ENDPOINTS ====================

@app.route('/api/medical-records', methods=['GET'])
@require_auth()  # All authenticated users can view medical records (with filtering)
def get_medical_records():
    """Get medical records (role-based access)"""
    try:
        records = MedicalRecord.query.all()
        
        user_roles = request.user['roles']
        username = request.user['username']
        
        result = []
        for record in records:
            # Patients can only see their own records
            if 'patient' in user_roles:
                # In real system, check if patient_id matches user
                if 'patient' not in username.lower():
                    continue
            
            result.append({
                'id': record.record_id,
                'patient_id': record.patient_id,
                'record_type': record.record_type,
                'description': record.description,
                'doctor_id': record.doctor_id,
                'date': record.date.strftime('%Y-%m-%d'),
                'created_by': record.created_by
            })
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/medical-records', methods=['POST'])
@require_doctor  # Only doctors can create medical records
def create_medical_record():
    """Create medical record (doctor only)"""
    try:
        data = request.json
        
        record_id = f"MR{str(uuid.uuid4())[:8].upper()}"
        
        record = MedicalRecord(
            record_id=record_id,
            patient_id=data['patient_id'],
            record_type=data['record_type'],
            description=data['description'],
            doctor_id=data.get('doctor_id', ''),
            created_by=request.user['username']
        )
        
        db.session.add(record)
        db.session.commit()
        
        return jsonify({
            'message': 'Medical record created successfully',
            'record_id': record_id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# ==================== HEALTH CHECK ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'hospital-management-api',
        'timestamp': datetime.utcnow().isoformat(),
        'database': 'connected' if db.session.bind else 'disconnected',
        'keycloak_admin': 'available' if keycloak_admin else 'unavailable'
    }), 200
    
    
# ==================== USER PROFILE ENDPOINTS ====================

@app.route('/api/profile', methods=['GET'])
@require_auth()
def get_profile():
    """Get current user's profile"""
    try:
        from auth import keycloak_auth
        
        # Get the user's ID from the token
        auth_header = request.headers.get('Authorization')
        token = auth_header.split(' ')[1] if auth_header and auth_header.startswith('Bearer ') else None
        
        if not token:
            return jsonify({'error': 'No token found'}), 401
        
        # Get user info from token
        decoded_token = keycloak_auth.verify_token(token)
        if not decoded_token:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Try to get user details from Keycloak
        user_id = decoded_token.get('sub')
        username = decoded_token.get('preferred_username', '')
        email = decoded_token.get('email', '')
        
        # Get user details from database based on role
        user_roles = request.user['roles']
        user_data = {
            'id': user_id,
            'username': username,
            'email': email,
            'firstName': decoded_token.get('given_name', ''),
            'lastName': decoded_token.get('family_name', ''),
            'roles': user_roles
        }
        
        # Add role-specific data
        if 'patient' in user_roles:
            # Try to find patient record
            patient = Patient.query.filter_by(created_by=username).first()
            if patient:
                user_data['patientInfo'] = {
                    'patientId': patient.patient_id,
                    'name': patient.name,
                    'age': patient.age,
                    'gender': patient.gender,
                    'condition': patient.condition,
                    'doctor': patient.doctor_assigned
                }
        
        elif 'doctor' in user_roles:
            # Try to find doctor record
            doctor = Doctor.query.filter_by(email=email).first()
            if doctor:
                user_data['doctorInfo'] = {
                    'doctorId': doctor.doctor_id,
                    'name': doctor.name,
                    'specialty': doctor.specialty,
                    'department': doctor.department,
                    'experience': doctor.years_experience
                }
        
        return jsonify(user_data), 200
        
    except Exception as e:
        print(f"Error getting profile: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/profile', methods=['PUT'])
@require_auth()
def update_profile():
    """Update current user's profile"""
    try:
        data = request.json
        
        # Get current user info
        auth_header = request.headers.get('Authorization')
        token = auth_header.split(' ')[1] if auth_header and auth_header.startswith('Bearer ') else None
        
        if not token:
            return jsonify({'error': 'No token found'}), 401
        
        from auth import keycloak_auth
        decoded_token = keycloak_auth.verify_token(token)
        if not decoded_token:
            return jsonify({'error': 'Invalid token'}), 401
        
        user_id = decoded_token.get('sub')
        current_username = decoded_token.get('preferred_username', '')
        current_email = decoded_token.get('email', '')
        user_roles = request.user['roles']
        
        # Prepare update data for Keycloak
        update_data = {}
        if 'email' in data and data['email'] != current_email:
            update_data['email'] = data['email']
        if 'firstName' in data:
            update_data['firstName'] = data['firstName']
        if 'lastName' in data:
            update_data['lastName'] = data['lastName']
        
        # Update in Keycloak if there are changes
        if update_data:
            result = keycloak_admin.update_user(user_id, update_data)
            if not result:
                return jsonify({'error': 'Failed to update user in Keycloak'}), 400
        
        # Update password if provided
        if 'password' in data and data['password']:
            success = keycloak_admin.reset_password(user_id, data['password'])
            if not success:
                return jsonify({'error': 'Failed to update password'}), 400
        
        # Update role-specific data in database
        if 'patient' in user_roles and 'patientInfo' in data:
            patient_info = data['patientInfo']
            patient = Patient.query.filter_by(created_by=current_username).first()
            if patient:
                if 'name' in patient_info:
                    patient.name = patient_info['name']
                if 'age' in patient_info:
                    patient.age = patient_info['age']
                if 'gender' in patient_info:
                    patient.gender = patient_info['gender']
                db.session.commit()
        
        elif 'doctor' in user_roles and 'doctorInfo' in data:
            doctor_info = data['doctorInfo']
            doctor = Doctor.query.filter_by(email=current_email).first()
            if doctor:
                if 'name' in doctor_info:
                    doctor.name = doctor_info['name']
                if 'specialty' in doctor_info:
                    doctor.specialty = doctor_info['specialty']
                if 'department' in doctor_info:
                    doctor.department = doctor_info['department']
                db.session.commit()
        
        return jsonify({'message': 'Profile updated successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error updating profile: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/profile/password', methods=['PUT'])
@require_auth()
def change_password():
    """Change current user's password"""
    try:
        data = request.json
        
        if 'currentPassword' not in data or 'newPassword' not in data:
            return jsonify({'error': 'Current password and new password are required'}), 400
        
        # Note: Keycloak doesn't have an API to verify current password
        # In production, you should use Keycloak's password reset with current password verification
        # For now, we'll just reset the password if user is authenticated
        
        # Get user ID from token
        auth_header = request.headers.get('Authorization')
        token = auth_header.split(' ')[1] if auth_header and auth_header.startswith('Bearer ') else None
        
        if not token:
            return jsonify({'error': 'No token found'}), 401
        
        from auth import keycloak_auth
        decoded_token = keycloak_auth.verify_token(token)
        if not decoded_token:
            return jsonify({'error': 'Invalid token'}), 401
        
        user_id = decoded_token.get('sub')
        
        # Reset password in Keycloak
        success = keycloak_admin.reset_password(user_id, data['newPassword'])
        
        if success:
            return jsonify({'message': 'Password changed successfully'}), 200
        else:
            return jsonify({'error': 'Failed to change password'}), 400
        
    except Exception as e:
        print(f"Error changing password: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ==================== INITIALIZE DATABASE ====================

@app.before_request
def initialize_database():
    """Initialize database on first request"""
    if not hasattr(app, 'database_initialized'):
        with app.app_context():
            # Create all tables
            db.create_all()
            print("✅ Database tables created")
            
            # Add sample data if database is empty
            if Patient.query.count() == 0:
                try:
                    from init_db import init_database
                    init_database()
                    print("✅ Sample data added to database")
                except ImportError as e:
                    print(f"⚠️ Could not import init_db: {e}")
                except Exception as e:
                    print(f"⚠️ Error adding sample data: {e}")
            
            print("📊 Database Statistics:")
            print(f"   Patients: {Patient.query.count()}")
            print(f"   Doctors: {Doctor.query.count()}")
            print(f"   Appointments: {Appointment.query.count()}")
            print(f"   Medical Records: {MedicalRecord.query.count()}")
            
            app.database_initialized = True

if __name__ == '__main__':
    print("🚀 Starting Hospital Management System Backend...")
    print(f"Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"Keycloak URL: {app.config['KEYCLOAK_SERVER_URL']}")
    print(f"Realm: {app.config['KEYCLOAK_REALM']}")
    print(f"Master Realm: {app.config['KEYCLOAK_MASTER_REALM']}")
    
    # Initialize database immediately
    with app.app_context():
        db.create_all()
        print("✅ Database initialized")
        
        # Add sample data if needed
        if Patient.query.count() == 0:
            try:
                from init_db import init_database
                init_database()
            except Exception as e:
                print(f"⚠️ Error initializing sample data: {e}")
    
    app.run(debug=True, port=5000)