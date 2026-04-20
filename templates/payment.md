# Payment Methods Setup Guide

Your e-commerce website now supports multiple payment methods!

## Available Payment Methods

### 1. Razorpay (Recommended for India) 🇮🇳
Supports:
- ✅ **UPI** (Google Pay, PhonePe, Paytm, BHIM, etc.)
- ✅ **Credit/Debit Cards** (Visa, Mastercard, RuPay)
- ✅ **Wallets** (Paytm, PhonePe, Freecharge, Mobikwik)
- ✅ **Net Banking** (All major Indian banks)
- ✅ **EMI** (Easy Monthly Installments)

### 2. Stripe (International)
Supports:
- ✅ Credit/Debit Cards (International)
- ✅ Apple Pay, Google Pay
- ✅ Various international payment methods

### 3. Mock Payment (Testing)
- ✅ No setup required
- ✅ Perfect for development and testing
- ✅ No real money charged

## Quick Setup

### Option A: Use Razorpay (Best for India)

1. **Get Razorpay Keys:**
   - Sign up at [razorpay.com](https://razorpay.com)
   - Go to Settings → API Keys
   - Copy Key ID and Key Secret

2. **Set Environment Variables:**
   ```powershell
   $env:RAZORPAY_KEY_ID="rzp_test_your_key_id"
   $env:RAZORPAY_KEY_SECRET="your_key_secret"
   ```

3. **Restart the app:**
   ```bash
   python app.py
   ```

### Option B: Use Stripe (International)

1. **Get Stripe Keys:**
   - Sign up at [stripe.com](https://stripe.com)
   - Go to Developers → API Keys
   - Copy Publishable Key and Secret Key

2. **Set Environment Variables:**
   ```powershell
   $env:STRIPE_SECRET_KEY="sk_test_your_key"
   $env:STRIPE_PUBLISHABLE_KEY="pk_test_your_key"
   ```

3. **Restart the app**

### Option C: Use Mock Payment (No Setup)

- Just use the website as-is
- Click "Complete Mock Payment" at checkout
- Perfect for testing

## How It Works

1. **Customer adds items to cart**
2. **Proceeds to checkout**
3. **Selects payment method:**
   - Razorpay (UPI/Cards/Wallets) - if configured
   - Stripe (Cards) - if configured
   - Mock Payment - if no gateways configured
4. **Completes payment**
5. **Order is processed**

## Testing

### Razorpay Test Credentials:
- **UPI:** `success@razorpay` (success) or `failure@razorpay` (failure)
- **Card:** `4111 1111 1111 1111` (success)
- **Net Banking:** Any bank (test mode)

### Stripe Test Card:
- **Card:** `4242 4242 4242 4242`
- Use any future expiry, any CVV

## Current Status

The website automatically detects which payment methods are available:
- ✅ **Razorpay Enabled** → Shows UPI/Cards/Wallets option
- ✅ **Stripe Enabled** → Shows Card payment option
- ✅ **Both Enabled** → Shows both options
- ❌ **None Enabled** → Shows Mock Payment option

## Need Help?

- **Razorpay Setup:** See `RAZORPAY_SETUP.md`
- **Stripe Setup:** See `STRIPE_SETUP.md`
- **Issues:** Check the console for error messages

## Security Notes

- Never commit API keys to version control
- Use test keys for development
- Switch to live keys only in production
- Keep your keys secure

