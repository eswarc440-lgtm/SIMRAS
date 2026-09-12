from app.main import app

keywords = (
    "twin",
    "asset",
    "report",
    "prediction",
    "infrastructure",
    "gis",
)

print("CURRENT BACKEND ROUTES")
print("-" * 100)

for route in app.routes:

    path = getattr(
        route,
        "path",
        ""
    )

    methods = getattr(
        route,
        "methods",
        None
    )

    if not any(
        keyword in path.lower()
        for keyword in keywords
    ):
        continue

    method_text = (
        ",".join(
            sorted(methods)
        )
        if methods
        else ""
    )

    print(
        f"{method_text:<20} {path}"
    )
