export interface PredictionStatus {
  asset: {
    id: number;
    asset_code: string;
    name: string;
    asset_type: string;
    identity_status: string;
  };
  prediction_available: boolean;
  status: string;
  reason_code: string;
  model: {
    model_name?: string;
    version?: string;
    feature_version?: string;
    stage?: string;
    promotion_decision?: string;
    promotion_approved?: boolean;
    training_dataset?: string;
  } | null;
  governance?: {
    identity_status?: string;
    promotion_blockers?: string[];
    ap_validation?: {
      total_candidates?: number;
      prediction_eligible?: number;
      prediction_withheld?: number;
      verified_identities?: number;
      average_feature_coverage?: number;
      max_feature_coverage?: number;
      local_engineering_validation?: boolean;
    };
    warning?: string;
  };
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

if (!API_BASE_URL) {
  throw new Error("VITE_API_BASE_URL is not configured");
}

export async function getPredictionStatus(
  assetCode: string,
): Promise<PredictionStatus> {
  const response = await fetch(
    `${API_BASE_URL}/assets/${encodeURIComponent(assetCode)}/predictions/status`,
    {
      method: "GET",
      cache: "no-store",
      headers: {
        Accept: "application/json",
      },
    },
  );

  if (!response.ok) {
    throw new Error(
      `Prediction governance API failed: ${response.status}`,
    );
  }

  return response.json() as Promise<PredictionStatus>;
}

export function predictionReasonLabel(
  code?: string,
): string {
  switch (code) {
    case "MODEL_NOT_AP_LOCALLY_VALIDATED":
      return "Model not locally validated for Andhra Pradesh";
    case "ASSET_IDENTITY_NOT_VERIFIED":
      return "Asset identity requires verification";
    case "NO_AP_ASSETS_MEET_INFERENCE_ELIGIBILITY":
      return "Verified engineering features are insufficient";
    case "MODEL_STAGE_NOT_PRODUCTION_ALLOWED":
      return "Model is not approved for production inference";
    case "MODEL_NOT_REGISTERED":
      return "No governed production model is registered";
    case "MODEL_GOVERNANCE_APPROVED":
      return "Governed AI prediction is available";
    case "NON_BRIDGE_MULTIFACTOR_SCOPE":
      return "Transparent decision-support assessment available";
    default:
      return code
        ? code.replaceAll("_", " ")
        : "Prediction governance status unavailable";
  }
}
