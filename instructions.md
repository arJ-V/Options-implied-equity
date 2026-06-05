# Options-Implied Signals — Exact Definitions Reference

Hand each section to Cursor as the spec for one file in `signals/`. Every signal is computed **per (date, underlying)** and produces one number that day. Conventions with more than one valid choice are flagged ⚠️ — pin them down before Cursor implements, or you'll get a plausible-but-wrong feature.

All IVs are annualized. All formulas assume you've already built the standardized surface (§0). Lag everything per the timing rule in §8.

---

## 0. Shared input: the standardized surface (build this first)

Raw chains are unusable directly. For each (date, underlying) produce a clean grid:

**Filters (apply before anything):** drop quotes with zero bid, crossed/locked markets, bid-ask spread > [50%] of mid, open interest < [threshold], |moneyness| outside [0.70, 1.30], and time-to-expiry outside [7, 365] days. ⚠️ These thresholds are research choices — expose them all as parameters.

**Interpolate to a fixed grid** per (date, underlying):
- **Deltas:** put side at Δ = −0.10, −0.25, −0.50; call side at Δ = +0.10, +0.25, +0.50. (Δ = ±0.50 ≈ ATM.)
- **Constant maturities:** 30, 60, 90 calendar days.
- Method: interpolate IV across log-moneyness (or delta) within each expiry, then interpolate across maturity in **total variance** (IV²·T), not raw IV — interpolating raw IV across time is a subtle bug. ⚠️

Output table columns: `date, underlying, iv_p10_30, iv_p25_30, iv_atm_30, iv_c25_30, iv_c10_30, ...` for each maturity.

> If your vendor (ORATS, OptionMetrics) ships a pre-standardized surface, use it and skip this — but confirm their delta and maturity conventions match what the formulas below assume.

---

## 1. Volatility smirk (skew)

**Reference:** Xing, Zhang & Zhao (2010).

**Canonical (XZZ) definition:**
```
SMIRK = IV(OTM put) − IV(ATM call)
```
where, on each (date, underlying):
- OTM put = put with moneyness K/S in [0.80, 0.95)
- ATM call = call with moneyness K/S in [0.95, 1.05)
- time to expiry in [10, 60] days
- ⚠️ if multiple contracts qualify, take the one **nearest** the bin center (XZZ) or the liquidity-weighted average — choose one and document it.

**Recommended robust variant (delta-standardized, preferred for a clean panel):**
```
SMIRK = iv_p25 − iv_atm     (at the 30-day maturity)
```
i.e. 25-delta put IV minus ATM IV. Less sensitive to which strikes happen to be listed.

**Sign:** higher SMIRK (steeper put skew) → **lower** future returns (bearish). So you go **short** high-smirk names.

**Pitfalls:** mixing the moneyness-based and delta-based definitions across the codebase; not requiring both legs to exist on the same date.

---

## 2. Risk reversal

**Definition (25-delta, at a chosen maturity, e.g. 30d):**
```
RR = iv_c25 − iv_p25
```
call IV at Δ=+0.25 minus put IV at Δ=−0.25 (|Δ|=0.25).

**Normalized variant (comparable across names with different vol levels):**
```
RR_norm = (iv_c25 − iv_p25) / iv_atm
```

**Sign convention — state it explicitly:** RR > 0 means calls richer than puts (bullish tilt); equities usually sit at RR < 0 (puts richer). A *less negative / rising* RR is the bullish signal. ⚠️ Decide and document whether your feature is `iv_c25 − iv_p25` or the reverse; getting this backwards silently flips the strategy.

**Pitfalls:** the put's delta is **negative** — "25-delta put" means Δ=−0.25, i.e. |Δ|=0.25. Make sure the surface grid uses that convention.

---

## 3. Put–call IV spread (deviation from put-call parity)

**Reference:** Cremers & Weinbaum (2010).

**Definition — open-interest-weighted average over matched (same strike K, same maturity T) call/put pairs:**
```
VS = Σ_j  w_j · (IV_call,j − IV_put,j)

w_j = (OI_call,j + OI_put,j) / Σ_k (OI_call,k + OI_put,k)
```
Sum over all pairs *j* where both a call and a put exist at the same (K, T) with valid two-sided quotes (after §0 filters).

**Sign:** VS > 0 (call IV exceeds put IV) → **positive** future returns. Go **long** high-VS names.

**Pitfalls:** this one is **pair-matched on raw listed strikes**, not on the interpolated delta grid — don't feed it interpolated IVs. Require genuine same-(K,T) call+put pairs. Weight by the *pair's* average OI, normalized to sum to 1.

---

## 4. Term-structure slope

**Definition (ATM, difference form):**
```
TS_SLOPE = iv_atm_90 − iv_atm_30
```
long-maturity ATM IV minus short-maturity ATM IV. ⚠️ Pick the maturity pair (30/90 is common; 30/60 also fine) and keep it fixed.

**Ratio variant:** `iv_atm_30 / iv_atm_90` (values > 1 = inverted/backwardated).

**Sign:** inversion (short > long, i.e. TS_SLOPE < 0) signals near-term stress / elevated event risk → typically bearish near-term. Confirm direction empirically; don't assume.

