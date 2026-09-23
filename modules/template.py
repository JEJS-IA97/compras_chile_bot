# modules/template.py

import os

from datetime import datetime

from zoneinfo import ZoneInfo


CL_TZ = ZoneInfo(
    "America/Santiago"
)


CATEGORY_CONFIG = {
    "induwork": {
        "primary_color": "#f3901e",
        "banner": "induwork.jpg",
        "titulo_general": "LICITACIONES",
        "empresa": "Induwork",
        "logo_clave": "INDUWORK",
    },

    "coimsa": {
        "primary_color": "#054075",
        "banner": "coimsa.jpg",
        "titulo_general": "LICITACIONES",
        "empresa": "Coimsa",
        "logo_clave": "COIMSASPA",
    },

    "especial": {
        "primary_color": "#c29f63",
        "banner": "inversiones.jpg",
        "titulo_general": "LICITACIONES",
        "empresa": "MVI",
        "logo_clave": "MVI",
    },
}


BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)


ASSETS_DIR = os.path.join(
    BASE_DIR,
    "src",
    "assets",
    "images",
)


BANNERS_DIR = os.path.join(
    ASSETS_DIR,
    "banners",
)


def _get_banner_path(
    categoria: str,
) -> str:

    config = CATEGORY_CONFIG.get(
        categoria
    )

    if not config:
        return ""

    banner_name = config[
        "banner"
    ]

    banner_path = os.path.join(
        BANNERS_DIR,
        banner_name,
    )

    if os.path.exists(
        banner_path
    ):
        return banner_path

    if os.path.exists(
        BANNERS_DIR
    ):

        for fname in os.listdir(
            BANNERS_DIR
        ):

            normalizado = (
                fname
                .lower()
                .replace(
                    " ",
                    ""
                )
            )

            if (
                banner_name.lower()
                in normalizado
            ):

                return os.path.join(
                    BANNERS_DIR,
                    fname,
                )

    return ""


def _get_logo_path(
    clave: str,
) -> str:

    if not os.path.isdir(
        ASSETS_DIR
    ):
        return ""

    for fname in os.listdir(
        ASSETS_DIR
    ):

        ruta = os.path.join(
            ASSETS_DIR,
            fname,
        )

        if os.path.isdir(
            ruta
        ):
            continue

        normalizado = (
            fname
            .lower()
            .replace(
                " ",
                ""
            )
        )

        if (
            clave.lower()
            in normalizado
        ):

            return ruta

    return ""


def _formatear_fecha_cierre(
    valor,
) -> str:

    if not valor:
        return "Sin fecha"

    if isinstance(
        valor,
        datetime,
    ):

        fecha = valor

        if fecha.tzinfo is not None:

            fecha = fecha.astimezone(
                CL_TZ
            )

        return fecha.strftime(
            "%d/%m/%Y %H:%M"
        )

    if isinstance(
        valor,
        str,
    ):

        valor = valor.strip()

        if not valor:
            return "Sin fecha"

        try:

            fecha = datetime.fromisoformat(
                valor.replace(
                    "Z",
                    "+00:00",
                )
            )

            if fecha.tzinfo is not None:

                fecha = fecha.astimezone(
                    CL_TZ
                )

            return fecha.strftime(
                "%d/%m/%Y %H:%M"
            )

        except ValueError:

            pass

        formatos = (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
        )

        for formato in formatos:

            try:

                fecha = datetime.strptime(
                    valor,
                    formato,
                )

                return fecha.strftime(
                    "%d/%m/%Y %H:%M"
                )

            except ValueError:

                continue

        return valor

    return str(
        valor
    )


