from fastapi import Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import requests
import os 
import dotenv

dotenv.load_dotenv()

def get_cognito_public_keys():
    response = requests.get(os.getenv("AWS_SIGNING_KEY_URL"))
    return response.json()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    try:
        token = credentials.credentials
        header = jwt.get_unverified_header(token)
        kid = header["kid"]
        public_keys = get_cognito_public_keys()
        public_key = None
        for key in public_keys["keys"]:
            if key["kid"] == kid:
                public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                break
        if not public_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        payload = jwt.decode(token, public_key, algorithms=["RS256"])
    except Exception as e:
        print("Error verifying token: ", e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return token

def verify_token_query(token = Query(None)):
    try:
        if token:
            try:
                header = jwt.get_unverified_header(token)
                kid = header["kid"]
                public_keys = get_cognito_public_keys()
                public_key = None
                for key in public_keys["keys"]:
                    if key["kid"] == kid:
                        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                        break
                payload = jwt.decode(token, public_key, algorithms=["RS256"])
                if not public_key:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
            except Exception as e:
                print("Error verifying token: ", e)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
            return token
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No token provided")
    except Exception as e:
        print("Error verifying token: ", e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
