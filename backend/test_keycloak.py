# test_keycloak.py
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from keycloak_admin import keycloak_admin

# Test configuration
print("🔧 Testing Keycloak Admin Connection...")
print(f"KEYCLOAK_SERVER_URL: {os.getenv('KEYCLOAK_SERVER_URL')}")
print(f"KEYCLOAK_REALM: {os.getenv('KEYCLOAK_REALM')}")
print(f"KEYCLOAK_ADMIN: {os.getenv('KEYCLOAK_ADMIN')}")
print(f"KEYCLOAK_MASTER_REALM: {os.getenv('KEYCLOAK_MASTER_REALM', 'master')}")

# Test admin token
print("\n🔑 Testing admin token retrieval...")
token = keycloak_admin.get_admin_token()
if token:
    print(f"✅ Admin token obtained successfully (first 20 chars): {token[:20]}...")
else:
    print("❌ Failed to get admin token")

# Test getting users
print("\n👥 Testing user retrieval...")
users = keycloak_admin.get_users(max=5)
if users is not None:
    print(f"✅ Retrieved {len(users)} users")
    for user in users[:3]:  # Show first 3 users
        print(f"  - {user.get('username')} ({user.get('email')})")
else:
    print("❌ Failed to get users")

# Test available roles
print("\n🎭 Testing role retrieval...")
roles = keycloak_admin.get_available_roles()
if roles:
    print(f"✅ Found {len(roles)} roles:")
    for role in roles[:5]:  # Show first 5 roles
        print(f"  - {role.get('name')}")
else:
    print("❌ Failed to get roles")

print("\n✅ Test completed!")