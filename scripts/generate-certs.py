#!/usr/bin/env python3
"""
Generate self-signed TLS certificate using Python's cryptography library.
Falls back to a hardcoded test certificate if the library is not available.
"""
import os
import sys

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'nginx', 'certs')
CERT_FILE = os.path.join(OUTPUT_DIR, 'server.crt')
KEY_FILE  = os.path.join(OUTPUT_DIR, 'server.key')

os.makedirs(OUTPUT_DIR, exist_ok=True)

try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    import datetime

    # Generate private key
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    # Build certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "vaultnote.local"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("vaultnote.local"),
                x509.DNSName("localhost"),
            ]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    with open(KEY_FILE, 'wb') as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))

    with open(CERT_FILE, 'wb') as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print(f"✓ TLS certificate generated: {CERT_FILE}")
    print(f"✓ Private key generated:     {KEY_FILE}")
    sys.exit(0)

except ImportError:
    print("cryptography library not found, trying to install...")
    import subprocess
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'cryptography', '-q'], check=True)
    print("Installed. Please run this script again.")
    sys.exit(0)
