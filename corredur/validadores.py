import re

_LETRAS_DNI = "TRWAGMYFPDXBNJZSQVHLCKE"

def nif_valido(valor):
    """Valida DNI, NIE y CIF españoles (letra o dígito de control)."""
    if not valor:
        return False
    v = re.sub(r"[\s\-\.]", "", str(valor)).upper()
    if re.fullmatch(r"\d{8}[A-Z]", v):                       # DNI
        return _LETRAS_DNI[int(v[:8]) % 23] == v[8]
    if re.fullmatch(r"[XYZ]\d{7}[A-Z]", v):                  # NIE
        n = int("XYZ".index(v[0]).__str__() + v[1:8])
        return _LETRAS_DNI[n % 23] == v[8]
    if re.fullmatch(r"[ABCDEFGHJNPQRSUVW]\d{7}[0-9A-J]", v):  # CIF
        d = v[1:8]
        impares = sum(sum(divmod(int(d[i]) * 2, 10)) for i in (0, 2, 4, 6))
        pares = sum(int(d[i]) for i in (1, 3, 5))
        control = (10 - (impares + pares) % 10) % 10
        letra = "JABCDEFGHI"[control]
        c = v[8]
        if v[0] in "PQRSNW":
            return c == letra
        if v[0] in "ABEH":
            return c == str(control)
        return c in (str(control), letra)
    return False

def email_valido(valor):
    if not valor:
        return False
    return re.fullmatch(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}", str(valor).strip()) is not None

def movil_valido(valor):
    """Móvil español: 9 dígitos que empiezan por 6 o 7 (con o sin +34)."""
    if not valor:
        return False
    d = re.sub(r"[\s\-\.\(\)]", "", str(valor))
    d = re.sub(r"^(\+34|0034)", "", d)
    return re.fullmatch(r"[67]\d{8}", d) is not None
