import hashlib
from typing import Optional, Tuple


HASHING_SECRET = "default-secret-should-be-changed" # A secret key used to securely hash account numbers.

# This is a placeholder for your actual proxy resolution logic.
def proxy_resolve(proxy_id: str, proxy_type: str) -> Tuple[str, str]:
    """Resolves a proxy ID to a financial institution code and account number."""
    # In a real implementation, this would look up the proxy in a database or service.
    print(f"Resolving proxy '{proxy_id}' of type '{proxy_type}'...")
    return (f"fi_for_{proxy_type}", f"account_for_{proxy_id}")

def hash_with_secret(text: str, secret: str) -> str:
    """
    Hashes a string with a secret pepper using SHA-256.

    Args:
        text: The input string to hash (e.g., an account number).
        secret: The secret pepper to include in the hash.

    Returns:
        The hexadecimal representation of the hash.
    """
    combined = f"{text}|{secret}"
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()

def construct_correlation_id(
    sender_proxy_id: str,
    receiver_proxy_id: str,
    timestamp: str,
    amount: str,
    sender_fi_code: Optional[str] = None,
    receiver_fi_code: Optional[str] = None,
    sender_proxy_type: str = 'account',
    receiver_proxy_type: str = 'account',
) -> str:
    """
    Constructs a short, unique correlation ID for a transaction.

    Args:
        sender_proxy_id: The sender's proxy ID (e.g., account number, phone).
        receiver_proxy_id: The receiver's proxy ID.
        timestamp: ISO 8601 formatted timestamp of the transaction.
        amount: The transaction amount.
        sender_fi_code: The sender's financial institution code. Required if proxy type is 'account'.
        receiver_fi_code: The receiver's financial institution code. Required if proxy type is 'account'.
        sender_proxy_type: The type of the sender's proxy.
        receiver_proxy_type: The type of the receiver's proxy.

    Returns:
        A 18-character hexadecimal correlation ID.

    Raises:
        ValueError: If an FI code is missing for an 'account' proxy type.
    """
    if (sender_proxy_type == 'account' and not sender_fi_code) or \
       (receiver_proxy_type == 'account' and not receiver_fi_code):
        raise ValueError("Financial institution code is required for 'account' proxy types.")

    if sender_proxy_type == 'account':
        sender_account_number = sender_proxy_id
    else:
        sender_fi_code, sender_account_number = proxy_resolve(sender_proxy_id, sender_proxy_type)

    if receiver_proxy_type == 'account':
        receiver_account_number = receiver_proxy_id
    else:
        receiver_fi_code, receiver_account_number = proxy_resolve(receiver_proxy_id, receiver_proxy_type)

    # Securely hash the account numbers with the secret
    sender_account_hash = hash_with_secret(sender_account_number, HASHING_SECRET)
    receiver_account_hash = hash_with_secret(receiver_account_number, HASHING_SECRET)

    # Combine all unique components of the transaction into a single string.
    # Using a separator (like '|') helps prevent ambiguity.
    combined_string = "|".join([
        str(sender_fi_code), sender_account_hash,
        str(receiver_fi_code), receiver_account_hash,
        str(timestamp), str(amount)
    ])

    # Hash the combined string using SHA-256 and encode it to bytes.
    hasher = hashlib.sha256(combined_string.encode('utf-8'))
    # Take the first 18 characters from the hexadecimal representation of the hash.
    correlation_id = hasher.hexdigest()[:18]

    return correlation_id
