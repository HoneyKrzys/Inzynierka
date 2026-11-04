from pydantic import BaseModel, Field, ConfigDict


class PodsumowanieWizyty(BaseModel):
    summary: str = Field(min_length=1, max_length=6000)


class Zalecenie(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=1500)
    sources: list[int] = Field(min_length=1, max_length=5)


class Propozycja(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str = Field(min_length=1, max_length=6000)
    recommendations: list[Zalecenie] = Field(default_factory=list, max_length=8)
    missing_information: list[str] = Field(default_factory=list, max_length=12)


class OcenaZakresu(BaseModel):
    model_config = ConfigDict(extra="forbid")
    all_problems_covered: bool
    uncertain: bool


class OcenaUzasadnienia(BaseModel):
    model_config = ConfigDict(extra="forbid")
    supported: bool
    applies_to_patient: bool
    non_pharmacological: bool
    uncertain: bool

