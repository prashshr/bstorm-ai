from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.limiter import limiter
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.session import get_db
from app.models.models import User, ProviderCredential, Discussion, Message, SearchHistory
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.core.crypto import (
    generate_salt,
    generate_random_key,
    derive_pdk,
    encrypt_uek,
    decrypt_uek,
    decrypt_secret,
    encrypt_secret,
    encrypt_field,
    decrypt_field_or_plaintext,
)


router = APIRouter()


@router.post("/register", response_model=TokenResponse)
@limiter.limit("10/minute")
def register(request: Request, payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")

    # Generate salt and user-specific master key (UEK)
    salt_hex = generate_salt()
    uek = generate_random_key()
    pdk = derive_pdk(payload.password, salt_hex)
    uek_encrypted = encrypt_uek(uek, pdk)

    user = User(
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        encryption_salt=salt_hex,
        master_key_encrypted=uek_encrypted,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return TokenResponse(access_token=create_access_token(str(user.id), extra_claims={"uek": uek}))


@router.post("/login", response_model=TokenResponse)
@limiter.limit("20/minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Auto-migration for legacy users
    if not user.master_key_encrypted:
        salt_hex = generate_salt()
        uek = generate_random_key()
        pdk = derive_pdk(payload.password, salt_hex)
        uek_encrypted = encrypt_uek(uek, pdk)

        user.encryption_salt = salt_hex
        user.master_key_encrypted = uek_encrypted

        # Re-encrypt legacy provider credentials for this user
        creds = db.query(ProviderCredential).filter(ProviderCredential.user_id == user.id).all()
        for cred in creds:
            try:
                # Decrypt using legacy server key (decrypt_secret with no custom key falls back to legacy)
                api_key_plain = decrypt_secret(cred.api_key_encrypted)
                # Re-encrypt using the new user encryption key (UEK)
                cred.api_key_encrypted = encrypt_secret(api_key_plain, uek)
            except Exception:
                # Skip if already migrated or if decryption fails
                pass

        # Re-encrypt discussions
        discussions = db.query(Discussion).filter(Discussion.user_id == user.id).all()
        for disc in discussions:
            try:
                plain_title = decrypt_field_or_plaintext(disc.title, None)
                disc.title = encrypt_field(plain_title, uek)
                plain_question = decrypt_field_or_plaintext(disc.question, None)
                disc.question = encrypt_field(plain_question, uek)
                if disc.state_json:
                    plain_state = decrypt_field_or_plaintext(disc.state_json, None)
                    disc.state_json = encrypt_field(plain_state, uek)
            except Exception:
                pass

        # Re-encrypt messages
        messages = db.query(Message).filter(Message.user_id == user.id).all()
        for msg in messages:
            try:
                plain_content = decrypt_field_or_plaintext(msg.content, None)
                msg.content = encrypt_field(plain_content, uek)
            except Exception:
                pass

        # Re-encrypt search history
        histories = db.query(SearchHistory).filter(SearchHistory.user_id == user.id).all()
        for hist in histories:
            try:
                plain_query = decrypt_field_or_plaintext(hist.query, None)
                hist.query = encrypt_field(plain_query, uek)
            except Exception:
                pass

        db.commit()
        db.refresh(user)
    else:
        # Normal login: derive PDK and decrypt UEK
        try:
            pdk = derive_pdk(payload.password, user.encryption_salt)
            uek = decrypt_uek(user.master_key_encrypted, pdk)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to decrypt secure storage key.",
            )

    return TokenResponse(access_token=create_access_token(str(user.id), extra_claims={"uek": uek}))
