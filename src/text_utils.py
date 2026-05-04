import re
import unicodedata


COUNTRY_NAMES = {
    "AR": "Argentina",
    "BR": "Brasil",
    "CL": "Chile",
    "CO": "Colombia",
    "CR": "Costa Rica",
    "EC": "Ecuador",
    "MX": "Mexico",
    "PE": "Peru",
    "UY": "Uruguay",
}

ACRONYMS = {
    "AR",
    "BR",
    "CL",
    "CO",
    "CR",
    "EC",
    "MX",
    "PE",
    "UY",
    "AI",
    "ATC",
    "CVR",
    "FS",
    "GMV",
    "MLTV",
    "OP",
    "PRO",
    "PTC",
    "SS",
    "SST",
    "UE",
}


def remove_accents(value: object) -> str:
    """Remove accents and normalize whitespace from a text value."""
    if value is None:
        return ""

    text = str(value).strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[-_/]+", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def clean_text(value: object) -> str:
    """Create a readable canonical value for processed text fields."""
    text = remove_accents(value)
    words = []

    for word in text.split(" "):
        upper_word = word.upper()
        if upper_word in ACRONYMS:
            words.append(upper_word)
        elif word.replace(".", "", 1).isdigit():
            words.append(word)
        else:
            words.append(word.lower().capitalize())

    return " ".join(words).strip()


def normalize_code(value: object) -> str:
    """Create a compact uppercase code value."""
    return remove_accents(value).upper()


def country_name_from_code(country_code: object) -> str:
    """Map Rappi country codes to readable country names."""
    code = normalize_code(country_code)
    return COUNTRY_NAMES.get(code, code)
