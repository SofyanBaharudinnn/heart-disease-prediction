import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

class NumberValidator:
    def validate(self, password, user=None):
        if not re.search(r'[0-9]', password):
            raise ValidationError(
                _("Kata sandi harus mengandung setidaknya satu angka."),
                code='password_no_number',
            )

    def get_help_text(self):
        return _("Kata sandi harus mengandung setidaknya satu angka.")
