from dataclasses import dataclass


@dataclass(slots=True)
class Citation:
    source_file: str
    fiscal_year: str
    section: str
    paragraph_id: str
    quote_en: str
