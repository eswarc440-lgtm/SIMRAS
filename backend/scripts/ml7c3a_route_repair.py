from pathlib import Path


root = Path.cwd()

main_file = root / "backend/app/main.py"

api_file = (
    root
    / "frontend/src/services/simrasTwinApi.ts"
)


# ============================================================
# PATCH backend/app/main.py
# ============================================================

main = main_file.read_text(
    encoding="utf-8"
)


import_line = (
    "from app.api.routes.dam_barrage_profile "
    "import router as dam_barrage_profile_router"
)


if import_line not in main:

    anchor = "app = FastAPI("

    index = main.find(anchor)

    if index < 0:

        raise RuntimeError(
            "Could not find app = FastAPI( in main.py"
        )

    main = (
        main[:index]
        + import_line
        + "\n\n"
        + main[index:]
    )


include_line = (
    "app.include_router("
    "dam_barrage_profile_router"
    ")"
)


if include_line not in main:

    main = (
        main.rstrip()
        + "\n\n"
        + "# ML-7C official dam/barrage profile route\n"
        + include_line
        + "\n"
    )


# Must occur exactly once.
if main.count(import_line) != 1:

    raise RuntimeError(
        "dam_barrage_profile_router import count != 1"
    )


if main.count(include_line) != 1:

    raise RuntimeError(
        "dam_barrage_profile_router include count != 1"
    )


main_file.write_text(
    main,
    encoding="utf-8",
    newline="\n",
)


# ============================================================
# PATCH frontend/src/services/simrasTwinApi.ts
# ============================================================

api = api_file.read_text(
    encoding="utf-8"
)


if "damBarrageProfile:" not in api:

    anchor = "assets: (options?: {"

    index = api.find(anchor)

    if index < 0:

        raise RuntimeError(
            "Could not locate assets API method anchor"
        )


    method = '''damBarrageProfile: (assetCode: string) =>
    request<any>(
      `/assets/${encodeURIComponent(assetCode)}/dam-barrage-profile`,
    ),

  '''


    api = (
        api[:index]
        + method
        + api[index:]
    )


if api.count("damBarrageProfile:") != 1:

    raise RuntimeError(
        "damBarrageProfile API method count != 1"
    )


api_file.write_text(
    api,
    encoding="utf-8",
    newline="\n",
)


print("MAIN_IMPORT=PASS")
print("MAIN_INCLUDE=PASS")
print("FRONTEND_API=PASS")