from backend.app.utils.auth import hash_password, verify_password
from backend.app.database import SessionLocal
from backend.app.models import User
from sqlalchemy.orm import Session

# Test the hash/verify functions
test_password = "TestPassword123!"
hashed = hash_password(test_password)

print(f"Test password: {test_password}")
print(f"Hashed: {hashed}")
print(f"Verify: {verify_password(test_password, hashed)}")

# Update a test user with known password
db = SessionLocal()
try:
    user = db.query(User).filter(User.username == "sujiterp").first()
    if user:
        user.hashed_password = hash_password("TestPass123")
        db.commit()
        print(f"\n✅ Updated user 'sujiterp' password to 'TestPass123'")
    else:
        print("\n❌ User 'sujiterp' not found")
        
    # Also update director account
    user2 = db.query(User).filter(User.username == "director_vvma005_c158").first()
    if user2:
        user2.hashed_password = hash_password("TestPass123")
        db.commit()
        print(f"✅ Updated user 'director_vvma005_c158' password to 'TestPass123'")
    else:
        print(f"❌ User 'director_vvma005_c158' not found")
finally:
    db.close()

print("\nNow try logging in with credentials:")
print("  Username: sujiterp or director_vvma005_c158")
print("  Password: TestPass123")
