from django.contrib.auth.hashers import PBKDF2PasswordHasher
from .settings import PBKDF2_ITERATION


class MyPBKDF2PasswordHasher(PBKDF2PasswordHasher):
    """
    A subclass of PBKDF2PasswordHasher that uses 100 times more iterations.
    """

    iterations = PBKDF2_ITERATION
