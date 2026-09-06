# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import logging
import binascii
import time
import re
import copy

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import ec, utils as ecutils
from cryptography.hazmat.primitives import serialization

from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidSignature

from py_vapid.utils import b64urldecode, b64urlencode
from py_vapid.jwt import sign

# Show compliance version. For earlier versions see previously tagged releases.
VERSION = "VAPID-RFC/ECE-RFC"


class VapidException(Exception):
    """An exception wrapper for Vapid."""
    pass


class Vapid01(object):
    """Minimal VAPID Draft 01 signature generation library.

    https://tools.ietf.org/html/draft-ietf-webpush-vapid-01

    """
    _private_key = None
    _public_key = None
    _schema = "WebPush"

    def __init__(self, private_key=None, conf=None):
        """Initialize VAPID with an optional private key.

        :param private_key: A private key object
        :type private_key: ec.EllipticCurvePrivateKey

        """
        if conf is None:
            conf = {}
        self.conf = conf
        self.private_key = private_key
        if private_key:
            self._public_key = self.private_key.public_key()

    @classmethod
    def from_raw(cls, private_raw):
        """Initialize VAPID using a private key point in "raw" or
        "uncompressed" form. Raw keys consist of a single, 32 octet
        encoded integer.

        :param private_raw: A private key point in uncompressed form.
        :type private_raw: bytes

        """
        key = ec.derive_private_key(
            int(binascii.hexlify(b64urldecode(private_raw)), 16),
            curve=ec.SECP256R1(),
            backend=default_backend())
        return cls(key)

    @classmethod
    def from_raw_public(cls, public_raw):
        key = ec.EllipticCurvePublicKey.from_encoded_point(
            curve=ec.SECP256R1(),
            data=b64urldecode(public_raw)
        )
        ss = cls()
        ss._public_key = key
        return ss

    @classmethod
    def from_pem(cls, private_key):
        """Initialize VAPID using a private key in PEM format.

        :param private_key: A private key in PEM format.
        :type private_key: bytes

        """
        try:
            key = serialization.load_pem_private_key(
                private_key,
                password=None,
                backend=default_backend()
            )
            return cls(key)
        except Exception:
            lines = [line.strip() for line in private_key.splitlines() if line.strip() and not line.strip().startswith(b"-----")]
            return cls.from_der(b''.join(lines))

    @classmethod
    def from_der(cls, private_key):
        """Initialize VAPID using a private key in DER format.

        :param private_key: A private key in DER format and Base64-encoded.
        :type private_key: bytes

        """
        key = serialization.load_der_private_key(b64urldecode(private_key),
                                                 password=None,
                                                 backend=default_backend())
        return cls(key)

    @classmethod
    def from_file(cls, private_key_file=None):
        """Initialize VAPID using a file containing a private key in PEM or
        DER format.

        :param private_key_file: Name of the file containing the private key
        :type private_key_file: str

        """
        if not os.path.isfile(private_key_file):
            logging.info("Private key not found, generating key...")
            vapid = cls()
            vapid.generate_keys()
            vapid.save_key(private_key_file)
            return vapid
        with open(private_key_file, 'r') as file:
            private_key = file.read()
        try:
            if "-----BEGIN" in private_key:
                vapid = cls.from_pem(private_key.encode('utf8'))
            else:
                vapid = cls.from_der(private_key.encode('utf8'))
            return vapid
        except Exception as exc:
            logging.error("Could not open private key file: %s", repr(exc))
            raise VapidException(exc)

    @classmethod
    def from_string(cls, private_key):
        """Initialize VAPID using a string containing the private key. This
        will try to determine if the key is in RAW or DER format.

        :param private_key: String containing the key info
        :type private_key: str

        """

        pkey = private_key.encode().replace(b"\n", b"")
        key = b64urldecode(pkey)
        if len(key) == 32:
            return cls.from_raw(pkey)
        return cls.from_der(pkey)

    @classmethod
    def verify(cls, key, auth):
        """Verify a VAPID authorization token.

        :param key: base64 serialized public key
        :type key: str
        :param auth: authorization token
        type key: str

        """
        tokens = auth.rsplit(' ', 1)[1].rsplit('.', 1)
        kp = cls().from_raw_public(key.encode())
        return kp.verify_token(
            validation_token=tokens[0].encode(),
            verification_token=tokens[1]
        )

    @property
    def private_key(self):
        """The VAPID private ECDSA key"""
        if not self._private_key:
            raise VapidException("No private key. Call generate_keys()")
        return self._private_key

    @private_key.setter
    def private_key(self, value):
        """Set the VAPID private ECDSA key

        :param value: the byte array containing the private ECDSA key data
        :type value: ec.EllipticCurvePrivateKey

        """
        self._private_key = value
        if value:
            self._public_key = self.private_key.public_key()

    @property
    def public_key(self):
        """The VAPID public ECDSA key

        The public key is currently read only. Set it via the `.private_key`
        method. This will autogenerate a public and private key if no value
        has been set.

        :returns ec.EllipticCurvePublicKey

        """
        return self._public_key

    def generate_keys(self):
        """Generate a valid ECDSA Key Pair."""
        self.private_key = ec.generate_private_key(ec.SECP256R1(),
                                                   default_backend())

    def private_pem(self):
        return self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

    def public_pem(self):
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

    def save_key(self, key_file):
        """Save the private key to a PEM file.

        :param key_file: The file path to save the private key data
        :type key_file: str

        """
        with open(key_file, "wb") as file:
            file.write(self.private_pem())
            file.close()

    def save_public_key(self, key_file):
        """Save the public key to a PEM file.
        :param key_file: The name of the file to save the public key
        :type key_file: str

        """
        with open(key_file, "wb") as file:
            file.write(self.public_pem())
            file.close()

    def verify_token(self, validation_token, verification_token):
        """Internally used to verify the verification token is correct.

        :param validation_token: Provided validation token string
        :type validation_token: str
        :param verification_token: Generated verification token
        :type verification_token: str
        :returns: Boolean indicating if verifictation token is valid.
        :rtype: boolean

        """
        hsig = b64urldecode(verification_token.encode('utf8'))
        r = int(binascii.hexlify(hsig[:32]), 16)
        s = int(binascii.hexlify(hsig[32:]), 16)
        try:
            self.public_key.verify(
                ecutils.encode_dss_signature(r, s),
                validation_token,
                signature_algorithm=ec.ECDSA(hashes.SHA256())
            )
            return True
        except InvalidSignature:
            return False

    def _base_sign(self, claims):
        cclaims = copy.deepcopy(claims)
        if not cclaims.get('exp'):
            cclaims['exp'] = int(time.time()) + 86400
        if not self.conf.get('no-strict', False):
            valid = _check_sub(cclaims.get('sub', ''))
        else:
            valid = cclaims.get('sub') is not None
        if not valid:
            raise VapidException(
                "Missing 'sub' from claims. "
                "'sub' is your admin email as a mailto: link.")
        if not re.match(r"^https?://[^/:]+(:\d+)?$",
                        cclaims.get("aud", ""),
                        re.IGNORECASE):
            raise VapidException(
                "Missing 'aud' from claims. "
                "'aud' is the scheme, host and optional port for this "
                "transaction e.g. https://example.com:8080")
        return cclaims

    def sign(self, claims, crypto_key=None):
        """Sign a set of claims.
        :param claims: JSON object containing the JWT claims to use.
        :type claims: dict
        :param crypto_key: Optional existing crypto_key header content. The
            vapid public key will be appended to this data.
        :type crypto_key: str
        :returns: a hash containing the header fields to use in
            the subscription update.
        :rtype: dict

        """
        sig = sign(self._base_sign(claims), self.private_key)
        pkey = 'p256ecdsa='
        pkey += b64urlencode(
            self.public_key.public_bytes(
                serialization.Encoding.X962,
                serialization.PublicFormat.UncompressedPoint
            ))
        if crypto_key:
            crypto_key = crypto_key + ';' + pkey
        else:
            crypto_key = pkey

        return {"Authorization": "{} {}".format(self._schema, sig.strip('=')),
                "Crypto-Key": crypto_key}


