"""Configuration management for AMAR v3."""

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path.home() / ".amar"
CONFIG_FILE = CONFIG_DIR / "config.json"
TOKEN_FILE = CONFIG_DIR / "token.txt"
HISTORY_FILE = CONFIG_DIR / "history.json"
FAVORITES_FILE = CONFIG_DIR / "favorites.json"

STOREFRONTS = {
    "dz": "Algeria", "ao": "Angola", "ai": "Anguilla", "ag": "Antigua and Barbuda",
    "ar": "Argentina", "am": "Armenia", "au": "Australia", "at": "Austria",
    "az": "Azerbaijan", "bs": "Bahamas", "bh": "Bahrain", "bb": "Barbados",
    "by": "Belarus", "be": "Belgium", "bz": "Belize", "bj": "Benin",
    "bm": "Bermuda", "bt": "Bhutan", "bo": "Bolivia", "bw": "Botswana",
    "br": "Brazil", "vg": "British Virgin Islands", "bn": "Brunei", "bg": "Bulgaria",
    "bf": "Burkina Faso", "kh": "Cambodia", "cm": "Cameroon", "ca": "Canada",
    "cv": "Cape Verde", "ky": "Cayman Islands", "td": "Chad", "cl": "Chile",
    "cn": "China mainland", "co": "Colombia", "cg": "Congo", "cr": "Costa Rica",
    "hr": "Croatia", "cy": "Cyprus", "cz": "Czech Republic", "ci": "Cote d'Ivoire",
    "dk": "Denmark", "dm": "Dominica", "do": "Dominican Republic", "ec": "Ecuador",
    "eg": "Egypt", "sv": "El Salvador", "ee": "Estonia", "sz": "Eswatini",
    "fj": "Fiji", "fi": "Finland", "fr": "France", "ga": "Gabon",
    "gm": "Gambia", "ge": "Georgia", "de": "Germany", "gh": "Ghana",
    "gr": "Greece", "gd": "Grenada", "gt": "Guatemala", "gw": "Guinea-Bissau",
    "gy": "Guyana", "hn": "Honduras", "hk": "Hong Kong", "hu": "Hungary",
    "is": "Iceland", "in": "India", "id": "Indonesia", "iq": "Iraq",
    "ie": "Ireland", "il": "Israel", "it": "Italy", "jm": "Jamaica",
    "jp": "Japan", "jo": "Jordan", "kz": "Kazakhstan", "ke": "Kenya",
    "kr": "Korea, Republic of", "xk": "Kosovo", "kw": "Kuwait", "kg": "Kyrgyzstan",
    "la": "Lao", "lv": "Latvia", "lb": "Lebanon", "lr": "Liberia",
    "ly": "Libya", "lt": "Lithuania", "lu": "Luxembourg", "mo": "Macao",
    "mg": "Madagascar", "mw": "Malawi", "my": "Malaysia", "mv": "Maldives",
    "ml": "Mali", "mt": "Malta", "mr": "Mauritania", "mu": "Mauritius",
    "mx": "Mexico", "fm": "Micronesia", "md": "Moldova", "mn": "Mongolia",
    "me": "Montenegro", "ms": "Montserrat", "ma": "Morocco", "mz": "Mozambique",
    "mm": "Myanmar", "na": "Namibia", "nr": "Nauru", "np": "Nepal",
    "nl": "Netherlands", "nz": "New Zealand", "ni": "Nicaragua", "ne": "Niger",
    "ng": "Nigeria", "mk": "North Macedonia", "no": "Norway", "om": "Oman",
    "pk": "Pakistan", "pw": "Palau", "pa": "Panama", "pg": "Papua New Guinea",
    "py": "Paraguay", "pe": "Peru", "ph": "Philippines", "pl": "Poland",
    "pt": "Portugal", "qa": "Qatar", "ro": "Romania", "ru": "Russia",
    "rw": "Rwanda", "sa": "Saudi Arabia", "sn": "Senegal", "rs": "Serbia",
    "sc": "Seychelles", "sl": "Sierra Leone", "sg": "Singapore", "sk": "Slovakia",
    "si": "Slovenia", "sb": "Solomon Islands", "za": "South Africa", "es": "Spain",
    "lk": "Sri Lanka", "kn": "St. Kitts and Nevis", "lc": "St. Lucia",
    "vc": "St. Vincent and the Grenadines", "sr": "Suriname", "se": "Sweden",
    "ch": "Switzerland", "tw": "Taiwan", "tj": "Tajikistan", "tz": "Tanzania",
    "th": "Thailand", "to": "Tonga", "tt": "Trinidad and Tobago", "tn": "Tunisia",
    "tr": "Turkiye", "tm": "Turkmenistan", "tc": "Turks and Caicos Islands",
    "ug": "Uganda", "ua": "Ukraine", "ae": "United Arab Emirates",
    "gb": "United Kingdom", "us": "United States", "uy": "Uruguay",
    "uz": "Uzbekistan", "vu": "Vanuatu", "ve": "Venezuela", "vn": "Vietnam",
    "ye": "Yemen", "zw": "Zimbabwe",
}


@dataclass
class AMARConfig:
    storefront: str = "us"
    save_path: str = ""
    max_concurrency: int = 10
    rate_limit: float = 18.0
    chunk_size: int = 65536
    retry_max: int = 3
    cache_ttl: int = 300
    theme: str = "dark"
    auto_organize: bool = True
    download_artwork: bool = True
    download_editorial: bool = True
    download_videos: bool = True
    download_metadata: bool = True
    artwork_size: int = 3000
    include_all_storefronts: bool = False

    def __post_init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if not self.save_path:
            self.save_path = str(Path.home() / "AMAR Downloads")

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls) -> "AMARConfig":
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    data = json.load(f)
                valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
                filtered = {k: v for k, v in data.items() if k in valid_fields}
                return cls(**filtered)
            except (json.JSONDecodeError, TypeError):
                pass
        config = cls()
        config.save()
        return config

    @property
    def token(self) -> Optional[str]:
        if TOKEN_FILE.exists():
            return TOKEN_FILE.read_text().strip()
        old_token = Path("token.txt")
        if old_token.exists():
            t = old_token.read_text().strip()
            self.token = t
            return t
        return None

    @token.setter
    def token(self, value: str):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(value.strip())

    @property
    def api_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Origin": "https://music.apple.com",
            "Referer": "https://music.apple.com/",
        }

    @property
    def storefront_name(self) -> str:
        return STOREFRONTS.get(self.storefront, "Unknown")
