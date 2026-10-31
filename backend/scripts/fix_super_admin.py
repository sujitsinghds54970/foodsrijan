from app.database import SessionLocal
from app.models import User


def ensure_single_super_ceo(username: str = "sujitep") -> None:
    db = SessionLocal()
    try:
        super_admins = db.query(User).filter(User.is_super_admin.is_(True)).all()
        for user in super_admins:
            if user.username != username:
                user.is_super_admin = False
                if user.role in {"super_admin", "super_ceo"}:
                    user.role = "super_admin"
                print(f"⚠️ Revoked super_admin from: {user.username}")

        sujitep = db.query(User).filter(User.username == username).first()
        if sujitep:
            sujitep.is_super_admin = True
            sujitep.role = "super_ceo"
            db.commit()
            print("✅ sujitep is the sole Super CEO")
        else:
            print(f"⚠️ User '{username}' not found")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    ensure_single_super_ceo()
