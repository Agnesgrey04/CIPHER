import httpx
from fastapi import APIRouter, HTTPException, status, Header, Depends
from auth.schemas import LoginRequest, AuthenticationResponse
from auth.firebaseconfig import webapikey, db
from firebase_admin import auth

router=APIRouter(prefix="/auth", tags=["Authentication"])

identifytoolkitURL=(
    f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
    f"?key={webapikey}"
)

#function is used to lock a specific page, if trying to access it, the token is verifyed with respective role for authentication
async def verifyuser(authorization: str=Header(...)):
    try:
        if authorization.startswith("Bearer "):
            token = authorization[7:].strip()
        else:
            token = authorization.strip()
        return auth.verify_id_token(token)      #returns the user dictonary
    
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or expired token")


def requiredrole(allowedrole: str):
    async def rolecheck(user: dict=Depends(verifyuser)):
        uid=user["uid"]
        userdocument=db.collection("users").document(uid).get()

        if not userdocument.exists:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: User profile not found.")

        userole=userdocument.to_dict().get("role")
        if userole!=allowedrole:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Forbidden: This endpoint requires '{allowedrole}' privileges.")

        return user
    return rolecheck

@router.post("/login", response_model=AuthenticationResponse)
async def login(credentials: LoginRequest):

    #preparing payload for authentication
    payload={
        "email":credentials.email,
        "password":credentials.password,
        "returnSecureToken":True
    }

    async with httpx.AsyncClient() as client:
        try:
            response=await client.post(identifytoolkitURL, json=payload, timeout=10.0)  #calling authentication endpoint
            data=response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

    if response.status_code != 200:
        errormessage=data.get("error", {}).get("message", "AUTHENTICATION_FAILED")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"{errormessage}"
        )

    uid=data["localId"]
    email=data["email"]
    idtoken=data["idToken"]

    userreference=db.collection("users").document(uid)
    userdocument=userreference.get()

    if not userdocument.exists:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: User account is not authorized in CIPHER.")

    userdata=userdocument.to_dict()
    role=userdata.get("role")

    if not role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: No role assigned to this account.")


    return AuthenticationResponse(
        accesstoken=idtoken,
        tokentype="bearer",
        uid=uid,
        email=email,
        role=role,
        message="Authentication successful"
    )