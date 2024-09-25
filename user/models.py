from django.contrib.auth.models import AbstractUser


class User(AbstractUser):

    def get_engineer_or_none(self):
        try:
            return getattr(self, "engineer")
        except Exception:
            return None

    class Meta:
        db_table = "users"
