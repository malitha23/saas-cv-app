# 💳 PayHere Integration & Feature Switch Guide
### DreemFolio AI — Startup Mode vs. Full/Plus Mode Documentation

> **IMPORTANT**: කිසිදු Backend කේතයක් (Backend logic), Database Tables, හෝ Discount Engines පද්ධතියෙන් ඉවත් කර (delete කර) **නැත**.  
> පද්ධතියේ සියලුම Advanced Features (USD Currency, PayHere Subscription Manager REST API, Multi-duration passes) 100% ක් සුරක්ෂිතව පවතී.  
> මෙම ලේඛනයෙන් විස්තර කරන්නේ **PayHere Lite (Free Plan)** සඳහා Customer UI එක සරල කර ඇති ආකාරය සහ අනාගතයේදී **PayHere Plus / Premium** වෙත Upgrade කළ විට එය නැවත Active කරන ආකාරයයි.

---

## 1. 📌 වත්මන් තත්වය (Current State: PayHere Lite Mode)

* **PayHere Plan:** **LITE (Free - No monthly fee)**
* **සහය දක්වන ගෙවීම්:** ශ්‍රී ලංකා රුපියල් (LKR) වලින් සිදුකරන **Prepaid One-Time Payments** පමණි.
* **Customer UI හැසිරීම:**
  * Currency Switcher (USD / Global toggle) එක Normal Users ලාට නොපෙනෙන සේ Hide කර ඇත.
  * සියලුම මිල ගණන් **LKR (රුපියල්)** වලින් පමණක් දිස්වේ (උදා: 1 Month = Rs. 990, 3 Months = Rs. 2,490, 6 Months = Rs. 4,490, 1 Year = Rs. 7,990, Lifetime = Rs. 14,990).
  * Recurring / Auto-debit වචන වෙනුවට **"Prepaid Job-Hunt Pass (One-Time Checkout)"** ලෙස පැහැදිලිව පෙන්වයි.
  * Customer Profile (`/profile`) එකේ සක්‍රිය Pass එකේ ඉතිරි දින ගණන, ගෙවීම් ඉතිහාසය (Order History) සහ **"Request Refund"** බොත්තම පවතී.

---

## 2. 📂 වෙනස්කම් සිදුකර ඇති ස්ථාන (Exact File Locations & Code)

### 🔹 File 1: `app/static/app.js`

#### A. Global Feature Flag (Line ~204)
```javascript
// ═══════════════════════════════════════════════════════════════════════════
// PAYHERE LITE MODE FEATURE SWITCH (See PAYHERE_LITE_MODE_GUIDE.md in root)
// ═══════════════════════════════════════════════════════════════════════════
// When true: Hides USD / foreign currency toggles on Customer UI & locks to LKR One-Time Payments.
// When false: Enables multi-currency (USD/LKR) and PayHere Recurring Billing.
payhereLiteMode: true,
```

#### B. Dynamic Currency Enforcement in `loadDynamicPlans()` (Line ~2340)
```javascript
async loadDynamicPlans(countryCode = null) {
  try {
    // In PayHere Lite Mode, strictly lock to Sri Lanka (LK / LKR)
    const code = this.payhereLiteMode ? 'LK' : (countryCode || this.activeCountryCode || 'LK');
    const res = await fetch(`/api/subscription/plans?country=${encodeURIComponent(code)}`);
    if (res.ok) {
      const data = await res.json();
      if (data.plans && data.plans.length > 0) {
        this.dynamicPlans = data.plans;
      }
      if (this.payhereLiteMode) {
        this.activeCountryCode = 'LK';
        this.activeCurrency = 'LKR';
        this.activeCurrencySymbol = 'Rs. ';
      } else {
        if (data.country_code) this.activeCountryCode = data.country_code;
        if (data.currency) this.activeCurrency = data.currency;
        if (data.currency_symbol) this.activeCurrencySymbol = data.currency_symbol;
      }
...
```

---

### 🔹 File 2: `app/templates/components/modals/pricing_modal.html`

