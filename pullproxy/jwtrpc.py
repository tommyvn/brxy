import jwt
# from jsonrpc import JSONRPCResponseManager, dispatcher
import uuid
import time
from jsonrpcclient.request import Request
from jsonrpcserver import Methods as _Methods
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key


class RequestFactory(object):
    def __init__(self, key, iss, expires_after=30):
        self._key = key
        self._iss = iss
        self._expires_after = expires_after
        key_obj = load_pem_private_key(self._key, password=None, backend=default_backend())
        if isinstance(key_obj, rsa.RSAPrivateKey):
            self._algorithm = "RS256"
        elif isinstance(key_obj, ec.EllipticCurvePrivateKey):
            # key_obj.curve.key_size is the key size if ever I want to use it
            self._algorithm = "ES256"
        else:
            raise ValueError("private key isn't a supported type")

    def __call__(self, method, *args, **kwargs):
        return jwt.encode({
            "iss": self._iss,
            "exp": time.time() + self._expires_after,
            "jsonrpc": Request(method, *args, **kwargs)
        }, self._key, self._algorithm)


class Methods(_Methods):
    def __init__(self, key_iss_lookup_fun, *args, **kwargs):
        self._key_iss_lookup_fun = key_iss_lookup_fun
        super(Methods, self).__init__(*args, **kwargs)

    def dispatch(self, jwt_request):
        UNSAFE_request = jwt.decode(jwt_request, verify=False)
        print(UNSAFE_request)
        key = self._key_iss_lookup_fun(UNSAFE_request['iss'])
        key_obj = load_pem_public_key(key, backend=default_backend())
        if isinstance(key_obj, rsa.RSAPublicKey):
            algorithm = "RS256"
        elif isinstance(key_obj, ec.EllipticCurvePublicKey):
            # key_obj.curve.key_size is the key size if ever I want to use it
            algorithm = "ES256"
        else:
            raise ValueError("private key isn't a supported type")
        safe_request = jwt.decode(jwt_request, key, algorithm)
        return super(Methods, self).dispatch(safe_request['jsonrpc'])
