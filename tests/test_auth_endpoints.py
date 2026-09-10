from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal, User

client = TestClient(app)

def test_user_authentication_flow():
    test_email = "test_auth_123@example.com"
    test_password = "secure_test_password_123"
    
    # 1. Clean up any previous test user if it exists
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == test_email).first()
        if user:
            db.delete(user)
            db.commit()
    finally:
        db.close()
        
    try:
        # 2. Register a new user
        register_payload = {
            "first_name": "Test",
            "middle_name": "Auth",
            "last_name": "User",
            "email": test_email,
            "password": test_password
        }
        response = client.post("/api/v1/auth/register", json=register_payload)
        assert response.status_code == 200, f"Registration failed: {response.text}"
        data = response.json()
        assert data["email"] == test_email
        assert data["first_name"] == "Test"
        assert data["middle_name"] == "Auth"
        assert data["last_name"] == "User"
        assert "password_hash" not in data, "Should not return password_hash in response"
        
        # 3. Attempt to register the same user again (should fail)
        response_dup = client.post("/api/v1/auth/register", json=register_payload)
        assert response_dup.status_code == 400
        assert "already exists" in response_dup.json()["detail"].lower()
        
        # 4. Login with correct credentials
        login_payload = {
            "email": test_email,
            "password": test_password
        }
        response_login = client.post("/api/v1/auth/login", json=login_payload)
        assert response_login.status_code == 200
        login_data = response_login.json()
        assert login_data["email"] == test_email
        assert login_data["first_name"] == "Test"
        assert login_data["last_name"] == "User"
        
        # 5. Login with incorrect password (should fail)
        response_wrong_pwd = client.post("/api/v1/auth/login", json={
            "email": test_email,
            "password": "wrong_password"
        })
        assert response_wrong_pwd.status_code == 401
        assert "invalid credentials" in response_wrong_pwd.json()["detail"].lower()
        
        # 6. Login with incorrect email (should fail)
        response_wrong_email = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": test_password
        })
        assert response_wrong_email.status_code == 401
        assert "invalid credentials" in response_wrong_email.json()["detail"].lower()
        
        print("\n🎉 ALL AUTH ENDPOINT TESTS PASSED SUCCESSFULY!")
        
    finally:
        # 7. Clean up the test user after tests complete
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == test_email).first()
            if user:
                db.delete(user)
                db.commit()
                print("🧹 Cleaned up test user from the database.")
        finally:
            db.close()

if __name__ == "__main__":
    test_user_authentication_flow()
