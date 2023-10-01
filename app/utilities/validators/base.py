import re

mobile_format = re.compile("""^(\+\d{1,3}[- ]?)?\d{10}$""")
email_format = re.compile(
            r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"
            r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-011\013\014\016-\177])*"'
            r')@(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,10}\.?$', re.IGNORECASE)


def validate_email(email: str) -> bool:
    for email in email.split(','):
        if not email_format.match(email.strip()):
            return False
    return True


def validate_mobile(mobile: str) -> bool:
    if mobile_format.match(mobile):
        return True
    return False