def generar_html_correo(
    categoria: str,
    licitaciones: list,
    es_alerta_urgente: bool = False,
    cuerpo_extra_html: str = "",
    nuevas_licitaciones: list = None,
    activas_anteriores: list = None,
) -> str:

    config = CATEGORY_CONFIG.get(
        categoria,
        CATEGORY_CONFIG["induwork"],
    )

    primary_color = (
        "#d9534f"
        if es_alerta_urgente
        else config["primary_color"]
    )

    titulo = (
        "🚨 ALERTA URGENTE: COMPRAS ÁGILES"
        if es_alerta_urgente
        else config["titulo_general"]
    )

    banner_path = _get_banner_path(
        categoria
    )

    banner_cid = (
        "banner"
        if banner_path
        else ""
    )

    if banner_path:

        banner_html = f'''
        <img
            src="cid:{banner_cid}"
            alt="{config["empresa"]}"
            style="
                width: 100%;
                height: auto;
                display: block;
            "
        >
        '''

    else:

        banner_html = f'''
        <div
            style="
                width: 100%;
                height: 80px;
                background-color:
                    {primary_color};
            "
        ></div>
        '''

    usar_secciones_diarias = (
        nuevas_licitaciones is not None
        or activas_anteriores is not None
    )

    if usar_secciones_diarias:

        nuevas = (
            nuevas_licitaciones
            or []
        )

        anteriores = (
            activas_anteriores
            or []
        )

        tabla_html = (
            _generar_secciones_diarias(
                nuevas=nuevas,
                anteriores=anteriores,
                primary_color=primary_color,
            )
        )

        total_oportunidades = (
            len(nuevas)
            + len(anteriores)
        )

    else:

        tabla_html = (
            _generar_tabla_html(
                licitaciones,
                primary_color,
            )
            if licitaciones
            else ""
        )

        total_oportunidades = (
            len(licitaciones)
            if licitaciones
            else 0
        )

    if (
        not usar_secciones_diarias
        and not licitaciones
        and cuerpo_extra_html
    ):

        tabla_html = (
            cuerpo_extra_html
        )

    contador_html = ""

    if total_oportunidades > 0:

        contador_html = f"""
        <tr>
            <td
                style="
                    text-align: center;
                    padding:
                        10px 0 5px 0;
                    font-size: 14px;
                    color: #666666;
                "
            >
                <b
                    style="
                        color:
                            {primary_color};
                    "
                >
                    Total de oportunidades:
                    {total_oportunidades}
                </b>
            </td>
        </tr>
        """

    html = f"""
<!DOCTYPE html>

<html>

<head>

    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="
            width=device-width,
            initial-scale=1.0
        "
    >

    <title>
        {config['empresa']} -
        {titulo}
    </title>

</head>

<body
    style="
        margin: 0;
        padding: 0;
        font-family:
            'Segoe UI',
            Arial,
            sans-serif;
        background-color:
            #f0f2f5;
    "
>

    <table
        align="center"
        border="0"
        cellpadding="0"
        cellspacing="0"
        width="100%"
        style="
            max-width: 700px;
            background-color:
                #ffffff;
            margin: 20px auto;
            border-radius: 12px;
            box-shadow:
                0 4px 20px
                rgba(0,0,0,0.08);
        "
    >

        <tr>

            <td
                style="
                    padding: 0;
                "
            >

                <!-- BANNER -->

                <table
                    width="100%"
                    border="0"
                    cellpadding="0"
                    cellspacing="0"
                >

                    <tr>

                        <td
                            style="
                                padding: 0;
                            "
                        >

                            {banner_html}

                        </td>

                    </tr>

                </table>

                <!-- ESPACIADO -->

                <table
                    width="100%"
                    border="0"
                    cellpadding="0"
                    cellspacing="0"
                >

                    <tr>

                        <td
                            style="
                                height: 20px;
                                font-size: 0;
                                line-height: 0;
                            "
                        >
                            &nbsp;
                        </td>

                    </tr>

                </table>

                <!-- TITULO -->

                <table
                    width="100%"
                    border="0"
                    cellpadding="0"
                    cellspacing="0"
                >

                    <tr>

                        <td
                            style="
                                text-align: center;
                                padding:
                                    0 20px;
                            "
                        >

                            <h2
                                style="
                                    color:
                                        #1A1A2E;
                                    margin: 0;
                                    font-size:
                                        22px;
                                    font-weight:
                                        700;
                                    letter-spacing:
                                        0.5px;
                                "
                            >
                                {titulo}
                            </h2>

                        </td>

                    </tr>

                </table>

                <!-- ESPACIADO -->

                <table
                    width="100%"
                    border="0"
                    cellpadding="0"
                    cellspacing="0"
                >

                    <tr>

                        <td
                            style="
                                height: 15px;
                                font-size: 0;
                                line-height: 0;
                            "
                        >
                            &nbsp;
                        </td>

                    </tr>

                </table>

                <!-- CONTENIDO -->

                <table
                    width="100%"
                    border="0"
                    cellpadding="0"
                    cellspacing="0"
                    style="
                        padding:
                            0 20px;
                    "
                >

                    <tr>

                        <td
                            style="
                                padding: 0;
                            "
                        >

                            {tabla_html}

                        </td>

                    </tr>

                </table>

                <!-- CONTADOR -->

                <table
                    width="100%"
                    border="0"
                    cellpadding="0"
                    cellspacing="0"
                >

                    {contador_html}

                </table>

                <!-- ESPACIADO -->

                <table
                    width="100%"
                    border="0"
                    cellpadding="0"
                    cellspacing="0"
                >

                    <tr>

                        <td
                            style="
                                height: 15px;
                                font-size: 0;
                                line-height: 0;
                            "
                        >
                            &nbsp;
                        </td>

                    </tr>

                </table>

                <!-- FOOTER -->

                <table
                    width="100%"
                    border="0"
                    cellpadding="0"
                    cellspacing="0"
                    style="
                        background-color:
                            {primary_color};
                        border-radius:
                            0 0 12px 12px;
                    "
                >

                    <tr>

                        <td
                            style="
                                padding:
                                    16px 20px;
                                text-align: center;
                            "
                        >

                            <p
                                style="
                                    margin:
                                        0 0 4px 0;
                                    color:
                                        #ffffff;
                                    font-weight:
                                        600;
                                    font-size:
                                        13px;
                                "
                            >
                                ¿Este filtro está funcionando bien?
                            </p>

                            <p
                                style="
                                    margin:
                                        0 0 10px 0;
                                    color:
                                        rgba(
                                            255,
                                            255,
                                            255,
                                            0.85
                                        );
                                    font-size:
                                        12px;
                                "
                            >
                                Reporta licitaciones que
                                <b>no corresponden</b>
                                o sugiere nuevas palabras clave.
                            </p>

                            <a
                                href="
                                    https://forms.gle/
                                    9WScZHxP9xaJCMYq9
                                "
                                style="
                                    display:
                                        inline-block;
                                    background-color:
                                        #ffffff;
                                    color:
                                        {primary_color};
                                    padding:
                                        9px 28px;
                                    text-decoration:
                                        none;
                                    font-weight:
                                        700;
                                    border-radius:
                                        30px;
                                    font-size:
                                        13px;
                                    margin-bottom:
                                        6px;
                                "
                            >
                                ✍️ Enviar Feedback
                            </a>

                            <p
                                style="
                                    margin:
                                        6px 0 0 0;
                                    color:
                                        rgba(
                                            255,
                                            255,
                                            255,
                                            0.7
                                        );
                                    font-size:
                                        10px;
                                "
                            >
                                ©
                                {datetime.now(CL_TZ).year}
                                ·
                                {config['empresa']}
                                · Bot automatizado
                            </p>

                        </td>

                    </tr>

                </table>

            </td>

        </tr>

    </table>

</body>

</html>
"""

    return html


