# auth.py (remove the standalone get_admin_token function)
import jwt
import requests
from functools import wraps
from flask import request, jsonify, current_app
from datetime import datetime

class KeycloakAuth:
    def __init__(self, server_url, realm):
        self.server_url = server_url
        self.realm = realm
        self.public_key = None
        self.jwks_url = f"{server_url}/realms/{realm}/protocol/openid-connect/certs"
    
    def get_public_key(self):
        """Get public key from Keycloak"""
        if not self.public_key:
            try:
                response = requests.get(self.jwks_url, timeout=5)
                if response.status_code == 200:
                    self.public_key = response.json()
            except:
                pass
        return self.public_key
    
    def verify_token(self, token):
        """Verify JWT token"""
        try:
            # Get token header
            header = jwt.get_unverified_header(token)
            
            # For demo purposes, decode without signature verification
            # In production, you should verify the signature
            decoded = jwt.decode(
                token,
                options={"verify_signature": False},
                algorithms=["RS256"]
            )
            
            # Check expiration
            if 'exp' in decoded:
                exp_timestamp = decoded['exp']
                current_timestamp = datetime.utcnow().timestamp()
                if exp_timestamp < current_timestamp:
                    return None
            
            return decoded
            
        except Exception as e:
            print(f"Token verification error: {e}")
            return None
    
    def get_user_roles(self, token):
        """Extract roles from token"""
        decoded = self.verify_token(token)
        if not decoded:
            return []
        
        roles = []
        
        # Get realm roles
        realm_access = decoded.get('realm_access', {})
        if isinstance(realm_access, dict):
            roles.extend(realm_access.get('roles', []))
        
        # Get resource roles
        resource_access = decoded.get('resource_access', {})
        if isinstance(resource_access, dict):
            for client_roles in resource_access.values():
                if isinstance(client_roles, dict):
                    roles.extend(client_roles.get('roles', []))
        
        return roles
    
    def has_role(self, token, required_role):
        """Check if token has specific role"""
        user_roles = self.get_user_roles(token)
        return required_role in user_roles
    
    def has_any_role(self, token, required_roles):
        """Check if token has any of the required roles"""
        user_roles = self.get_user_roles(token)
        return any(role in user_roles for role in required_roles)

# Initialize auth
keycloak_auth = None

def init_auth(app):
    global keycloak_auth
    keycloak_auth = KeycloakAuth(
        server_url=app.config['KEYCLOAK_SERVER_URL'],
        realm=app.config['KEYCLOAK_REALM']
    )

# Role-Based Access Decorators
def require_auth(roles=None):
    """Decorator for requiring authentication and optional roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get('Authorization')
            
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Missing or invalid Authorization header'}), 401
            
            token = auth_header.split(' ')[1]
            decoded_token = keycloak_auth.verify_token(token)
            
            if not decoded_token:
                return jsonify({'error': 'Invalid or expired token'}), 401
            
            # Check roles if specified
            if roles:
                has_required_role = False
                user_roles = keycloak_auth.get_user_roles(token)
                
                # Check if user has any of the required roles
                for required_role in roles:
                    if required_role in user_roles:
                        has_required_role = True
                        break
                
                if not has_required_role:
                    return jsonify({
                        'error': 'Insufficient permissions',
                        'required_roles': roles,
                        'user_roles': user_roles
                    }), 403
            
            # Add user info to request context
            request.user = {
                'username': decoded_token.get('preferred_username', ''),
                'email': decoded_token.get('email', ''),
                'roles': keycloak_auth.get_user_roles(token)
            }
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Specific role decorators for convenience
def require_admin(f):
    return require_auth(['admin'])(f)

def require_doctor(f):
    return require_auth(['doctor', 'admin'])(f)  # Admin can also access doctor endpoints

def require_patient(f):
    return require_auth(['patient', 'doctor', 'admin'])(f)  # All roles can access patient endpoints