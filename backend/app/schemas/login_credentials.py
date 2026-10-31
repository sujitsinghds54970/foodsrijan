from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.utils.validators import validate_password_strength, validate_username


class LoginCredentialsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str | None = Field(default=None, max_length=30)
    reset_password: bool = False
    password: str | None = Field(default=None, max_length=72, repr=False)
    password_confirm: str | None = Field(default=None, max_length=72, repr=False)

    @model_validator(mode="after")
    def validate_changes(self):
        if "username" in self.model_fields_set:
            if self.username is None or not validate_username(self.username.strip()):
                raise ValueError("Username must be 4-30 alphanumeric characters or underscores")
            self.username = self.username.strip()
        if self.password is not None:
            valid, errors = validate_password_strength(self.password)
            if not valid:
                raise ValueError("; ".join(errors))
            if self.password != self.password_confirm:
                raise ValueError("Passwords do not match")
            if self.reset_password:
                raise ValueError("Choose either a custom password or a generated password")
        elif self.password_confirm is not None:
            raise ValueError("A password is required with password confirmation")
        if self.username is None and self.password is None and not self.reset_password:
            raise ValueError("Provide a username or reset the password")
        return self
