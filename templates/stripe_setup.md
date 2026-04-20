# Stripe Payment Setup Guide

## Option 1: Use Mock Payment (Current - No Setup Required)

The website is currently configured to use **mock payments** for testing. You can complete orders without setting up Stripe. Just click "Complete Mock Payment" at checkout.

## Option 2: Set Up Real Stripe Payments

If you want to use real Stripe payments:

### Step 1: Get Stripe API Keys

1. Go to [https://stripe.com](https://stripe.com)
2. Sign up for a free account (or log in)
3. Go to **Developers** → **API keys**
4. Copy your **Publishable key** (starts with `pk_test_`)
5. Copy your **Secret key** (starts with `sk_test_`)

### Step 2: Set Environment Variables

**On Windows PowerShell:**
```powershell
$env:STRIPE_SECRET_KEY="sk_test_your_actual_secret_key_here"
$env:STRIPE_PUBLISHABLE_KEY="pk_test_your_actual_publishable_key_here"
```

**On Windows Command Prompt:**
```cmd
set STRIPE_SECRET_KEY=sk_test_your_actual_secret_key_here
set STRIPE_PUBLISHABLE_KEY=pk_test_your_actual_publishable_key_here
```

**On macOS/Linux:**
```bash
export STRIPE_SECRET_KEY="sk_test_your_actual_secret_key_here"
export STRIPE_PUBLISHABLE_KEY="pk_test_your_actual_publishable_key_here"
```

### Step 3: Restart the Flask Application

After setting the environment variables, restart your Flask app:

```bash
python app.py
```

### Step 4: Test Payments

Use Stripe test card numbers:
- **Success:** `4242 4242 4242 4242`
- **Decline:** `4000 0000 0000 0002`
- Use any future expiry date, any CVC, and any ZIP code

## Current Status

✅ **Mock Payment Mode** - Works without Stripe setup
- Click "Complete Mock Payment" to test the checkout flow
- No real money is charged
- Perfect for development and testing

## Notes

- Test keys start with `pk_test_` and `sk_test_`
- Production keys start with `pk_live_` and `sk_live_`
- Never commit your secret keys to version control
- The app automatically detects if Stripe is configured

