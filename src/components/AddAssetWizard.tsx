import React, { useState } from "react";
import {
  PlusCircle,
  CheckCircle,
  AlertTriangle,
  Building,
  MapPin,
  Wrench,
  Shield,
  ArrowRight,
  ArrowLeft,
  X,
} from "lucide-react";

interface AddAssetWizardProps {
  onSuccess: (newAsset: any) => void;
  onCancel: () => void;
}

const AP_DISTRICTS = [
  "Alluri Sitharama Raju",
  "Anakapalli",
  "Ananthapuramu",
  "Annamayya",
  "Bapatla",
  "Chittoor",
  "Dr. B.R. Ambedkar Konaseema",
  "East Godavari",
  "Eluru",
  "Guntur",
  "Kakinada",
  "Krishna",
  "Kurnool",
  "Nandyal",
  "NTR",
  "Palnadu",
  "Parvathipuram Manyam",
  "Prakasam",
  "Sri Potti Sriramulu Nellore",
  "Sri Sathya Sai",
  "Srikakulam",
  "Tirupati",
  "Visakhapatnam",
  "Vizianagaram",
  "West Godavari",
  "YSR Kadapa",
];

export function AddAssetWizard({ onSuccess, onCancel }: AddAssetWizardProps) {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form State
  const [assetCode, setAssetCode] = useState("");
  const [name, setName] = useState("");
  const [assetType, setAssetType] = useState<"dam" | "barrage" | "bridge" | "airport" | "temple">("bridge");
  const [subtype, setSubtype] = useState("prestressed_concrete_bridge");
  const [district, setDistrict] = useState("East Godavari");

  const [latitude, setLatitude] = useState("16.9890");
  const [longitude, setLongitude] = useState("81.7820");

  const [builtYear, setBuiltYear] = useState("2015");
  const [material, setMaterial] = useState("Reinforced Concrete & High-Strength Steel");
  const [dimensionAuthority, setDimensionAuthority] = useState("Roads & Buildings Department / MoRTH");
  const [lengthM, setLengthM] = useState("450");
  const [heightM, setHeightM] = useState("18");
  const [unitsCount, setUnitsCount] = useState("12");

  const [condition, setCondition] = useState("Good");
  const [healthScore, setHealthScore] = useState("78.5");
  const [riskScore, setRiskScore] = useState("22.0");

  const validateStep = (currentStep: number): boolean => {
    setError(null);
    if (currentStep === 1) {
      if (!name.trim()) {
        setError("Please enter the official asset name");
        return false;
      }
    } else if (currentStep === 2) {
      const lat = parseFloat(latitude);
      const lng = parseFloat(longitude);
      if (isNaN(lat) || isNaN(lng)) {
        setError("Latitude and longitude must be valid floating numbers");
        return false;
      }
      if (lat < 12.0 || lat > 20.0 || lng < 76.0 || lng > 85.0) {
        setError("Coordinates must be within Andhra Pradesh geographic boundary (Lat 12°-20°N, Lng 76°-85°E)");
        return false;
      }
    }
    return true;
  };

  const handleNext = () => {
    if (validateStep(step)) {
      setStep((s) => s + 1);
    }
  };

  const handleBack = () => {
    setError(null);
    setStep((s) => s - 1);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateStep(step)) return;

    setLoading(true);
    setError(null);

    const token = localStorage.getItem("simras_token");

    const payload = {
      asset_code: assetCode.trim() || undefined,
      name: name.trim(),
      type: assetType,
      subtype,
      category: assetType.toUpperCase(),
      district,
      state: "Andhra Pradesh",
      coordinates: {
        latitude: parseFloat(latitude),
        longitude: parseFloat(longitude),
      },
      specifications: {
        built_year: parseInt(builtYear) || 2010,
        material,
        dimension_authority: dimensionAuthority,
        length_m: parseFloat(lengthM) || undefined,
        height_m: parseFloat(heightM) || undefined,
        element_count: parseInt(unitsCount) || undefined,
      },
      condition,
      health_score: parseFloat(healthScore) || 75.0,
      risk_score: parseFloat(riskScore) || 25.0,
      priority: 2,
    };

    try {
      const res = await fetch("/api/v1/assets", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "Failed to register infrastructure asset");
      }

      const created = await res.json();
      onSuccess(created);
    } catch (err: any) {
      setError(err.message || "Failed to submit asset registration");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white border border-[#D8E2EA] rounded-lg p-6 sm:p-8 shadow-md text-slate-800 max-w-3xl mx-auto">
      {/* Wizard Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-100 mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-[#1268A8]">
            <PlusCircle className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-900 tracking-tight">Add Infrastructure Asset</h2>
            <p className="text-xs text-slate-500">Step {step} of 4 — Civil Engineering Asset Induction</p>
          </div>
        </div>
        <button
          onClick={onCancel}
          className="text-xs text-slate-500 hover:text-slate-800 p-1 rounded hover:bg-slate-100 transition"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Top 4 Progress Steps */}
      <div className="grid grid-cols-4 gap-2 mb-6">
        {[
          { num: 1, label: "Basic Info" },
          { num: 2, label: "Location" },
          { num: 3, label: "Engineering" },
          { num: 4, label: "Review" },
        ].map((s) => (
          <div
            key={s.num}
            className={`p-2.5 rounded-md text-center text-xs font-semibold border transition ${
              step === s.num
                ? "bg-blue-50 border-[#1268A8] text-[#1268A8]"
                : step > s.num
                ? "bg-emerald-50 border-emerald-300 text-emerald-700"
                : "bg-slate-50 border-[#D8E2EA] text-slate-400"
            }`}
          >
            {s.num}. {s.label}
          </div>
        ))}
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-md bg-red-50 border border-red-200 flex items-center gap-2 text-xs text-red-700">
          <AlertTriangle className="w-4 h-4 shrink-0 text-red-500" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Step 1: Basic Information */}
        {step === 1 && (
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Official Infrastructure Asset Name *
              </label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Gundlakamma Reservoir Spillway"
                className="w-full bg-white border border-[#D8E2EA] focus:border-[#1268A8] focus:ring-1 focus:ring-[#1268A8] rounded-md px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Asset Code (Optional)</label>
                <input
                  type="text"
                  value={assetCode}
                  onChange={(e) => setAssetCode(e.target.value)}
                  placeholder="Auto-generated if empty"
                  className="w-full bg-white border border-[#D8E2EA] focus:border-[#1268A8] rounded-md px-3 py-2 text-xs font-mono text-slate-900 placeholder-slate-400 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Category / Infrastructure Class *</label>
                <select
                  value={assetType}
                  onChange={(e) => {
                    const t = e.target.value as any;
                    setAssetType(t);
                    if (t === "dam") setSubtype("composite_gravity_dam");
                    else if (t === "barrage") setSubtype("river_barrage_with_roadway");
                    else if (t === "bridge") setSubtype("prestressed_concrete_bridge");
                    else if (t === "airport") setSubtype("commercial_aviation_terminal");
                    else if (t === "temple") setSubtype("heritage_temple_complex");
                  }}
                  className="w-full bg-white border border-[#D8E2EA] focus:border-[#1268A8] rounded-md px-3 py-2 text-xs font-medium text-slate-900 focus:outline-none"
                >
                  <option value="dam">Dam (Reservoir / Hydel)</option>
                  <option value="barrage">Barrage (Regulator & Weir)</option>
                  <option value="bridge">Bridge (Highway / Rail / River)</option>
                  <option value="airport">Airport (Terminal & Runway)</option>
                  <option value="temple">Temple (Religious Heritage Site)</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">District (Andhra Pradesh) *</label>
              <select
                value={district}
                onChange={(e) => setDistrict(e.target.value)}
                className="w-full bg-white border border-[#D8E2EA] focus:border-[#1268A8] rounded-md px-3 py-2 text-xs font-medium text-slate-900 focus:outline-none"
              >
                {AP_DISTRICTS.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}

        {/* Step 2: Location */}
        {step === 2 && (
          <div className="space-y-4">
            <div className="p-3 bg-blue-50/60 border border-blue-200 rounded-md text-xs text-blue-900 flex items-center gap-2">
              <MapPin className="w-4 h-4 text-[#1268A8] shrink-0" />
              <span>GIS Geodetic WGS84 decimal coordinates within Andhra Pradesh bounds.</span>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Latitude (°N) *</label>
                <input
                  type="text"
                  required
                  value={latitude}
                  onChange={(e) => setLatitude(e.target.value)}
                  placeholder="e.g. 16.9890"
                  className="w-full bg-white border border-[#D8E2EA] focus:border-[#1268A8] rounded-md px-3 py-2 text-sm text-slate-900 font-mono focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Longitude (°E) *</label>
                <input
                  type="text"
                  required
                  value={longitude}
                  onChange={(e) => setLongitude(e.target.value)}
                  placeholder="e.g. 81.7820"
                  className="w-full bg-white border border-[#D8E2EA] focus:border-[#1268A8] rounded-md px-3 py-2 text-sm text-slate-900 font-mono focus:outline-none"
                />
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Engineering Specs */}
        {step === 3 && (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Built Year</label>
                <input
                  type="number"
                  value={builtYear}
                  onChange={(e) => setBuiltYear(e.target.value)}
                  className="w-full bg-white border border-[#D8E2EA] rounded-md px-3 py-2 text-sm text-slate-900 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Length / Span (m)</label>
                <input
                  type="number"
                  value={lengthM}
                  onChange={(e) => setLengthM(e.target.value)}
                  className="w-full bg-white border border-[#D8E2EA] rounded-md px-3 py-2 text-sm text-slate-900 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Max Height (m)</label>
                <input
                  type="number"
                  value={heightM}
                  onChange={(e) => setHeightM(e.target.value)}
                  className="w-full bg-white border border-[#D8E2EA] rounded-md px-3 py-2 text-sm text-slate-900 focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Construction Material</label>
              <input
                type="text"
                value={material}
                onChange={(e) => setMaterial(e.target.value)}
                className="w-full bg-white border border-[#D8E2EA] rounded-md px-3 py-2 text-sm text-slate-900 focus:outline-none"
              />
            </div>
          </div>
        )}

        {/* Step 4: Review */}
        {step === 4 && (
          <div className="space-y-4">
            <div className="p-4 bg-slate-50 border border-[#D8E2EA] rounded-md space-y-2 text-xs">
              <h4 className="font-bold text-slate-900 border-b border-slate-200 pb-2">Review Summary</h4>
              <div className="flex justify-between"><span className="text-slate-500">Asset Name:</span> <span className="font-bold text-slate-900">{name}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Category:</span> <span className="font-semibold capitalize text-slate-800">{assetType}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">District:</span> <span className="font-semibold text-slate-800">{district}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Coordinates:</span> <span className="font-mono text-slate-800">{latitude}°N, {longitude}°E</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Dimensions:</span> <span className="font-mono text-slate-800">{lengthM}m Length × {heightM}m Height</span></div>
            </div>
          </div>
        )}

        {/* Navigation Buttons */}
        <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
          {step > 1 ? (
            <button
              type="button"
              onClick={handleBack}
              className="flex items-center gap-1 px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-slate-100 rounded-md transition"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back</span>
            </button>
          ) : (
            <div />
          )}

          {step < 4 ? (
            <button
              type="button"
              onClick={handleNext}
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-white bg-[#1268A8] hover:bg-[#0D4E7A] rounded-md transition shadow-sm"
            >
              <span>Next Step</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-1.5 px-5 py-2.5 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-md transition shadow-sm disabled:opacity-50"
            >
              {loading ? (
                <span>Registering Infrastructure...</span>
              ) : (
                <>
                  <CheckCircle className="w-4 h-4" />
                  <span>Submit Official Registration</span>
                </>
              )}
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
