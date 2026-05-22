"""
AERO BOT PRO — Módulo BingX
Gestión de órdenes, balance y estado de posiciones.
Conéctalo poniendo api_key y api_secret en config.json.
"""

import json
import ccxt

_CFG_PATH = "config.json"


def _cargar_config():
    with open(_CFG_PATH, "r") as f:
        return json.load(f)


def _exchange():
    cfg = _cargar_config()
    ex = ccxt.bingx({
        "apiKey":  cfg.get("api_key")    or "",
        "secret":  cfg.get("api_secret") or "",
        "enableRateLimit": True,
    })
    return ex


def verificar_balance():
    """Retorna el balance de USDT disponible, o None si falla."""
    try:
        b = _exchange().fetch_balance()
        return float(b["USDT"]["free"])
    except Exception as e:
        return None, str(e)


def colocar_orden(simbolo, lado, cantidad_usdt, apalancamiento=10, modo="demo"):
    """
    lado: 'long' | 'short'
    modo: 'demo' (paper) | 'real'
    Retorna dict con resultado o error.
    """
    if modo == "demo":
        return {
            "status": "demo",
            "simbolo": simbolo,
            "lado": lado,
            "usdt": cantidad_usdt,
            "apalancamiento": apalancamiento,
        }

    try:
        ex = _exchange()
        ex.set_leverage(apalancamiento, simbolo)
        tipo_lado = "buy" if lado == "long" else "sell"
        ticker    = ex.fetch_ticker(simbolo)
        precio    = float(ticker["last"])
        cantidad  = (cantidad_usdt * apalancamiento) / precio
        orden     = ex.create_market_order(simbolo, tipo_lado, cantidad)
        return {"status": "ok", "orden": orden}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}


def cerrar_posicion(simbolo, lado):
    """Cierra una posición abierta en BingX."""
    try:
        ex       = _exchange()
        pos      = ex.fetch_positions([simbolo])
        for p in pos:
            if p["symbol"] == simbolo and p["side"] == lado:
                tipo_cierre = "sell" if lado == "long" else "buy"
                cantidad    = abs(float(p["contracts"]))
                orden = ex.create_market_order(
                    simbolo, tipo_cierre, cantidad,
                    params={"reduceOnly": True},
                )
                return {"status": "ok", "orden": orden}
        return {"status": "sin_posicion"}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}
