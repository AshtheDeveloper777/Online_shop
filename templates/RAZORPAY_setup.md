# Razorpay Payment Setup Guide

## What is Razorpay?

Razorpay is India's leading payment gateway that supports:
- ✅ **UPI** (Unified Payments Interface)
- ✅ **Credit/Debit Cards** (Visa, Mastercard, RuPay, etc.)
- ✅ **Wallets** (Paytm, PhonePe, Freecharge, etc.)
- ✅ **Net Banking** (All major banks)
- ✅ **EMI** (Easy Monthly Installments)

## Step 1: Create Razorpay Account

1. Go to [https://razorpay.com](https://razorpay.com)
2. Click **Sign Up** and create a free account
3. Complete your business details (you can use test mode for development)

## Step 2: Get API Keys

1. Log in to your Razorpay Dashboard
2. Go to **Settings** → **API Keys**
3. Click **Generate Test Keys** (for testing) or use **Live Keys** (for production)
4. Copy your **Key ID** (starts with `rzp_test_` or `rzp_live_`)
5. Copy your **Key Secret** (starts with `rzp_test_` or `rzp_live_`)

## Step 3: Set Environment Variables

**On Windows PowerShell:**
```powershell
$env:RAZORPAY_KEY_ID="rzp_test_your_key_id_here"
$env:RAZORPAY_KEY_SECRET="your_key_secret_here"
```

**On Windows Command Prompt:**
```cmd
set RAZORPAY_KEY_ID=rzp_test_your_key_id_here
set RAZORPAY_KEY_SECRET=your_key_secret_here
```

**On macOS/Linux:**
```bash
export RAZORPAY_KEY_ID="rzp_test_your_key_id_here"
export RAZORPAY_KEY_SECRET="your_key_secret_here"
```

## Step 4: Install Dependencies

```bash
pip install razorpay
```

Or if you haven't installed requirements:
```bash
pip install -r requirements.txt
```

## Step 5: Restart Flask Application

After setting environment variables, restart your Flask app:

```bash
python app.py
```

## Step 6: Test Payments

### Test UPI IDs:
- `success@razorpay` - Successful payment
- `failure@razorpay` - Failed payment

### Test Cards:
- **Success:** `4111 1111 1111 1111`
- **Failure:** `4000 0000 0000 0002`
- Use any future expiry date, any CVV, and any name

### Test Net Banking:
- Select any bank from the list
- Use any credentials (test mode)

## Payment Methods Supported

### UPI
- Google Pay
- PhonePe
- Paytm
- BHIM
- All UPI apps

### Cards
- Visa
- Mastercard
- RuPay
- American Express
- Diners Club

### Wallets
- Paytm
- PhonePe
- Freecharge
- Mobikwik
- JioMoney
- And more...

### Net Banking
- All major Indian banks

## Features

✅ **Secure Payments** - PCI DSS compliant
✅ **Instant Settlements** - Funds in your account quickly
✅ **Multiple Payment Options** - UPI, Cards, Wallets, Net Banking
✅ **Mobile Friendly** - Works on all devices
✅ **Easy Integration** - Simple API
✅ **24/7 Support** - Always available

## Current Status

The website automatically detects if Razorpay is configured:
- ✅ **Razorpay Enabled** - Shows UPI/Cards/Wallets option
- ❌ **Razorpay Disabled** - Shows mock payment option

## Notes

- Test keys start with `rzp_test_`
- Live keys start with `rzp_live_`
- Never commit your Key Secret to version control
- Use test mode for development
- Switch to live mode only after testing

## Support

For issues or questions:
- Razorpay Docs: https://razorpay.com/docs/
- Razorpay Support: support@razorpay.com

