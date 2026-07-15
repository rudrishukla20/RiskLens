import hashlib
from typing import BinaryIO


def calculate_sha256(file_obj: BinaryIO, chunk_size: int = 65536) -> str:
    """
    Computes a SHA256 hex digest checksum for a file-like stream object.
    Reads the file in chunks to prevent loading large datasets completely into memory.
    """
    sha256 = hashlib.sha256()

    # Seek to start if object has seek attribute
    if hasattr(file_obj, "seek"):
        file_obj.seek(0)

    while True:
        data = file_obj.read(chunk_size)
        if not data:
            break
        sha256.update(data)

    # Reset seek if object has seek attribute
    if hasattr(file_obj, "seek"):
        file_obj.seek(0)

    return sha256.hexdigest()
