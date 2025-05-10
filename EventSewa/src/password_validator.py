import re


def validate_password(password):
    # Check the length of the password
    if len(password) < 8:
        return "Password must be at least 8 characters long."

    # Check for at least one uppercase letter
    if not any(char.isupper() for char in password):
        return "Password must contain at least one uppercase letter."

    # Check for at least one lowercase letter
    if not any(char.islower() for char in password):
        return "Password must contain at least one lowercase letter."

    # Check for at least one digit
    if not any(char.isdigit() for char in password):
        return "Password must contain at least one number."

    # Check for at least one special character
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return "Password must contain at least one special character."

    return "Password is valid."


# Example usage
password = input("Enter a password to validate: ")
print(validate_password(password))