# ============================================================
# SECCIONES DIARIAS
# ============================================================

def _generar_secciones_diarias(
    nuevas: list,
    anteriores: list,
    primary_color: str,
) -> str:

    if nuevas:

        nuevas_html = (
            _generar_tabla_html(
                nuevas,
                primary_color,
            )
        )

    else:

        nuevas_html = """
        <div
            style="
                padding: 18px;
                border:
                    1px solid #e5e5e5;
                border-radius: 8px;
                color: #666666;
                font-size: 13px;
                background-color:
                    #fafafa;
            "
        >
            No se encontraron nuevas
            oportunidades hoy.
        </div>
        """

    if anteriores:

        anteriores_html = (
            _generar_tabla_html(
                anteriores,
                primary_color,
            )
        )

    else:

        anteriores_html = """
        <div
            style="
                padding: 18px;
                border:
                    1px solid #e5e5e5;
                border-radius: 8px;
                color: #666666;
                font-size: 13px;
                background-color:
                    #fafafa;
            "
        >
            No hay oportunidades detectadas
            en días anteriores que continúen activas.
        </div>
        """

    return f"""

    <div
        style="
            margin-bottom: 35px;
        "
    >

        <h3
            style="
                margin:
                    0 0 12px 0;
                color:
                    #1A1A2E;
                font-size:
                    17px;
                font-weight:
                    700;
                border-bottom:
                    2px solid
                    {primary_color};
                padding-bottom:
                    8px;
            "
        >
            Nuevas oportunidades de hoy
        </h3>

        {nuevas_html}

    </div>

    <div>

        <h3
            style="
                margin:
                    0 0 12px 0;
                color:
                    #1A1A2E;
                font-size:
                    17px;
                font-weight:
                    700;
                border-bottom:
                    2px solid
                    #999999;
                padding-bottom:
                    8px;
            "
        >
            Oportunidades anteriores aún activas
        </h3>

        <p
            style="
                margin:
                    0 0 15px 0;
                color:
                    #777777;
                font-size:
                    12px;
            "
        >
            Estas oportunidades fueron detectadas
            en días anteriores y continúan publicadas.
        </p>

        {anteriores_html}

    </div>

    """


