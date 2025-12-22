# keycloak_admin.py
import requests
from datetime import datetime, timedelta
from flask import current_app

class KeycloakAdmin:
    def __init__(self):
        self.admin_token = None
        self.token_expiry = None  # Store as datetime object
    
    def _get_config(self, key):
        """Get configuration from Flask app"""
        try:
            return current_app.config[key]
        except RuntimeError:
            # If we're not in app context, use default
            defaults = {
                'KEYCLOAK_SERVER_URL': 'http://localhost:8080',
                'KEYCLOAK_REALM': 'hospital-realm',
                'KEYCLOAK_ADMIN': 'admin',
                'KEYCLOAK_ADMIN_PASSWORD': 'admin',
                'KEYCLOAK_MASTER_REALM': 'master'
            }
            return defaults.get(key, '')
    
    def get_admin_token(self):
        """Get admin token for Keycloak Admin API"""
        # Check if token is still valid (comparing datetime objects)
        if self.admin_token and self.token_expiry and datetime.utcnow() < self.token_expiry:
            return self.admin_token
        
        server_url = self._get_config('KEYCLOAK_SERVER_URL')
        master_realm = self._get_config('KEYCLOAK_MASTER_REALM')
        admin_username = self._get_config('KEYCLOAK_ADMIN')
        admin_password = self._get_config('KEYCLOAK_ADMIN_PASSWORD')
        
        token_url = f"{server_url}/realms/{master_realm}/protocol/openid-connect/token"
        
        payload = {
            'grant_type': 'password',
            'client_id': 'admin-cli',
            'username': admin_username,
            'password': admin_password
        }
        
        try:
            print(f"🔑 Requesting admin token from {token_url}")
            response = requests.post(token_url, data=payload, timeout=10)
            
            if response.status_code == 200:
                token_data = response.json()
                self.admin_token = token_data['access_token']
                
                # Set expiry as datetime object
                expires_in = token_data.get('expires_in', 60)
                self.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in - 30)
                
                print("✅ Admin token obtained successfully")
                return self.admin_token
            else:
                print(f"❌ Failed to get admin token: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"❌ Error getting admin token: {e}")
            return None
    
    def get_headers(self):
        """Get headers with admin token"""
        token = self.get_admin_token()
        if not token:
            print("❌ No admin token available")
            return None
        
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def get_users(self, search=None, first=0, max=100):
        """Get users from Keycloak"""
        try:
            headers = self.get_headers()
            if not headers:
                return []
            
            server_url = self._get_config('KEYCLOAK_SERVER_URL')
            realm = self._get_config('KEYCLOAK_REALM')
            
            url = f"{server_url}/admin/realms/{realm}/users"
            print(f"🔍 Fetching users from: {url}")
            
            params = {}
            if search:
                params['search'] = search
            if first is not None:
                params['first'] = first
            if max is not None:
                params['max'] = max
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                users = response.json()
                print(f"✅ Found {len(users)} users")
                
                # Get roles for each user
                for user in users:
                    try:
                        user['roles'] = self.get_user_roles(user['id'])
                    except Exception as e:
                        print(f"⚠️ Could not get roles for user {user.get('username')}: {e}")
                        user['roles'] = []
                
                return users
            else:
                print(f"❌ Failed to get users: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            print(f"❌ Error getting users: {e}")
            return []
    
    def get_user_roles(self, user_id):
        """Get roles for a user"""
        try:
            headers = self.get_headers()
            if not headers:
                return []
            
            server_url = self._get_config('KEYCLOAK_SERVER_URL')
            realm = self._get_config('KEYCLOAK_REALM')
            
            url = f"{server_url}/admin/realms/{realm}/users/{user_id}/role-mappings/realm"
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"⚠️ Failed to get user roles: {response.status_code}")
                return []
        except Exception as e:
            print(f"⚠️ Error getting user roles: {e}")
            return []
    
    def create_user(self, user_data):
        """Create new user in Keycloak"""
        try:
            headers = self.get_headers()
            if not headers:
                return None
            
            server_url = self._get_config('KEYCLOAK_SERVER_URL')
            realm = self._get_config('KEYCLOAK_REALM')
            
            url = f"{server_url}/admin/realms/{realm}/users"
            
            # Prepare user data
            user_payload = {
                'username': user_data['username'],
                'email': user_data.get('email', ''),
                'firstName': user_data.get('firstName', ''),
                'lastName': user_data.get('lastName', ''),
                'enabled': True,
                'credentials': [{
                    'type': 'password',
                    'value': user_data['password'],
                    'temporary': False
                }]
            }
            
            print(f"➕ Creating user: {user_data['username']}")
            response = requests.post(url, headers=headers, json=user_payload, timeout=10)
            
            if response.status_code in [201, 204]:
                print(f"✅ User {user_data['username']} created successfully")
                
                # Try to get the user ID from location header
                location = response.headers.get('Location')
                user_id = None
                
                if location:
                    try:
                        user_id = location.split('/')[-1]
                        print(f"📝 User ID: {user_id}")
                    except:
                        pass
                
                # Assign roles if specified
                if 'roles' in user_data and user_data['roles']:
                    if user_id:
                        success = self.assign_roles(user_id, user_data['roles'])
                        if not success:
                            print(f"⚠️ Failed to assign roles to user {user_data['username']}")
                
                return {'id': user_id or 'unknown', 'username': user_data['username'], 'success': True}
            else:
                error_msg = response.json().get('errorMessage', response.text)
                print(f"❌ Failed to create user {user_data['username']}: {response.status_code} - {error_msg}")
                return None
                
        except Exception as e:
            print(f"❌ Error creating user: {e}")
            return None
    
    def update_user(self, user_id, user_data):
        """Update user in Keycloak"""
        try:
            headers = self.get_headers()
            if not headers:
                return None
            
            server_url = self._get_config('KEYCLOAK_SERVER_URL')
            realm = self._get_config('KEYCLOAK_REALM')
            
            url = f"{server_url}/admin/realms/{realm}/users/{user_id}"
            
            # Prepare update payload
            update_payload = {}
            if 'email' in user_data:
                update_payload['email'] = user_data['email']
            if 'username' in user_data:
                update_payload['username'] = user_data['username']
            if 'firstName' in user_data:
                update_payload['firstName'] = user_data['firstName']
            if 'lastName' in user_data:
                update_payload['lastName'] = user_data['lastName']
            if 'enabled' in user_data:
                update_payload['enabled'] = user_data['enabled']
            
            print(f"✏️ Updating user {user_id}")
            response = requests.put(url, headers=headers, json=update_payload, timeout=10)
            
            if response.status_code == 204:
                print(f"✅ User {user_id} updated successfully")
                
                # Update roles if specified
                if 'roles' in user_data and user_data['roles']:
                    self.update_user_roles(user_id, user_data['roles'])
                
                return {'id': user_id, 'success': True}
            else:
                error_msg = response.json().get('errorMessage', response.text)
                print(f"❌ Failed to update user {user_id}: {response.status_code} - {error_msg}")
                return None
                
        except Exception as e:
            print(f"❌ Error updating user: {e}")
            return None
    
    def delete_user(self, user_id):
        """Delete user from Keycloak"""
        try:
            headers = self.get_headers()
            if not headers:
                return False
            
            server_url = self._get_config('KEYCLOAK_SERVER_URL')
            realm = self._get_config('KEYCLOAK_REALM')
            
            url = f"{server_url}/admin/realms/{realm}/users/{user_id}"
            
            print(f"🗑️ Deleting user {user_id}")
            response = requests.delete(url, headers=headers, timeout=10)
            
            if response.status_code == 204:
                print(f"✅ User {user_id} deleted successfully")
                return True
            else:
                error_msg = response.json().get('errorMessage', response.text)
                print(f"❌ Failed to delete user {user_id}: {response.status_code} - {error_msg}")
                return False
                
        except Exception as e:
            print(f"❌ Error deleting user: {e}")
            return False
    
    def get_available_roles(self):
        """Get all available roles in realm"""
        try:
            headers = self.get_headers()
            if not headers:
                return []
            
            server_url = self._get_config('KEYCLOAK_SERVER_URL')
            realm = self._get_config('KEYCLOAK_REALM')
            
            url = f"{server_url}/admin/realms/{realm}/roles"
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                roles = response.json()
                print(f"✅ Found {len(roles)} available roles")
                return roles
            else:
                print(f"❌ Failed to get roles: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Error getting roles: {e}")
            return []
    
    def assign_roles(self, user_id, roles):
        """Assign roles to user"""
        try:
            headers = self.get_headers()
            if not headers:
                return False
            
            server_url = self._get_config('KEYCLOAK_SERVER_URL')
            realm = self._get_config('KEYCLOAK_REALM')
            
            # Get role objects
            available_roles = self.get_available_roles()
            if not available_roles:
                return False
            
            roles_to_assign = [role for role in available_roles if role['name'] in roles]
            
            if not roles_to_assign:
                print(f"❌ No valid roles found to assign: {roles}")
                return False
            
            url = f"{server_url}/admin/realms/{realm}/users/{user_id}/role-mappings/realm"
            
            response = requests.post(url, headers=headers, json=roles_to_assign, timeout=10)
            
            if response.status_code in [200, 204]:
                print(f"✅ Assigned roles {roles} to user {user_id}")
                return True
            else:
                print(f"❌ Failed to assign roles: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error assigning roles: {e}")
            return False
    
    def update_user_roles(self, user_id, new_roles):
        """Update user roles (remove old, add new)"""
        try:
            # Get current roles
            current_roles = self.get_user_roles(user_id)
            current_role_names = [role['name'] for role in current_roles]
            
            # Roles to remove
            roles_to_remove = [role for role in current_roles if role['name'] not in new_roles]
            
            # Roles to add
            roles_to_add = [role for role in new_roles if role not in current_role_names]
            
            # Remove old roles
            if roles_to_remove:
                self.remove_roles(user_id, roles_to_remove)
            
            # Add new roles
            if roles_to_add:
                self.assign_roles(user_id, roles_to_add)
            
            return True
            
        except Exception as e:
            print(f"❌ Error updating user roles: {e}")
            return False
    
    def remove_roles(self, user_id, roles):
        """Remove roles from user"""
        try:
            headers = self.get_headers()
            if not headers:
                return False
            
            server_url = self._get_config('KEYCLOAK_SERVER_URL')
            realm = self._get_config('KEYCLOAK_REALM')
            
            url = f"{server_url}/admin/realms/{realm}/users/{user_id}/role-mappings/realm"
            
            response = requests.delete(url, headers=headers, json=roles, timeout=10)
            
            if response.status_code in [200, 204]:
                print(f"✅ Removed roles from user {user_id}")
                return True
            else:
                print(f"❌ Failed to remove roles: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error removing roles: {e}")
            return False
    
    def reset_password(self, user_id, new_password):
        """Reset user password"""
        try:
            headers = self.get_headers()
            if not headers:
                return False
            
            server_url = self._get_config('KEYCLOAK_SERVER_URL')
            realm = self._get_config('KEYCLOAK_REALM')
            
            url = f"{server_url}/admin/realms/{realm}/users/{user_id}/reset-password"
            
            password_payload = {
                'type': 'password',
                'value': new_password,
                'temporary': False
            }
            
            print(f"🔑 Resetting password for user {user_id}")
            response = requests.put(url, headers=headers, json=password_payload, timeout=10)
            
            if response.status_code == 204:
                print(f"✅ Password reset for user {user_id}")
                return True
            else:
                print(f"❌ Failed to reset password: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error resetting password: {e}")
            return False

# Initialize Keycloak Admin instance
keycloak_admin = KeycloakAdmin()