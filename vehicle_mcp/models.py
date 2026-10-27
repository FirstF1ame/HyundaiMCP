from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class NavigationSnapshot(BaseModel):
    """Bridge contract. Units are meters/seconds; UTC observation time is required."""

    model_config = ConfigDict(extra="forbid")
    source: Literal["pleos_sdk", "mock_bridge"]
    status: Literal["ok", "no_destination", "sdk_error", "unsupported"]
    observed_at: AwareDatetime
    destination_name: str | None = Field(default=None, max_length=200)
    remaining_distance_m: int | None = Field(default=None, ge=0, strict=True)
    remaining_duration_s: int | None = Field(default=None, ge=0, strict=True)

    @model_validator(mode="after")
    def valid_state(self):
        values = (self.destination_name, self.remaining_distance_m, self.remaining_duration_s)
        if self.status == "ok":
            if any(v is None for v in values) or not self.destination_name.strip():
                raise ValueError("ok requires destination name, distance and duration")
        elif any(v is not None for v in values):
            raise ValueError("non-ok results must not contain navigation values")
        return self


class BridgeResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command_id: str = Field(min_length=36, max_length=36)
    result: NavigationSnapshot