**Pitfalls:** earnings/event dates spike the front month — decide whether to exclude names with earnings inside the short window (recommended; expose as a flag).

---

## 5. Implied minus realized vol (variance-risk-premium proxy)

**Definition:**
```
VRP = iv_atm_30 − RV_21

RV_21 = sqrt(252) · stdev( daily log returns over trailing 21 trading days )
```
⚠️ **Match horizons and annualization.** 30 calendar days ≈ 21 trading days. Both terms must be annualized vols (the √252 does that for RV; vendor IV is already annualized). Use trailing returns strictly **before** the signal date (no lookahead).

**Sign:** interpretation varies at single-name level — define the feature cleanly and let the backtest tell you the direction rather than asserting it.

**Pitfalls:** mixing variance and vol units; using a realized window that overlaps the forward-return period.

---

## 6. Model-free implied skewness (advanced — Phase 2+)

**Reference:** Bakshi, Kapadia & Madan (2003); Conrad, Dittmar & Ghysels (2013).

Risk-neutral moments from a strip of OTM options across **all** strikes at a fixed maturity τ. Define three replicating-portfolio prices via numerical integration over OTM calls C(K) and OTM puts P(K) (OTM relative to forward/spot S):

```
V(τ) = ∫_{S}^{∞} [2(1 − ln(K/S)) / K²]·C(K) dK
     + ∫_{0}^{S} [2(1 + ln(S/K)) / K²]·P(K) dK            (quadratic / variance)

W(τ) = ∫_{S}^{∞} [ (6·ln(K/S) − 3·ln(K/S)²) / K² ]·C(K) dK
     − ∫_{0}^{S} [ (6·ln(S/K) + 3·ln(S/K)²) / K² ]·P(K) dK   (cubic)

X(τ) = ∫_{S}^{∞} [ (12·ln(K/S)² − 4·ln(K/S)³) / K² ]·C(K) dK
     + ∫_{0}^{S} [ (12·ln(S/K)² + 4·ln(S/K)³) / K² ]·P(K) dK   (quartic)
```

Then with r = risk-free rate:
```
μ = e^{rτ} − 1 − (e^{rτ}/2)·V − (e^{rτ}/6)·W − (e^{rτ}/24)·X

IMPLIED_SKEW = [ e^{rτ}·W − 3μ·e^{rτ}·V + 2μ³ ] / ( e^{rτ}·V − μ² )^{3/2}
```

**Sign:** more negative implied skew → historically associated with **higher** subsequent returns (CDG). Verify in-sample.

**Pitfalls (this is the error-prone one):** results are highly sensitive to ⚠️ the strike grid and its range — sparse or truncated OTM wings bias the integrals badly. Use fine interpolation across strikes, a wide moneyness range, and a consistent integration rule (trapezoidal). Validate by recovering a near-symmetric skew on an index with a known smile. Gate behind Phase 2 and unit-test against a synthetic Black–Scholes chain (should yield skew ≈ 0).

---

## 7. Options order flow (Phase 3 — needs signed/opening volume)

**Reference:** Pan & Poteshman (2006). **Requires IvyDB Signed Volume or equivalent** — ordinary chains don't have it.

**Put-buy ratio from opening buyer-initiated volume:**
```
PC_FLOW = OpenBuy_PutVolume / (OpenBuy_PutVolume + OpenBuy_CallVolume)
```
**Sign:** high PC_FLOW (heavy opening put buying) → **negative** future returns (informed bearish flow).

**O/S ratio (Roll–Schwartz–Subrahmanyam) — works without signing:**
```
OS = TotalOptionVolume(contracts·100) / StockVolume(shares)
```
a relative-informedness / attention proxy.

**Pitfalls:** "opening" vs "closing" and "buyer-" vs "seller-initiated" classification is the whole signal — without that decomposition you only have crude put/call volume ratios, which are far weaker.

---

## Quick reference table

| Signal | Formula core | Predicts | Data beyond standard surface |
|---|---|---|---|
| Smirk | `iv_p25 − iv_atm` | high → short | — |
| Risk reversal | `iv_c25 − iv_p25` | high → long | — |
| Put–call IV spread | OI-wtd `IV_call − IV_put` over (K,T) pairs | high → long | raw paired quotes + OI |
| Term slope | `iv_atm_90 − iv_atm_30` | inversion → bearish | — |
| IV − RV | `iv_atm_30 − RV_21` | test direction | trailing equity returns |
| Implied skew (BKM) | strike-strip integrals | more neg → long | full OTM strike strip |
| Order flow | opening put-buy ratio | high → short | signed/opening volume |

---

## Before you let Cursor run these

1. **Sign audit.** For each signal, write one sentence: "feature > 0 means the market is [bullish/bearish] on this name, so I expect [higher/lower] forward return." If you can't, the sign convention isn't pinned.
2. **Same-date completeness.** A signal is only valid on dates where all its legs exist post-filter; emit NaN otherwise, never a partial number.
3. **Lag.** Every input must be known strictly before the forward-return window opens (see build spec §7). This is the leakage check that matters most.
4. **BKM unit test.** Feed a synthetic Black–Scholes chain → implied skew must come back ≈ 0. If it doesn't, your integration or strike grid is wrong, not the data.