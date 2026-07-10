def evaluar_licitacion(licitacion: dict) -> dict:
    nombre = licitacion.get("nombre", "").lower()
    descripcion = licitacion.get("descripcion", "").lower()
    region = licitacion.get("region", "").lower()

    texto = f"{nombre} {descripcion}"

    # COIMSA — Limpieza / Aseo / Mantención
    keywords_coimsa = [
        "limpieza", "aseo", "sanitizacion", "sanitización",
        "higiene", "mantención", "mantencion", "ornato",
        "desinfección", "desinfeccion", "áreas verdes",
        "areas verdes", "jardinería", "jardineria"
    ]

    # INDUWORK — Seguridad / Táctico / Protección
    keywords_induwork = [
        "balistico", "balístico", "anticorte", "tactico", "táctico",
        "seguridad", "chaleco", "casco", "uniforme",
        "protección", "proteccion", "policial", "institucional",
        "operativo", "emergencia", "ropa de trabajo",
        "equipamiento", "equipos de seguridad"
    ]

    # ESPECIALES — Social / Informático / Comunitario
    keywords_especiales = [
        "actividad social", "programa social", "intervención",
        "comunitaria", "ciudadana", "participación",
        "desarrollo informatico", "desarrollo informático",
        "software", "sistema", "plataforma", "tecnológica",
        "digital", "modernización"
    ]

    # Región Metropolitana (COIMSA)
    es_rm = (
        "metropolitana" in region or
        "santiago" in region or
        "rm" == region.strip()
    )

    return {
        "coimsa": es_rm and any(k in texto for k in keywords_coimsa),
        "induwork": any(k in texto for k in keywords_induwork),
        "especial": any(k in texto for k in keywords_especiales)
    }
