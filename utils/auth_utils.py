from datetime import datetime, timedelta
from flask import flash
from models import db, EmailToken, sha256
from utils.email_utils import send_email


def build_verify_email_html(username: str, code: str) -> str:
    return f"""
    <div style="margin:0;padding:0;background-color:#f4f6f9;font-family:Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="padding:30px 0;background:#f4f6f9;">
        <tr>
          <td align="center">
            <table width="520" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:10px;padding:28px;">
              <tr>
                <td align="center" style="font-size:20px;font-weight:bold;color:#222;padding-bottom:10px;">
                  Verify your email
                </td>
              </tr>
              <tr>
                <td align="center" style="font-size:14px;color:#555;padding-bottom:18px;">
                  Hi {username}, thanks for using <strong>SpendSense</strong>. Use the code below to finish setting up your account.
                </td>
              </tr>
              <tr>
                <td align="center">
                  <div style="
                      display:inline-block;
                      padding:14px 22px;
                      background:#f0f3f8;
                      border-radius:8px;
                      font-size:28px;
                      font-weight:bold;
                      letter-spacing:4px;
                      color:#2c3e50;">
                    {code}
                  </div>
                </td>
              </tr>
              <tr>
                <td align="center" style="font-size:12px;color:#888;padding-top:16px;">
                  This code expires in 10 minutes.
                </td>
              </tr>
              <tr>
                <td style="padding:22px 0;">
                  <hr style="border:none;border-top:1px solid #eee;">
                </td>
              </tr>
              <tr>
                <td align="center" style="font-size:12px;color:#aaa;">
                  If you did not request this, please contact support.
                  <br><br>
                  © 2026 SpendSense
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </div>
    """

def build_reset_password_html(username: str, reset_link: str) -> str:
    return f"""
    <div style="margin:0;padding:0;background-color:#f4f6f9;font-family:Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="padding:30px 0;background:#f4f6f9;">
        <tr>
          <td align="center">
            <table width="520" cellpadding="0" cellspacing="0"
                   style="background:#ffffff;border-radius:10px;padding:28px;">
              <tr>
                <td align="center" style="font-size:20px;font-weight:bold;color:#222;padding-bottom:10px;">
                  Reset your password
                </td>
              </tr>

              <tr>
                <td align="center" style="font-size:14px;color:#555;padding-bottom:18px;line-height:1.4;">
                  Hi {username}, we received a request to reset your <strong>SpendSense</strong> password.
                  Click the button below. This link expires in <strong>30 minutes</strong>.
                </td>
              </tr>

              <tr>
                <td align="center" style="padding:10px 0 6px 0;">
                  <a href="{reset_link}"
                     style="
                       display:inline-block;
                       padding:12px 20px;
                       background:#4CAF50;
                       color:#ffffff;
                       text-decoration:none;
                       border-radius:8px;
                       font-weight:bold;
                       font-size:16px;">
                    Reset Password
                  </a>
                </td>
              </tr>

              <tr>
                <td align="center" style="font-size:12px;color:#888;padding-top:10px;line-height:1.4;">
                  If the button does not work, copy and paste this link into your browser:
                  <br>
                  <a href="{reset_link}" style="color:#0d47a1;word-break:break-all;">{reset_link}</a>
                </td>
              </tr>

              <tr>
                <td style="padding:22px 0;">
                  <hr style="border:none;border-top:1px solid #eee;">
                </td>
              </tr>

              <tr>
                <td align="center" style="font-size:12px;color:#aaa;line-height:1.4;">
                  If you did not request this, please contact support.
                  <br><br>
                  © 2026 SpendSense
                </td>
              </tr>

            </table>
          </td>
        </tr>
      </table>
    </div>
    """

def create_verify_token(user_id: int, minutes_valid: int = 10):
    EmailToken.query.filter_by(user_id=user_id, purpose="verify", used=False).update({"used": True})
    db.session.commit()

    code = EmailToken.new_otp()
    tok = EmailToken(
        user_id=user_id,
        purpose="verify",
        token_hash=sha256(code),
        expires_at=datetime.utcnow() + timedelta(minutes=minutes_valid),
        used=False
    )
    db.session.add(tok)
    db.session.commit()
    return code


def send_verification_code(user, subject: str, flash_on_success: str | None = None):
    code = create_verify_token(user.id)
    html = build_verify_email_html(user.username, code)

    try:
        send_email(user.email, subject, html, to_name=user.username)
        if flash_on_success:
            flash(flash_on_success, "info")
    except Exception as e:
        print("Mailjet send failed:", e)
        flash("We couldn't send the verification email right now.", "warning")


def can_resend_verify_code(user_id: int, max_in_window: int = 3, window_minutes: int = 15):
    window_start = datetime.utcnow() - timedelta(minutes=window_minutes)

    recent_count = (EmailToken.query
                    .filter(
                        EmailToken.user_id == user_id,
                        EmailToken.purpose == "verify",
                        EmailToken.created_at >= window_start
                    )
                    .count())

    return recent_count < max_in_window