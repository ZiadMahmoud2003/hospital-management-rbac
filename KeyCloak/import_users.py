import csv
import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get configuration
KEYCLOAK_URL = os.getenv("KEYCLOAK_SERVER_URL")
REALM_NAME = os.getenv("KEYCLOAK_REALM")
CLIENT_ID = os.getenv("BACKEND_CLIENT_ID")
CLIENT_SECRET = os.getenv("BACKEND_CLIENT_SECRET")

print("🚀 Starting Keycloak User Import")
print("=" * 60)

def get_admin_token():
    """Get admin token for API access"""
    token_url = f"{KEYCLOAK_URL}/realms/{REALM_NAME}/protocol/openid-connect/token"
    print(f"🔐 Getting token from: {token_url}")
    
    payload = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    
    try:
        response = requests.post(token_url, data=payload, timeout=10)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            token_data = response.json()
            print("   ✅ Token obtained successfully!")
            return token_data["access_token"]
        else:
            print(f"   ❌ Failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

def import_users():
    """Import users from CSV"""
    csv_file = 'excel_users.csv'
    
    if not os.path.exists(csv_file):
        print(f"❌ CSV file not found: {csv_file}")
        return
    
    print(f"📂 Reading: {csv_file}")
    
    # Get token
    token = get_admin_token()
    if not token:
        print("❌ Cannot proceed without token")
        return
    
    users_url = f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            username = row['Username'].strip()
            email = row['Email'].strip()
            password = row['Password'].strip()
            role = row['Assigned Role'].strip()
            first_name = row.get('FirstName', '').strip() or username
            last_name = row.get('LastName', '').strip() or 'User'
            
            print(f"\n➡️ Processing: {username} (role: {role})")
            
            try:
                # Check if user exists
                check = requests.get(
                    f"{users_url}?username={username}&exact=true",
                    headers=headers,
                    timeout=10
                )
                
                if check.status_code == 200 and check.json():
                    print(f"   ⚠️ Already exists, skipping")
                    user_id = check.json()[0]['id']
                else:
                    # Create user
                    user_data = {
                        "username": username,
                        "email": email,
                        "firstName": first_name,
                        "lastName": last_name,
                        "enabled": True,
                        "credentials": [{
                            "type": "password",
                            "value": password,
                            "temporary": False
                        }]
                    }
                    
                    create = requests.post(
                        users_url,
                        headers=headers,
                        json=user_data,
                        timeout=10
                    )
                    
                    if create.status_code == 201:
                        user_id = create.headers['Location'].split('/')[-1]
                        print(f"   ✅ Created user")
                    else:
                        print(f"   ❌ Failed to create: {create.status_code}")
                        continue
                
                # Get role
                role_url = f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/roles/{role}"
                role_resp = requests.get(role_url, headers=headers, timeout=10)
                
                if role_resp.status_code == 200:
                    role_data = role_resp.json()
                    assign_url = f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users/{user_id}/role-mappings/realm"
                    assign_resp = requests.post(
                        assign_url,
                        headers=headers,
                        json=[role_data],
                        timeout=10
                    )
                    
                    if assign_resp.status_code in [200, 204]:
                        print(f"   ✅ Role '{role}' assigned")
                    else:
                        print(f"   ❌ Failed to assign role: {assign_resp.status_code}")
                else:
                    print(f"   ❌ Role '{role}' not found")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Import process completed!")

if __name__ == '__main__':
    import_users()