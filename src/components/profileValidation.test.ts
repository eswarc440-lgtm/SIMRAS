import { describe, expect, it } from "vitest";
import { validateProfilePatch, validateProfilePhoto } from "./profileValidation";
describe("profile validation", () => {
  it("blocks immutable officer identity fields", () => { expect(validateProfilePatch({ role: "ADMIN", officer_id: "X" })).toMatchObject({ role: expect.any(String), officer_id: expect.any(String) }); });
  it("validates contact fields and photos", () => { expect(validateProfilePatch({ email: "bad" }).email).toBeTruthy(); expect(validateProfilePhoto({ type: "image/svg+xml", size: 100 })).toBeTruthy(); expect(validateProfilePhoto({ type: "image/png", size: 3_000_000 })).toBeTruthy(); expect(validateProfilePhoto({ type: "image/webp", size: 1000 })).toBeNull(); });
});
