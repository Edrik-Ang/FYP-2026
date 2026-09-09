"""
Field-level encryption for OAuth tokens stored in LinkedAccount
Encrypts on write, decrypts on read, transparently -- application code, 
(SteamService, GithubService, etc) always see plaintext in memory
Only DB column has ciphertext, DB compromised, data still safe.
"""


from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


class EncryptedCharField(models.CharField):
    def __init__(self, *args, **kwargs): 
        kwargs.setdefault('max_length', 1024) # Set a default max_length if not provided
        super().__init__(*args, **kwargs)
        self._fernet = Fernet(settings.FIELD_ENCRYPTION_KEY)        


    def get_prep_value(self, value): # encrypt text before saving to DB
        if value is None or value == '':
            return value
        if isinstance(value, str):
            value = value.encode('utf-8')
        return self._fernet.encrypt(value).decode('utf-8')

    def from_db_value(self, value, _expression, _connection): # decrypt text when reading from DB
        if value is None or value == '': 
            return value
        try:
            return self._fernet.decrypt(value.encode('utf-8')).decode('utf-8')
        except InvalidToken:
            raise ValueError(
            "Could not decrypt LinkedAccount token -- wrong"
            "FIELD_ENCRYPTION_KEY? Or legacy unencrypted data"
            "that needs a backfill migration first."
        )


    def to_python(self, value):
        return value