#### Currency Switcher Hide / Show (Line ~52)
```html
<!-- Currency Switcher Pill inside Pricing Modal (Active when payhereLiteMode is false) -->
<div x-show="!payhereLiteMode" class="flex items-center bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs">
  <template x-for="c in availableCountries" :key="c.code">
    <button @click="selectCountryCurrency(c.code)"
      class="px-2.5 py-1 rounded-lg font-bold transition flex items-center gap-1 text-[11px]"
      :class="activeCountryCode === c.code ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'">
      <span x-text="c.symbol"></span>
      <span x-text="c.currency"></span>
    </button>
  </template>
</div>

<!-- PayHere Lite Mode Badge (Active when payhereLiteMode is true) -->
<div x-show="payhereLiteMode" class="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-300 font-bold shadow-sm">
  <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
  <span>LKR (Rs.) • Prepaid Passes</span>
</div>
```

---

### 🔹 File 3 & 4 (Backend - 100% Untouched & Ready):
* **`app/services/payhere.py`**:
  * `create_checkout_payload()` — Generates MD5 security hash for both LKR and USD orders.
  * `verify_ipn_signature()` — Verifies IPN callback authenticity.
  * `PayHereSubscriptionClient` — OAuth 2.0 client for PayHere Subscription Manager API (`/merchant/v1/subscription`, `/retry`, `/cancel`).
* **`app/routers/payments.py`**:
  * Multi-duration checkout (`1m`, `3m`, `6m`, `12m`, `lifetime`).
  * Currency handling for both `LKR` and `USD`.
  * IPN automated duration extension and webhook listeners.

---

## 3. 🚀 අනාගතයේදී PayHere Plus / Premium වලට Upgrade කරන ආකාරය (How to Restore / Upgrade)

ඔබ PayHere ගිණුම **PayHere Plus** (LKR 3,990/mo) හෝ **Premium** වලට Upgrade කළ පසු, නැවත USD සහ Full International Currency විකල්ප සක්‍රිය කිරීමට කළ යුත්තේ **එකම එක් පියවරකි**:

### පියවර 1: Flag එක වෙනස් කරන්න
`app/static/app.js` ගොනුවේ **Line ~204** හි ඇති අගය `false` කරන්න:

```javascript
// පෙර:
payhereLiteMode: true,

// පසු (Plus / Premium සක්‍රිය කිරීමට):
payhereLiteMode: false,
```

### පියවර 2: Browser Refresh කරන්න
* Browser Cache එක Clear කර හෝ `Ctrl + F5` ගසන්න.
* දැන් ක්ෂණිකව Pricing Modal එකෙහි **LKR (Rs.) / USD ($) Switcher** එක දිස්වේ.
* පිටරටින් පැමිණෙන පාරිභෝගිකයින්ට ඔවුන්ගේ රට අනුව USD මිල ගණන් ස්වයංක්‍රීයව පෙන්වයි.

---

## 4. 📊 PayHere Plans සන්සන්දනය (Reference Table)

| Feature | PayHere LITE (දැනට භාවිතා වන) | PayHere PLUS | PayHere PREMIUM |
| :--- | :---: | :---: | :---: |
| **මාසික ගාස්තුව (Monthly Fee)** | **රු. 0 (Free)** | රු. 3,990 / mo | රු. 9,990 / mo |
| **Transaction Processing Fee** | 3.30% | 2.99% | 2.69% |
| **One-time Payments (LKR)** | ✅ ඔව් (උපරිම රු. 50,000) | ✅ ඔව් (උපරිම රු. 250,000) | ✅ ඔව් (උපරිම රු. 1,000,000) |
| **USD Payouts & Foreign Currency** | ❌ නැත | ✅ ඔව් | ✅ ඔව් |
| **Automated Recurring Billing** | ❌ නැත | ✅ ඔව් | ✅ ඔව් |
| **DreemFolio Multi-Duration Passes** | ✅ **100% ක්‍රියාත්මකයි** | ✅ **100% ක්‍රියාත්මකයි** | ✅ **100% ක්‍රියාත්මකයි** |

---

*Document Generated: 2026-09-17*  
*DreemFolio AI Architecture Team*
