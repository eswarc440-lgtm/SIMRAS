import * as nodemailer from "nodemailer";

function smtpConfiguration() {
  const user =
    process.env.SMTP_USER ||
    process.env.EMAIL_USER ||
    process.env.MAIL_USER ||
    "";

  const pass =
    process.env.SMTP_PASS ||
    process.env.EMAIL_APP_PASSWORD ||
    process.env.EMAIL_PASSWORD ||
    process.env.MAIL_PASS ||
    "";

  const host =
    process.env.SMTP_HOST ||
    (user.toLowerCase().endsWith("@gmail.com")
      ? "smtp.gmail.com"
      : "");

  const port = Number(process.env.SMTP_PORT || 587);

  const secure =
    String(process.env.SMTP_SECURE || "").toLowerCase() === "true" ||
    port === 465;

  const from =
    process.env.SMTP_FROM ||
    process.env.EMAIL_FROM ||
    user;

  return { host, port, secure, user, pass, from };
}

export function getEmailHealth() {
  const config = smtpConfiguration();

  return {
    configured: Boolean(
      config.host &&
      config.user &&
      config.pass &&
      config.from,
    ),
    host: config.host || null,
    port: config.port,
  };
}

export async function sendPasswordResetCode(
  recipient: string,
  code: string,
  expiresAt: string,
) {
  const config = smtpConfiguration();

  if (!config.host || !config.user || !config.pass || !config.from) {
    throw new Error(
      "SMTP_NOT_CONFIGURED: Configure SMTP_HOST, SMTP_USER, SMTP_PASS and SMTP_FROM in the server environment.",
    );
  }

  const transporter = nodemailer.createTransport({
    host: config.host,
    port: config.port,
    secure: config.secure,
    auth: {
      user: config.user,
      pass: config.pass,
    },
  });

  const expiry = new Date(expiresAt).toLocaleString("en-IN", {
    timeZone: "Asia/Kolkata",
  });

  await transporter.sendMail({
    from: config.from,
    to: recipient,
    subject: "SIMRAS Password Reset Code",
    text:
      `SIMRAS password reset code: ${code}\n\n` +
      `This code expires at ${expiry} IST.\n\n` +
      `If you did not request this password reset, ignore this email. ` +
      `Do not share this code with anyone.`,
    html: `
      <div style="font-family:Arial,sans-serif;max-width:560px;margin:auto">
        <h2 style="color:#1268A8">SIMRAS Password Reset</h2>
        <p>A password reset was requested for your SIMRAS Officer Portal account.</p>

        <div style="
          font-size:30px;
          font-weight:700;
          letter-spacing:8px;
          padding:18px;
          text-align:center;
          background:#f1f5f9;
          border-radius:8px;
          margin:20px 0
        ">${code}</div>

        <p>This verification code expires at <strong>${expiry} IST</strong>.</p>
        <p>If you did not request this reset, you can safely ignore this email.</p>
        <p style="font-size:12px;color:#64748b">
          Never share your password or reset code with another person.
        </p>
      </div>
    `,
  });
}