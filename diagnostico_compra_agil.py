import os

import requests

from dotenv import load_dotenv


load_dotenv()


TICKET = os.getenv(
    "CHILECOMPRA_TICKET"
)


BASE_URL = (
    "https://api2.mercadopublico.cl"
)


ENDPOINT = (
    f"{BASE_URL}/v2/compra-agil"
)


HEADERS = {
    "ticket": TICKET,
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64)"
    ),
    "Accept": "application/json",
}


def probar(
    nombre,
    params,
):

    print(
        "\n"
        + "=" * 75
    )

    print(
        f"PRUEBA: {nombre}"
    )

    print(
        "PARAMETROS:"
    )

    for key, value in params.items():

        print(
            f"  {key}: {value}"
        )

    print(
        "-" * 75
    )

    try:

        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params,
            timeout=60,
        )

        print(
            f"HTTP: {response.status_code}"
        )

        print(
            f"URL FINAL: {response.url}"
        )

        if response.status_code != 200:

            print(
                "RESPUESTA:"
            )

            print(
                response.text[:1500]
            )

            return

        data = response.json()

        payload = (
            data.get(
                "payload",
                {},
            )
            or {}
        )

        items = (
            payload.get(
                "items",
                [],
            )
            or []
        )

        paginacion = (
            payload.get(
                "paginacion",
                {},
            )
            or {}
        )

        print(
            f"RESULTADOS: {len(items)}"
        )

        print(
            "PAGINACION:"
        )

        print(
            f"  total_resultados: "
            f"{paginacion.get('total_resultados')}"
        )

        print(
            f"  total_paginas: "
            f"{paginacion.get('total_paginas')}"
        )

        print(
            "\nRESULTADOS:"
        )

        for item in items[:20]:

            codigo = item.get(
                "codigo",
                "",
            )

            nombre_item = item.get(
                "nombre",
                "",
            )

            estado = (
                (
                    item.get(
                        "estado",
                        {},
                    )
                    or {}
                ).get(
                    "codigo"
                )
            )

            convocatoria = (
                (
                    item.get(
                        "convocatoria",
                        {},
                    )
                    or {}
                ).get(
                    "estado_convocatoria"
                )
            )

            fecha_cierre = (
                (
                    item.get(
                        "fechas",
                        {},
                    )
                    or {}
                ).get(
                    "fecha_cierre"
                )
            )

            fecha_publicacion = (
                (
                    item.get(
                        "fechas",
                        {},
                    )
                    or {}
                ).get(
                    "fecha_publicacion"
                )
            )

            monto = (
                (
                    item.get(
                        "montos",
                        {},
                    )
                    or {}
                ).get(
                    "monto_disponible_clp"
                )
            )

            print(
                f"  {codigo}"
            )

            print(
                f"     nombre: {nombre_item}"
            )

            print(
                f"     estado: {estado}"
            )

            print(
                f"     llamado: {convocatoria}"
            )

            print(
                f"     publicado: "
                f"{fecha_publicacion}"
            )

            print(
                f"     cierre: "
                f"{fecha_cierre}"
            )

            print(
                f"     monto CLP: "
                f"{monto}"
            )

    except Exception as e:

        print(
            f"ERROR: "
            f"{type(e).__name__}: {e}"
        )


if not TICKET:

    print(
        "❌ No existe "
        "CHILECOMPRA_TICKET."
    )

    raise SystemExit(1)


# ============================================================
# BÚSQUEDAS EXACTAS DE LAS COMPRAS QUE ENCONTRASTE
# ============================================================

probar(
    "ID 4280-359-COT26",
    {
        "id": "4280-359-COT26",
    },
)


probar(
    "ID 2759-596-COT26",
    {
        "id": "2759-596-COT26",
    },
)


# ============================================================
# BÚSQUEDAS POR PRODUCTO
# ============================================================

probar(
    "q=botas",
    {
        "q": "botas",
        "estado": "publicada",
        "tamano_pagina": 50,
        "numero_pagina": 1,
    },
)


probar(
    "q=chaleco",
    {
        "q": "chaleco",
        "estado": "publicada",
        "tamano_pagina": 50,
        "numero_pagina": 1,
    },
)


probar(
    "q=geologo",
    {
        "q": "geologo",
        "estado": "publicada",
        "tamano_pagina": 50,
        "numero_pagina": 1,
    },
)


probar(
    "q=tactica",
    {
        "q": "tactica",
        "estado": "publicada",
        "tamano_pagina": 50,
        "numero_pagina": 1,
    },
)


probar(
    "q=tactico",
    {
        "q": "tactico",
        "estado": "publicada",
        "tamano_pagina": 50,
        "numero_pagina": 1,
    },
)


probar(
    "q=antibalas",
    {
        "q": "antibalas",
        "estado": "publicada",
        "tamano_pagina": 50,
        "numero_pagina": 1,
    },
)


probar(
    "q=balistico",
    {
        "q": "balistico",
        "estado": "publicada",
        "tamano_pagina": 50,
        "numero_pagina": 1,
    },
)


# ============================================================
# PRUEBAS DE FRASES
# ============================================================

probar(
    "q=botas tacticas",
    {
        "q": "botas tacticas",
        "estado": "publicada",
        "tamano_pagina": 50,
        "numero_pagina": 1,
    },
)


probar(
    "q=chaleco antibalas",
    {
        "q": "chaleco antibalas",
        "estado": "publicada",
        "tamano_pagina": 50,
        "numero_pagina": 1,
    },
)


# ============================================================
# CAMBIO_DESDE / CAMBIO_HASTA
# ============================================================

probar(
    "cambio últimos 30 minutos",
    {
        "cambio_desde": (
            "2026-09-23T19:30:00Z"
        ),
        "cambio_hasta": (
            "2026-09-23T20:00:00Z"
        ),
        "estado": "publicada",
        "tamano_pagina": 50,
        "numero_pagina": 1,
    },
)


probar(
    "cambio últimas 2 horas",
    {
        "cambio_desde": (
            "2026-09-23T18:00:00Z"
        ),
        "cambio_hasta": (
            "2026-09-23T20:00:00Z"
        ),
        "estado": "publicada",
        "tamano_pagina": 50,
        "numero_pagina": 1,
    },
)


probar(
    "cambio últimas 6 horas",
    {
        "cambio_desde": (
            "2026-09-23T14:00:00Z"
        ),
        "cambio_hasta": (
            "2026-09-23T20:00:00Z"
        ),
        "estado": "publicada",
        "tamano_pagina": 50,
        "numero_pagina": 1,
    },
)


# ============================================================
# PRUEBA DE FECHA EXACTA
# 15/09/2026
# ============================================================

probar(
    "publicadas solo 15/09/2026",
    {
        "publicado_desde": (
            "2026-09-15T00:00:00Z"
        ),
        "publicado_hasta": (
            "2026-09-15T23:59:59Z"
        ),
        "tamano_pagina": 50,
        "numero_pagina": 1,
    },
)


print(
    "\n"
    + "=" * 75
)

print(
    "DIAGNOSTICO TERMINADO"
)

print(
    "=" * 75
)