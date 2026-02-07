"""AMAR configuration management."""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Dict


COUNTRY_CODES: Dict[str, str] = {
    "al": "Albania", "dz": "Algeria", "ao": "Angola", "ai": "Anguilla",
    "ag": "Antigua and Barbuda", "ar": "Argentina", "am": "Armenia",
    "au": "Australia", "at": "Austria", "az": "Azerbaijan", "bs": "Bahamas",
    "bh": "Bahrain", "bb": "Barbados", "by": "Belarus", "be": "Belgium",
    "bz": "Belize", "bj": "Benin", "bm": "Bermuda", "bt": "Bhutan",
    "bo": "Bolivia", "bw": "Botswana", "br": "Brazil", "vg": "British Virgin Islands",
    "bn": "Brunei Darussalam", "bg": "Bulgaria", "bf": "Burkina-Faso",
    "kh": "Cambodia", "ca": "Canada", "cv": "Cape Verde", "ky": "Cayman Islands",
    "td": "Chad", "cl": "Chile", "cn": "China", "co": "Colombia", "cr": "Costa Rica",
    "hr": "Croatia", "cy": "Cyprus", "cz": "Czech Republic",
    "cg": "Democratic Republic of the Congo", "dk": "Denmark", "dm": "Dominica",
    "do": "Dominican Republic", "ec": "Ecuador", "eg": "Egypt", "sv": "El Salvador",
    "ee": "Estonia", "fm": "Federated States of Micronesia", "fj": "Fiji",
    "fi": "Finland", "fr": "France", "gm": "Gambia", "de": "Germany", "gh": "Ghana",
    "gb": "Great Britain", "gr": "Greece", "gd": "Grenada", "gt": "Guatemala",
    "gw": "Guinea Bissau", "gy": "Guyana", "hn": "Honduras", "hk": "Hong Kong",
    "hu": "Hungary", "is": "Iceland", "in": "India", "id": "Indonesia",
    "ie": "Ireland", "il": "Israel", "it": "Italy", "jm": "Jamaica", "jp": "Japan",
    "jo": "Jordan", "kz": "Kazakhstan", "ke": "Kenya", "kg": "Kyrgyzstan",
    "kw": "Kuwait", "la": "Laos", "lv": "Latvia", "lb": "Lebanon", "lr": "Liberia",
    "lt": "Lithuania", "lu": "Luxembourg", "mo": "Macau", "mk": "Macedonia",
    "mg": "Madagascar", "mw": "Malawi", "my": "Malaysia", "ml": "Mali", "mt": "Malta",
    "mr": "Mauritania", "mu": "Mauritius", "mx": "Mexico", "md": "Moldova",
    "mn": "Mongolia", "ms": "Montserrat", "mz": "Mozambique", "na": "Namibia",
    "np": "Nepal", "nl": "Netherlands", "nz": "New Zealand", "ni": "Nicaragua",
    "ne": "Niger", "ng": "Nigeria", "no": "Norway", "om": "Oman", "pk": "Pakistan",
    "pw": "Palau", "pa": "Panama", "pg": "Papua New Guinea", "py": "Paraguay",
    "pe": "Peru", "ph": "Philippines", "pl": "Poland", "pt": "Portugal", "qa": "Qatar",
    "tt": "Republic of Trinidad and Tobago", "ro": "Romania", "ru": "Russia",
    "kn": "Saint Kitts and Nevis", "lc": "Saint Lucia",
    "vc": "Saint Vincent and the Grenadines", "st": "Sao Tome e Principe",
    "sa": "Saudi Arabia", "sn": "Senegal", "sc": "Seychelles", "sl": "Sierra Leone",
    "sg": "Singapore", "sk": "Slovakia", "si": "Slovenia", "sb": "Solomon Islands",
    "za": "South Africa", "kr": "South Korea", "es": "Spain", "lk": "Sri Lanka",
    "sr": "Suriname", "sz": "Swaziland", "se": "Sweden", "ch": "Switzerland",
    "tw": "Taiwan", "tj": "Tajikistan", "tz": "Tanzania", "th": "Thailand",
    "tn": "Tunisia", "tr": "Turkey", "tm": "Turkmenistan", "tc": "Turks and Caicos Islands",
    "ug": "Uganda", "ua": "Ukraine", "ae": "United Arab Emirates",
    "us": "United States of America", "uy": "Uruguay", "uz": "Uzbekistan",
    "ve": "Venezuela", "vn": "Vietnam", "ye": "Yemen", "zw": "Zimbabwe",
}

# Persistent fields saved/loaded from JSON config
_SAVEABLE_FIELDS = {
    "storefront", "save_path", "max_concurrency", "rate_limit",
    "chunk_size", "retry_max", "cache_ttl", "theme",
}


@dataclass
class AMARConfig:
    token: str = ""
    storefront: str = "us"
    save_path: str = ""
    max_concurrency: int = 10
    rate_limit: float = 18.0
    chunk_size: int = 65536  # 64 KB
    retry_max: int = 3
    cache_ttl: int = 300  # seconds
    theme: str = "dark"  # "dark" or "light"
    base_path: str = field(default="", repr=False)

    @classmethod
    def load(cls, base_path: str) -> "AMARConfig":
        config = cls(base_path=base_path)

        # Load persisted settings
        config_file = os.path.join(base_path, "amar_config.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, "r") as f:
                    data = json.load(f)
                for key, value in data.items():
                    if key in _SAVEABLE_FIELDS and hasattr(config, key):
                        setattr(config, key, value)
            except (json.JSONDecodeError, OSError):
                pass

        # Load token from token.txt
        token_file = os.path.join(base_path, "token.txt")
        if os.path.exists(token_file):
            try:
                with open(token_file, "r") as f:
                    config.token = f.read().strip()
            except OSError:
                pass

        # Load saved destination path
        dest_file = os.path.join(base_path, "dest.path")
        if os.path.exists(dest_file) and not config.save_path:
            try:
                with open(dest_file, "r") as f:
                    path = f.readline().strip()
                if os.path.isdir(path):
                    config.save_path = path
            except OSError:
                pass

        return config

    def save(self) -> None:
        config_file = os.path.join(self.base_path, "amar_config.json")
        data = {k: getattr(self, k) for k in _SAVEABLE_FIELDS}
        with open(config_file, "w") as f:
            json.dump(data, f, indent=2)

        # Also persist dest.path for backward compatibility
        if self.save_path:
            dest_file = os.path.join(self.base_path, "dest.path")
            with open(dest_file, "w") as f:
                f.write(self.save_path)

    def save_token(self, token: str) -> None:
        self.token = token
        token_file = os.path.join(self.base_path, "token.txt")
        with open(token_file, "w") as f:
            f.write(token)

    @property
    def api_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://music.apple.com/",
            "Origin": "https://music.apple.com",
            "Accept": "*/*",
        }