class Vapid02(Vapid01):
    """Minimal Vapid RFC8292 signature generation library

    https://tools.ietf.org/html/rfc8292

    """
    _schema = "vapid"

    def sign(self, claims, crypto_key=None):
        """Generate an authorization token

        :param claims: JSON object containing the JWT claims to use.
        :type claims: dict
        :param crypto_key: Optional existing crypto_key header content. The
            vapid public key will be appended to this data.
        :type crypto_key: str
        :returns: a hash containing the header fields to use in
            the subscription update.
        :rtype: dict
        """
        sig = sign(self._base_sign(claims), self.private_key)
        pkey = self.public_key.public_bytes(
                serialization.Encoding.X962,
                serialization.PublicFormat.UncompressedPoint
            )
        return{
            "Authorization": "{schema} t={t},k={k}".format(
                schema=self._schema,
                t=sig,
                k=b64urlencode(pkey)
            )
        }

    @classmethod
    def verify(cls, auth):
        """Ensure that the token is correctly formatted and valid

        :param auth: An Authorization header
        :type auth: str
        :rtype: bool

        """
        pref_tok = auth.rsplit(' ', 1)
        assert pref_tok[0].lower() == cls._schema, (
                "Incorrect schema specified")
        parts = {}
        for tok in pref_tok[1].split(','):
            kv = tok.split('=', 1)
            parts[kv[0]] = kv[1]
        assert 'k' in parts.keys(), (
                "Auth missing public key 'k' value")
        assert 't' in parts.keys(), (
                "Auth missing token set 't' value")
        kp = cls().from_raw_public(parts['k'].encode())
        tokens = parts['t'].rsplit('.', 1)
        return kp.verify_token(
            validation_token=tokens[0].encode(),
            verification_token=tokens[1]
        )


def _check_sub(sub):
    """ Check to see if the `sub` is a properly formatted `mailto:`

    a `mailto:` should be a SMTP mail address. Mind you, since I run
    YouFailAtEmail.com, you have every right to yell about how terrible
    this check is. I really should be doing a proper component parse
    and valiate each component individually per RFC5341, instead I do
    the unholy regex you see below.

    :param sub: Candidate JWT `sub`
    :type sub: str
    :rtype: bool

    """
    pattern = (
        r"^(mailto:.+@((localhost|[%\w-]+(\.[%\w-]+)+|([0-9a-f]{1,4}):+([0-9a-f]{1,4})?)))|https:\/\/(localhost|[\w-]+\.[\w\.-]+|([0-9a-f]{1,4}:+)+([0-9a-f]{1,4})?)$" # noqa
        )
    return re.match(pattern, sub, re.IGNORECASE) is not None


Vapid = Vapid02
