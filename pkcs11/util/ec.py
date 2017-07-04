"""
Key handling utilities for EC keys (ANSI X.62/RFC3279), domain parameter and
signatures.
"""

from asn1crypto.keys import (
    ECDomainParameters,
    ECPrivateKey,
    NamedCurve,
    PublicKeyInfo,
)
from asn1crypto.core import OctetString

from ..constants import Attribute, ObjectClass
from ..mechanisms import KeyType


def encode_named_curve_parameters(oid):
    """
    Return DER-encoded ANSI X.62 EC parameters for a named curve.

    Curve names are given by object identifier and can be found in
    :mod:`pyasn1_modules.rfc3279`.

    :param str curve: named curve
    :rtype: bytes
    """
    return ECDomainParameters(
        name='named',
        value=NamedCurve.unmap(oid),
    ).dump()


def decode_ec_public_key(der, encode_ec_point=True):
    """
    Decode a DER-encoded EC public key as stored by OpenSSL into a dictionary
    of attributes able to be passed to :meth:`pkcs11.Session.create_object`.

    .. note:: **encode_ec_point**

        For use as an attribute `EC_POINT` should be DER-encoded (True).

        For key derivation implementations can vary.  Since v2.30 the
        specification says implementations MUST accept a raw `EC_POINT` for
        ECDH (False), however not all implementations follow this yet.

    :param bytes der: DER-encoded key
    :param encode_ec_point: See text.
    :rtype: dict(Attribute,*)
    """
    asn1 = PublicKeyInfo.load(der)

    assert asn1.algorithm == 'ec', \
        "Wrong algorithm, not an EC key!"

    ecpoint = bytes(asn1['public_key'])

    if encode_ec_point:
        ecpoint = OctetString(ecpoint).dump()

    return {
        Attribute.KEY_TYPE: KeyType.EC,
        Attribute.CLASS: ObjectClass.PUBLIC_KEY,
        Attribute.EC_PARAMS: asn1['algorithm']['parameters'].dump(),
        Attribute.EC_POINT: ecpoint,
    }


def decode_ec_private_key(der):
    """
    Decode a DER-encoded EC private key as stored by OpenSSL into a dictionary
    of attributes able to be passed to :meth:`pkcs11.Session.create_object`.

    :param bytes der: DER-encoded key
    :rtype: dict(Attribute,*)
    """

    asn1 = ECPrivateKey.load(der)

    return {
        Attribute.KEY_TYPE: KeyType.EC,
        Attribute.CLASS: ObjectClass.PRIVATE_KEY,
        Attribute.EC_PARAMS: asn1['parameters'].dump(),
        Attribute.VALUE: asn1['private_key'],
    }


def encode_ec_public_key(key):
    """
    Encode a DER-encoded EC public key as stored by OpenSSL.

    :param PublicKey key: EC public key
    :rtype: bytes
    """

    ecparams = ECDomainParameters.load(key[Attribute.EC_PARAMS])
    ecpoint = bytes(OctetString.load(key[Attribute.EC_POINT]))

    return PublicKeyInfo({
        'algorithm': {
            'algorithm': 'ec',
            'parameters': ecparams,
        },
        'public_key': ecpoint,
    }).dump()


def encode_ecdsa_signature(signature):
    """
    Encode a signature (generated by :meth:`pkcs11.SignMixin.sign`) into
    DER-encoded ASN.1 (ECDSA_Sig_Value) format.

    :param bytes signature: signature as bytes
    :rtype: bytes
    """

    part = len(signature) // 2
    r, s = signature[:part], signature[part:]

    asn1 = ECDSA_Sig_Value()
    asn1['r'] = int.from_bytes(r, byteorder='big')
    asn1['s'] = int.from_bytes(s, byteorder='big')

    return encoder.encode(asn1)


def decode_ecdsa_signature(der):
    """
    Decode a DER-encoded ASN.1 (ECDSA_Sig_Value) signature (as generated by
    OpenSSL/X.509) into PKCS #11 format.

    :param bytes der: DER-encoded signature
    :rtype bytes:
    """

    asn1, _ = decoder.decode(der, asn1Spec=ECDSA_Sig_Value())

    r = int(asn1['r'])
    s = int(asn1['s'])

    # r and s must be the same length
    length = (max(r.bit_length(), s.bit_length()) + 7) // 8
    return b''.join((
        r.to_bytes(length, byteorder='big'),
        s.to_bytes(length, byteorder='big'),
    ))
