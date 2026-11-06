import re
from typing import Optional, Tuple


class ValidationService:
    """
    Validates domain names according to RFC 1035 and RFC 1123 specifications.
    """

    # Label pattern: alphanumeric and hyphens, 1-63 chars, cannot start/end with hyphen
    LABEL_PATTERN = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$", re.IGNORECASE)

    @classmethod
    def sanitize_input(cls, raw_input: str) -> str:
        """
        Cleans user input by stripping protocols, paths, query params, and leading/trailing spaces.
        """
        if not raw_input:
            return ""

        cleaned = raw_input.strip().lower()
        # Remove schemes
        cleaned = re.sub(r"^https?://", "", cleaned)
        # Remove www.
        cleaned = re.sub(r"^www\.", "", cleaned)
        # Remove path, query string or hash
        cleaned = cleaned.split("/")[0].split("?")[0].split("#")[0]
        # Remove trailing dot if any
        cleaned = cleaned.rstrip(".")
        return cleaned

    @classmethod
    def parse_and_validate(cls, raw_input: str) -> Tuple[bool, str, Optional[str], Optional[str]]:
        """
        Parses input into (is_valid, sld_name, explicit_tld, error_message).
        
        Examples:
        - "tala" -> (True, "tala", None, None)
        - "tala.dev" -> (True, "tala", ".dev", None)
        - "-invalid" -> (False, "-invalid", None, "Domain label cannot start or end with a hyphen.")
        - "a" * 64 -> (False, "...", None, "Domain name is too long (maximum 63 characters).")
        """
        cleaned = cls.sanitize_input(raw_input)

        if not cleaned:
            return False, "", None, "Domain name cannot be empty."

        # Check total length
        if len(cleaned) > 253:
            return False, cleaned, None, "Full domain name cannot exceed 253 characters."

        if ".." in cleaned:
            return False, cleaned, None, "Domain name cannot contain consecutive dots."

        # Check if user entered an extension (e.g. "tala", "tala.gy", "myshop.com", "app.in")
        parts = cleaned.split(".")
        if any(len(p) == 0 for p in parts):
            return False, cleaned, None, "Domain label cannot be empty."

        if len(parts) > 1:
            sld = parts[0]
            explicit_tld = "." + ".".join(parts[1:])
            # Validate TLD parts
            for tld_part in parts[1:]:
                if not cls.LABEL_PATTERN.match(tld_part):
                    return False, sld, explicit_tld, f"Invalid domain extension label: '{tld_part}'."
        else:
            sld = parts[0]
            explicit_tld = None

        # Validate SLD (Second-Level Domain)
        if len(sld) == 0:
            return False, cleaned, None, "Domain name label cannot be empty."

        if len(sld) > 63:
            return False, sld, explicit_tld, f"Domain label '{sld}' exceeds maximum allowed length of 63 characters."

        if sld.startswith("-") or sld.endswith("-"):
            return False, sld, explicit_tld, "Domain name cannot start or end with a hyphen."

        if not cls.LABEL_PATTERN.match(sld):
            # Detailed error reason
            if re.search(r"[^a-z0-9-]", sld):
                invalid_chars = set(re.findall(r"[^a-z0-9-]", sld))
                return False, sld, explicit_tld, f"Domain contains invalid characters: {' '.join(invalid_chars)}. Only alphanumeric and hyphens are allowed."
            return False, sld, explicit_tld, "Invalid domain name syntax."

        return True, sld, explicit_tld, None
