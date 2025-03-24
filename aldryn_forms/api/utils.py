from typing import Dict


dataType = Dict[str, str]


def remove_identical_value(rule: dataType, src: dataType, dest: dataType) -> None:
    """Remove value if it is identical to another."""
    data = [dest.get(key) for key in rule.get("params", {}).get("fields", [])]
    if len(set(data)) < len(data) and rule["dest"] in dest:
        del dest[rule["dest"]]
