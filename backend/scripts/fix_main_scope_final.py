from pathlib import Path
import re

ROOT = Path("/repo")

assets_py = ROOT / "backend/app/api/routes/assets.py"
api_ts = ROOT / "frontend/src/services/api.ts"
app_tsx = ROOT / "frontend/src/App.tsx"


def read(path):
    return path.read_text(encoding="utf-8-sig")


def write(path, text):
    path.write_text(
        text,
        encoding="utf-8",
        newline="\n",
    )


# ============================================================
# BACKEND assets.py
# ============================================================

text = read(assets_py)

# Need OR for name/code/district search.
text = text.replace(
    "from sqlalchemy import func, select",
    "from sqlalchemy import func, or_, select",
)

# Main infrastructure scope.
if "MAIN_ASSET_TYPES" not in text:
    marker = 'router = APIRouter(prefix="/assets", tags=["assets"])'

    if marker not in text:
        raise RuntimeError(
            "assets.py router marker not found"
        )

    text = text.replace(
        marker,
        marker + '''

MAIN_ASSET_TYPES = (
    "dam",
    "bridge",
    "barrage",
    "airport",
    "temple",
)
''',
        1,
    )


# Every main registry request is limited to the five classes.
old = '''    filters = []
    if asset_type:
        filters.append(Asset.asset_type == asset_type)
    if district:
        filters.append(Asset.district == district)
    if search:
        filters.append(Asset.name.ilike(f"%{search}%"))
'''

new = '''    filters = [
        func.lower(Asset.asset_type).in_(
            MAIN_ASSET_TYPES
        )
    ]

    if asset_type:
        filters.append(
            func.lower(Asset.asset_type)
            == asset_type.lower()
        )

    if district:
        filters.append(
            func.lower(Asset.district)
            == district.lower()
        )

    if search:
        search_pattern = f"%{search}%"

        filters.append(
            or_(
                Asset.name.ilike(search_pattern),
                Asset.asset_code.ilike(search_pattern),
                Asset.district.ilike(search_pattern),
            )
        )
'''

if old in text:
    text = text.replace(
        old,
        new,
        1,
    )
elif "func.lower(Asset.asset_type)" not in text:
    raise RuntimeError(
        "Could not locate assets.py filter block"
    )

write(
    assets_py,
    text,
)

print("[PATCHED] assets.py")
print("          case-insensitive asset types")
print("          five main infrastructure classes")
print("          search name + code + district")


# ============================================================
# FRONTEND api.ts
# ============================================================

text = read(api_ts)

old = '''  assets: () => request<AssetListResponse>("/assets?limit=1000"),'''

new = '''  assets: (options?: {
    assetType?: string;
    search?: string;
    district?: string;
    limit?: number;
    offset?: number;
  }) => {
    const parameters = new URLSearchParams({
      limit: String(options?.limit ?? 1000),
      offset: String(options?.offset ?? 0),
    });

    if (options?.assetType) {
      parameters.set(
        "asset_type",
        options.assetType,
      );
    }

    if (options?.search) {
      parameters.set(
        "search",
        options.search,
      );
    }

    if (options?.district) {
      parameters.set(
        "district",
        options.district,
      );
    }

    return request<AssetListResponse>(
      `/assets?${parameters.toString()}`,
    );
  },'''

if old in text:
    text = text.replace(
        old,
        new,
        1,
    )

elif "assets: (options?" not in text:
    raise RuntimeError(
        "api.ts assets method format not recognised"
    )

write(
    api_ts,
    text,
)

print("[PATCHED] api.ts")


# ============================================================
# FRONTEND App.tsx
# ============================================================

text = read(app_tsx)


# ------------------------------------------------------------
# Heading
# ------------------------------------------------------------

for old_heading in (
    "AP BRIDGES · DAMS · BARRAGES",
    "AP BRIDGES Â· DAMS Â· BARRAGES",
):
    text = text.replace(
        old_heading,
        "AP DAMS · BRIDGES · BARRAGES · AIRPORTS · TEMPLES",
    )


# ------------------------------------------------------------
# Filter order
# ------------------------------------------------------------

old_options = '''<option value="all">All assets</option>
                  <option value="bridge">Bridges</option>
                  <option value="dam">Dams</option>
                  <option value="barrage">Barrages</option>
                  <option value="airport">Airports</option>
                  <option value="temple">Temples</option>'''

new_options = '''<option value="all">All assets</option>
                  <option value="dam">Dams</option>
                  <option value="bridge">Bridges</option>
                  <option value="barrage">Barrages</option>
                  <option value="airport">Airports</option>
                  <option value="temple">Temples</option>'''

text = text.replace(
    old_options,
    new_options,
)


# ------------------------------------------------------------
# Server-side selected-type request
#
# Replace the api.assets() call inside startup/load effect.
# ------------------------------------------------------------

if "api.assets()," in text:

    text = text.replace(
        "api.assets(),",
        '''api.assets({
        assetType:
          typeFilter === "all"
            ? undefined
            : typeFilter,
        search:
          query.trim() || undefined,
        limit: 1000,
        offset: 0,
      }),''',
        1,
    )

elif "api.assets()" in text:

    text = text.replace(
        "api.assets()",
        '''api.assets({
        assetType:
          typeFilter === "all"
            ? undefined
            : typeFilter,
        search:
          query.trim() || undefined,
        limit: 1000,
        offset: 0,
      })''',
        1,
    )


# ------------------------------------------------------------
# Make load effect react to selected type and search.
# Find the useEffect containing api.assets({ ... }).
# ------------------------------------------------------------

asset_call = text.find("api.assets({")

if asset_call < 0:
    raise RuntimeError(
        "App.tsx api.assets call not found"
    )

effect_start = text.rfind(
    "useEffect(() => {",
    0,
    asset_call,
)

if effect_start < 0:
    raise RuntimeError(
        "Asset-loading useEffect not found"
    )

dependency_pos = text.find(
    "}, []);",
    asset_call,
)

if dependency_pos >= 0:

    text = (
        text[:dependency_pos]
        + "}, [typeFilter, query]);"
        + text[
            dependency_pos
            + len("}, []);"):
        ]
    )


# ------------------------------------------------------------
# Existing local type filter must also tolerate uppercase DB
# values until normalization completes.
# ------------------------------------------------------------

text = text.replace(
    "asset.asset_type === typeFilter",
    '''String(asset.asset_type)
            .toLowerCase() === typeFilter''',
)


write(
    app_tsx,
    text,
)

print("[PATCHED] App.tsx")
print("          selected type loads from backend")
print("          search runs against full selected class")
print("          uppercase/lowercase type tolerant")