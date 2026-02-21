# FAXP (Freight Agent eXchange Protocol)

FAXP v0.1.1 demo includes:
- Python simulation (load flow + truck flow)
- Streamlit UI demo
- Security hardening (signing, TTL/replay checks, rotation scripts)

## Cloud Demo

Streamlit URL: https://YOUR-APP-URL.streamlit.app

### Demo settings (known-good)
- Verification Provider: MockBiometricProvider
- Mock Verification Status: Success
- BidResponse: Accept

Expected result:
- Booking completed
- VerifiedBadge: Premium
- Validation Errors: 0

### Direct FMCSA mode
- Set `FAXP_FMCSA_WEBKEY` in your local/Streamlit secrets.
- In the app, choose `Verification Provider: FMCSA` and `FMCSA Source: live-fmcsa`.
- Enter an MC number (example: `498282`).
