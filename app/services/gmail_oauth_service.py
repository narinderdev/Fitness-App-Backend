# import os
# import base64
# from email.mime.text import MIMEText
# from google.oauth2.credentials import Credentials
# from google_auth_oauthlib.flow import InstalledAppFlow
# from googleapiclient.discovery import build

# SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# CREDENTIALS_PATH = "credentials/credentials.json"
# TOKEN_PATH = "credentials/token.json"


# def get_gmail_service():
#     creds = None

#     # Load token.json if exists
#     if os.path.exists(TOKEN_PATH):
#         creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

#     # No token or expired? Trigger browser login
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             creds.refresh(Request())
#         else:
#             flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
#             creds = flow.run_local_server(port=0)  # <-- Browser opens here

#         # Save new token.json
#         with open(TOKEN_PATH, "w") as token:
#             token.write(creds.to_json())

#     return build("gmail", "v1", credentials=creds)


# def send_email(to_email: str, subject: str, message: str):
#     service = get_gmail_service()

#     mime_msg = MIMEText(message)
#     mime_msg["to"] = to_email
#     mime_msg["subject"] = subject

#     encoded_msg = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode()

#     body = {"raw": encoded_msg}

#     result = (
#         service.users()
#         .messages()
#         .send(userId="me", body=body)
#         .execute()
#     )

#     print("Email sent! ID:", result["id"])
#     return result


# def send_email_otp(to_email: str, otp: str):
#     subject = "Your OTP Code"
#     body = f"Your login OTP for Fitness App is: {otp}"
#     return send_email(to_email, subject, body)
import os
import base64
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request 

# Gmail API scope
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# File locations
CREDENTIALS_PATH = "credentials/credentials.json"
TOKEN_PATH = "credentials/token.json"


# -----------------------------
#  HTML EMAIL TEMPLATE (Fitness App)
# -----------------------------
OTP_TEMPLATE = """
<!DOCTYPE html>
<html>
  <body style="margin:0; padding:0; font-family:Arial, Helvetica, sans-serif; background:#f4f4f4;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f4; padding:40px 0;">
      <tr>
        <td align="center">
          <table width="420" cellpadding="0" cellspacing="0" style="background:#ffffff; border-radius:12px; padding:30px; box-shadow:0px 4px 12px rgba(0,0,0,0.08);">

            <!-- Logo -->
            <tr>
              <td align="center" style="padding-bottom:20px;">
                <img src="https://glowante.blr1.cdn.digitaloceanspaces.com/fitness_app/newlogo.png" width="60" alt="Fitness App Logo" />
              </td>
            </tr>

            <!-- Title -->
            <tr>
              <td align="center" style="font-size:22px; font-weight:bold; color:#333;">
                Your Simple Starts OTP Code
              </td>
            </tr>

            <tr><td style="height:20px;"></td></tr>

            <!-- Body text -->
            <tr>
              <td style="font-size:15px; color:#555; line-height:1.6;">
                Hi there 👋,<br><br>
                Use the OTP code below to continue signing in or registering with <strong>Simple Starts App</strong>.
              </td>
            </tr>

            <tr><td style="height:30px;"></td></tr>

            <!-- OTP Box -->
            <tr>
              <td align="center">
                <div style="
                  font-size:32px;
                  font-weight:bold;
                  letter-spacing:6px;
                  padding:16px 24px;
                  background:#2ecc71;
                  color:white;
                  border-radius:8px;
                  display:inline-block;">
                  {{OTP}}
                </div>
              </td>
            </tr>

            <tr><td style="height:30px;"></td></tr>

            <!-- Footer -->
            <tr>
              <td style="font-size:14px; color:#999; line-height:1.5;">
                This OTP is valid for 10 minutes.<br>
                If you didn’t request this, you may ignore this email.
                <br><br>
                Stay fit 💪,<br>
                <strong>Simple Starts Team</strong>
              </td>
            </tr>

          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


# -----------------------------
#  AUTHENTICATE AND GET GMAIL SERVICE
# -----------------------------
def get_gmail_service():
    creds = None

    # Load saved Gmail token.json
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # No valid token? Run Google OAuth
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Opens Google login in browser
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH, SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save token.json
        with open(TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

    # Build Gmail API client
    return build("gmail", "v1", credentials=creds)


# -----------------------------
#  SEND GENERIC EMAIL
# -----------------------------
def send_email(to_email: str, subject: str, html_message: str):
    service = get_gmail_service()

    msg = MIMEText(html_message, "html")
    msg["to"] = to_email
    msg["subject"] = subject

    encoded_msg = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    body = {"raw": encoded_msg}

    result = (
        service.users()
        .messages()
        .send(userId="me", body=body)
        .execute()
    )

    print("Email sent! ID:", result["id"])
    return result


# -----------------------------
#  SEND OTP FUNCTION (READY TO USE)
# -----------------------------
def send_email_otp(to_email: str, otp: str):
    html = OTP_TEMPLATE.replace("{{OTP}}", otp)
    return send_email(to_email, "Your Simple Starts OTP Code", html)