# ============================================================
# GARANTÍAS
# ============================================================

def _celda_garantia(
    requiere,
    monto=None,
) -> str:

    if requiere is None:

        return """
        <span
            style="
                color:#aaa;
                font-style:italic;
            "
        >
            No disponible vía API
        </span>
        """

    if not requiere:

        return """
        <span
            style="
                color:#888;
            "
        >
            No requiere
        </span>
        """

    texto = "Sí requiere"

    if monto:

        try:

            texto += (
                f" (${float(monto):,.0f})"
                .replace(
                    ",",
                    ".",
                )
            )

        except (
            ValueError,
            TypeError,
        ):

            pass

    return f"""
    <span
        style="
            color:#c0392b;
            font-weight:600;
        "
    >
        {texto}
    </span>
    """


# ============================================================
# TABLA
# ============================================================

def _generar_tabla_html(
    licitaciones: list,
    primary_color: str = "#E8720C",
) -> str:

    if not licitaciones:
        return ""

    filas = ""

    for l in licitaciones:

        enlace = l.get(
            "link",
            "https://www.mercadopublico.cl",
        )

        nombre = l.get(
            "nombre",
            "",
        )

        nombre_corto = (
            nombre[:50]
            + (
                "..."
                if len(nombre) > 50
                else ""
            )
        )

        fecha_cierre = (
            _formatear_fecha_cierre(
                l.get(
                    "fecha_cierre",
                    "",
                )
            )
        )

        monto = l.get(
            "monto_formateado",
            "No especificado",
        )

        filas += f"""
        <tr>

            <td
                style="
                    padding:
                        10px 8px;
                    border:
                        1px solid #e0e0e0;
                    font-size:
                        12px;
                    text-align:
                        center;
                "
            >
                <b>
                    {l.get('id', '')}
                </b>
            </td>

            <td
                style="
                    padding:
                        10px 8px;
                    border:
                        1px solid #e0e0e0;
                    font-size:
                        11px;
                    text-align:
                        center;
                "
            >
                {l.get('tipo', '')}
            </td>

            <td
                style="
                    padding:
                        10px 8px;
                    border:
                        1px solid #e0e0e0;
                    font-size:
                        12px;
                "
            >
                {nombre_corto}
            </td>

            <td
                style="
                    padding:
                        10px 8px;
                    border:
                        1px solid #e0e0e0;
                    font-size:
                        11px;
                    color:
                        #555;
                "
            >
                {l.get('organismo', '')}
            </td>

            <td
                style="
                    padding:
                        10px 8px;
                    border:
                        1px solid #e0e0e0;
                    font-size:
                        11px;
                    text-align:
                        center;
                "
            >
                {l.get('region', '')}
            </td>

            <td
                style="
                    padding:
                        10px 8px;
                    border:
                        1px solid #e0e0e0;
                    font-size:
                        11px;
                    text-align:
                        right;
                    white-space:
                        nowrap;
                "
            >
                <b>
                    {monto}
                </b>
            </td>

            <td
                style="
                    padding:
                        10px 8px;
                    border:
                        1px solid #e0e0e0;
                    font-size:
                        11px;
                    text-align:
                        center;
                    white-space:
                        nowrap;
                "
            >
                <b>
                    {fecha_cierre}
                </b>
            </td>

            <td
                style="
                    padding:
                        10px 8px;
                    border:
                        1px solid #e0e0e0;
                    font-size:
                        10px;
                    text-align:
                        center;
                "
            >
                {_celda_garantia(
                    l.get(
                        'requiere_garantia_seriedad'
                    ),
                    l.get(
                        'monto_garantia_seriedad'
                    )
                )}
            </td>

            <td
                style="
                    padding:
                        10px 8px;
                    border:
                        1px solid #e0e0e0;
                    font-size:
                        10px;
                    text-align:
                        center;
                "
            >
                {_celda_garantia(
                    l.get(
                        'requiere_garantia_fiel_cumplimiento'
                    ),
                    l.get(
                        'monto_garantia_fiel_cumplimiento'
                    )
                )}
            </td>

            <td
                style="
                    padding:
                        10px 8px;
                    border:
                        1px solid #e0e0e0;
                    text-align:
                        center;
                "
            >

                <a
                    href="{enlace}"
                    style="
                        background-color:
                            {primary_color};
                        color:
                            white;
                        padding:
                            5px 14px;
                        text-decoration:
                            none;
                        border-radius:
                            4px;
                        font-size:
                            11px;
                        font-weight:
                            600;
                        display:
                            inline-block;
                    "
                    target="_blank"
                >
                    Ver
                </a>

            </td>

        </tr>
        """

    return f"""
    <table
        width="100%"
        border="0"
        cellpadding="0"
        cellspacing="0"
        style="
            border-collapse:
                collapse;
            font-family:
                'Segoe UI',
                Arial,
                sans-serif;
            font-size:
                12px;
        "
    >

        <thead>

            <tr
                style="
                    background-color:
                        {primary_color};
                "
            >

                <th
                    style="
                        padding:
                            10px 8px;
                        border:
                            1px solid
                            {primary_color};
                        font-size:
                            11px;
                        color:
                            #fff;
                    "
                >
                    ID
                </th>

                <th
                    style="
                        padding:
                            10px 8px;
                        border:
                            1px solid
                            {primary_color};
                        font-size:
                            11px;
                        color:
                            #fff;
                    "
                >
                    Tipo
                </th>

                <th
                    style="
                        padding:
                            10px 8px;
                        border:
                            1px solid
                            {primary_color};
                        font-size:
                            11px;
                        text-align:
                            left;
                        color:
                            #fff;
                    "
                >
                    Nombre
                </th>

                <th
                    style="
                        padding:
                            10px 8px;
                        border:
                            1px solid
                            {primary_color};
                        font-size:
                            11px;
                        text-align:
                            left;
                        color:
                            #fff;
                    "
                >
                    Institución
                </th>

                <th
                    style="
                        padding:
                            10px 8px;
                        border:
                            1px solid
                            {primary_color};
                        font-size:
                            11px;
                        color:
                            #fff;
                    "
                >
                    Región
                </th>

                <th
                    style="
                        padding:
                            10px 8px;
                        border:
                            1px solid
                            {primary_color};
                        font-size:
                            11px;
                        color:
                            #fff;
                    "
                >
                    Monto
                </th>

                <th
                    style="
                        padding:
                            10px 8px;
                        border:
                            1px solid
                            {primary_color};
                        font-size:
                            11px;
                        color:
                            #fff;
                    "
                >
                    Cierra
                </th>

                <th
                    style="
                        padding:
                            10px 8px;
                        border:
                            1px solid
                            {primary_color};
                        font-size:
                            10px;
                        color:
                            #fff;
                    "
                >
                    Gtía. Seriedad
                </th>

                <th
                    style="
                        padding:
                            10px 8px;
                        border:
                            1px solid
                            {primary_color};
                        font-size:
                            10px;
                        color:
                            #fff;
                    "
                >
                    Gtía. Fiel Cump.
                </th>

                <th
                    style="
                        padding:
                            10px 8px;
                        border:
                            1px solid
                            {primary_color};
                        font-size:
                            11px;
                        color:
                            #fff;
                    "
                >
                    Link
                </th>

            </tr>

        </thead>

        <tbody>

            {filas}

        </tbody>

    </table>
    """


# ============================================================
# IMÁGENES
# ============================================================

def obtener_imagenes_para_cid(
    categoria: str,
) -> dict:

    return {
        "banner": _get_banner_path(
            categoria
        )
    }