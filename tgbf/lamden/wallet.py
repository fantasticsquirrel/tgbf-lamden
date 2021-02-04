import nacl
import nacl.encoding
import nacl.exceptions
import nacl.signing
import secrets


def verify(address: str, message: str, signature: str):
    address = bytes.fromhex(address)
    message = message.encode()
    signature = bytes.fromhex(signature)

    vk = nacl.signing.VerifyKey(address)

    try:
        vk.verify(message, signature)
    except nacl.exceptions.BadSignatureError:
        return False
    return True


# TODO: If i use 'lamden' module, do i still need 'pynacl' as a dependency?
class LamdenWallet:
    def __init__(self, seed=None):
        if isinstance(seed, str):
            seed = bytes.fromhex(seed)
        if seed is None:
            seed = secrets.token_bytes(32)

        self.sk = nacl.signing.SigningKey(seed=seed)
        self.vk = self.sk.verify_key

    def sign(self, msg: str):
        sig = self.sk.sign(msg.encode())
        return sig.signature.hex()

    @property
    def address(self):
        return self.vk.encode().hex()

    @property
    def privkey(self):
        return self.sk.encode().hex()
