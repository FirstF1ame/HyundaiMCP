from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class NavigationSnapshot(BaseModel):
    """Bridge contract. Units are meters/seconds; UTC observation time is required."""

    # 계약에 없는 필드를 거부해 잘못된 Bridge 응답을 조기에 발견한다.
    model_config = ConfigDict(extra="forbid")
    # source는 Bridge가 보고하는 출처이며 실제 하드웨어 연결을 증명하지 않는다.
    source: Literal["pleos_sdk", "mock_bridge"]
    status: Literal["ok", "no_destination", "sdk_error", "unsupported"]
    # 시간대가 있는 조회 시각. 서버는 이 값으로 데이터 신선도를 판단한다.
    observed_at: AwareDatetime
    destination_name: str | None = Field(default=None, max_length=200)
    # 거리=m, 시간=초. 음수 및 문자열/실수의 정수 자동 변환을 허용하지 않는다.
    remaining_distance_m: int | None = Field(default=None, ge=0, strict=True)
    remaining_duration_s: int | None = Field(default=None, ge=0, strict=True)

    # 성공 응답에는 세 내비게이션 값이 모두 필요하고, 오류 응답에는 모두 없어야 한다.
    @model_validator(mode="after")
    def valid_state(self):
        values = (self.destination_name, self.remaining_distance_m, self.remaining_duration_s)
        if self.status == "ok":
            if any(v is None for v in values) or not self.destination_name.strip():
                raise ValueError("ok requires destination name, distance and duration")
        elif any(v is not None for v in values):
            raise ValueError("non-ok results must not contain navigation values")
        return self


# POST /bridge/results의 본문: 명령 식별자와 검증할 내비게이션 스냅샷.
class BridgeResult(BaseModel):
    # 계약에 없는 필드를 거부해 잘못된 Bridge 응답을 조기에 발견한다.
    model_config = ConfigDict(extra="forbid")
    command_id: str = Field(min_length=36, max_length=36)
    result: NavigationSnapshot
