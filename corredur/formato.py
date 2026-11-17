def eur(v):
    if v is None:
        return "—"
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"

def fecha(v):
    return f"{v[8:10]}/{v[5:7]}/{v[0:4]}" if v and len(v) >= 10 else (v or "—")
