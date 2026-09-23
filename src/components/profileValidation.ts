export function validateProfilePatch(patch: Record<string, unknown>) {
  const errors: Record<string, string> = {};
  for (const field of ["role", "officer_id", "approval_authority"]) if (field in patch) errors[field] = `${field.replace(/_/g, " ")} cannot be changed`;
  if (patch.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(patch.email))) errors.email = "Enter a valid email address";
  if (patch.phone && !/^[+\d][\d\s-]{7,15}$/.test(String(patch.phone))) errors.phone = "Enter a valid phone number";
  if (patch.name !== undefined && String(patch.name).trim().length < 2) errors.name = "Name is required";
  return errors;
}
export function validateProfilePhoto(file: { type: string; size: number }) {
  if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) return "Use JPEG, PNG, or WebP";
  if (file.size > 2_000_000) return "Photo must be 2 MB or smaller";
  return null;
}
