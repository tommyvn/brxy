import unittest
from pullproxy.jwtrpc import RequestFactory, Methods
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import time
import random


class JWTRPCCase(unittest.TestCase):
    def setUp(self):
        private_key = ec.generate_private_key(
            ec.SECP384R1(), default_backend()
        )
        self.serialized_private = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        public_key = private_key.public_key()
        self.serialized_public = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        key = self.serialized_private
        iss = random.randint(0, 9)
        expires_after = 10
        self.client = RequestFactory(key, iss, expires_after)
        key_iss_lookup_fun = lambda k: {
            iss: self.serialized_public,
            random.randint(0, 9): None
        }[k]
        self.server = Methods(key_iss_lookup_fun)

    def test_client(self):
        call = self.client("mymethod", testing=1234)
        worked = False
        def mymethod(testing):
            nonlocal worked
            worked = True
            return "yolo!!!!"
        self.server.add(mymethod)
        print("called and got {}".format(self.server.dispatch(call)))
        self.assertTrue(worked)
