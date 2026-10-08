# PaySense: AI-Driven System for Financial Health Forecasting and BNPL Risk Classification
### (PaySense: Gen-Z Financial Copilot)

**Version:** 19.0 — September 2026  
**Student:** Nur Farah Binti Ahmad Nazri (22007916)  
**Supervisor:** Dr. Nazleeni Samiha Bt Haron  
**Institution:** Universiti Teknologi PETRONAS — Bachelor of Computer Science (Hons)  
**Area:** Computer Science (Data Analytics)  
**Grand Challenge:** Sustainable Living  
**Research Theme:** Inclusive and Equitable Development

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | May 2025 | Initial concept document |
| 2.0 | June 2025 | Major revision: confirmed ML model candidates (ARIMA, Prophet, LSTM for forecasting; Random Forest, XGBoost, LightGBM for classification), updated tech stack (Next.js, Supabase, FastAPI), added detailed model evaluation plan, two-semester Gantt chart, open-source references, and architecture details |
| 3.0 | June 2026 | Literature review integration: expanded from 5 to 30 papers across 7 domains (2021–2026), added full Literature Review Matrix (Section 10.2), 5 Research Gaps (Section 10.3), updated Kaggle dataset to ramyapintchy Personal Finance Data (2020–2024), expanded references to all 30 papers |
| 4.0 | June 2026 | ML training complete: Engine 1 winner (ARIMA, RMSE = 7,300.30) and Engine 2 winner (XGBoost, F1 = 0.8718, ROC-AUC = 0.8751, Recall = 0.8500) documented with full 3-model empirical comparison tables (Section 8.3) |
| 5.0 | July 2026 | Engine 2 dataset regenerated with Malaysian-literature-grounded distributions (age from Tan et al. 2026; employment and income from Osman et al. 2024); XGBoost confirmed as winner on updated dataset (F1 = 0.8732, ROC-AUC = 0.8756, Recall = 0.8455); Section 8.3 updated with new results and dataset justification |
| 6.0 | July 2026 | RQ/Objectives finalized per supervisor and proposal defence alignment: UAT added to Objective 3; tool comparison table in Section 3 corrected (removed factually incorrect RinggitWise/Moomoo MY entries, replaced with verified 5-tool feature comparison used in defence slides); Section 5.1 Dataset Sources updated to reflect actual personal dataset (808 transactions, May 2025–Apr 2026, farah_spending_history.xlsx) and new Generalisation Test row added; Out of Scope list in Section 9 reconciled with defence slides (7-item version); title updated to match slide branding |
| 7.0 | July 2026 | Reconciled document with actual implementation: Section 8.2 input feature list replaced with the true 11 trained features (age, employment_status, monthly_income, monthly_expenses, num_bnpl_plans, bnpl_outstanding, missed_payments, forecasted_cash_flow, income_expense_ratio, bnpl_income_ratio, savings_rate); clarified Engine 2 is a **binary** classifier (bnpl_risk 0/1) with the 3-tier label produced by rule-based bucketing of the predicted probability, not a native 3-class output; renamed risk tiers to **Safe / Caution / At Risk** to match the actual dashboard mockup wording (previously "Safe / At Risk / Danger", which collided with the mockup's own tier names); fixed Section 5.2 class-imbalance statistic (actual dataset is ~74% High Risk / ~26% Low Risk, not 80–90% Safe as previously stated); Section 11 timeline restructured to reflect that model training for both engines was completed during FYP1, ahead of the original FYP2 schedule |
| 8.0 | September 2026 | **Engine 2 label-design fix + retrain.** Live Risk Checker testing surfaced a labelling flaw: the synthetic training label used hard binary thresholds (`missed_payments` only counted at ≥2; `bnpl_income_ratio` gave a flat +2 regardless of being 51% or 500% of income), verified via SHAP on a real case (a 115%-of-income purchase scored "safe", P(risk)=0.08, because `missed_payments`'s SHAP contribution of −3.13 overrode `bnpl_income_ratio`'s +1.13). Fixed by replacing each threshold with a continuous, linearly-scaled term (same calibration point retained); relabelled the 2,000-row dataset and retrained all three candidates. **LightGBM is the new winner** (F1 0.8555, ROC-AUC 0.8987, Recall 0.8087), replacing XGBoost. Section 8.3 updated with the new comparison table, winner, and class-balance shift (74.1%/25.9% → 60.9%/39.1% High/Low Risk). Full trace in `docs/KNOWN_LIMITATIONS.md`; regression-guarded by `backend/tests/test_engine2_calibration.py`. `models v2/` (the v7.0-era artefacts) is kept unmodified as historical provenance; new artefacts are in `models v3/`. |
| 9.0 | September 2026 | **Savings tracking + limitations/future-work documentation.** Comparing Engine 1's forecast against actual May–July 2026 spending surfaced two unmodelled behaviours: income received early and spent across a month boundary, and a deliberate lump sum set aside for a future trip that wasn't logged as a transaction at all. Added Savings tracking with two mechanisms — recurring savings via a new `Savings` category under the existing `Expense` type (zero schema change), and one-off/goal savings via a new `savings` transaction type (excluded from spending-category breakdowns and Engine 1's forecast input, but still reduces available balance once re-synced). Updated Sections 5.3, 7.2, 7.3, 7.6, 8.1, and 8.2 accordingly. Added a **Known Limitations** block (self-reported data completeness, calendar-month vs. pay-cycle timing noise, manual balance sync) and a **Future Improvements** block (ledger-derived running balance, multi-account balance) to Section 9. |
| 10.0 | September 2026 | **Future Improvements: Engine 1 fixed/variable decomposition.** Added a documentation-only Future Improvements entry to Section 9 proposing that Engine 1 subtract known fixed outflows (rent, bills, BNPL instalments) before forecasting and run ARIMA only on the discretionary residual, then add the two back together. Records the expected modest benefit, the caveat that MAPE will likely stay poor regardless (Section 8.3 note), and the rationale for deferring it. No code, models, or previously reported metrics changed. |
| 11.0 | September 2026 | **Future Improvements: fuzzy / Fuzzy C-Means label logic for Engine 2.** Added a documentation-only Future Improvements entry to Section 9 covering the remaining limitation of the v8.0 label-design fix (continuous-scaling boundaries are manually chosen, not data-derived) and a proposed refinement using fuzzy membership functions with Fuzzy C-Means-derived parameters. Records that the direction is being explored in consultation with UTP faculty, its current status, and the caveat that synthetic labels limit what data-derived boundaries can show. No code, models, or previously reported metrics changed. |
| 12.0 | September 2026 | **Future Improvements: anchor Engine 1's forecast to the current date.** Added a documentation-only Future Improvements entry to Section 9 describing a limitation found during evaluation: the forecast starts from the last logged month while the balance curve starts from today, so a stale transaction log leaves the curve without forecast net cash flow and omits a proposed purchase's instalments from Engine 2's forecasted-cash-flow feature. Records the proposed change and why it is deferred. No code, models, or previously reported metrics changed. |
| 13.0 | September 2026 | **Savings type built and migrated; ledger-derived balance built, not yet activated.** A large one-off savings entry, logged as a normal expense, made `auto_arima` collapse the forecast to ARIMA(0,0,0); a dedicated `savings` transaction type (excluded from spending breakdowns and Engine 1's input) and an optional ledger-derived balance mode were built and tested, and the entry was reclassified. Reforecast restored ARIMA(1,0,0). *(Details of the author's personal transactions removed from this public copy.)* |
| 14.0 | September 2026 | **Future Improvements: income example added to the fixed/variable decomposition item.** Documentation-only. Added a concrete worked example inside the existing Section 9 decomposition entry (not a new entry): the income bar on the 6-month chart is a by-product of splitting trailing averages to match ARIMA's net forecast, so it showed a forecast income that differed from the author's fixed monthly income; and ARIMA reacts to a changed income for only about one month before decaying back toward zero. Records the caveats (changes all downstream figures, no accuracy gain on this dataset, affects the ARIMA-selection evidence) and that the chart is deliberately left unchanged during Engine 1/2 testing. No code, models, or previously reported metrics changed. |
| 15.0 | September 2026 | **Engine 1 description reconciled with the implementation; live evaluation on personal data.** Sections 7.6 and 8.1 rewritten to describe what is actually built (univariate ARIMA on monthly net cash flow, refit per request; income/expense bars derived from the net forecast; balance curve = pro-rata net plus BNPL instalments) instead of the earlier multi-feature description. Section 8.3 gains a live check of the April-cutoff forecast against real May–Jul 2026 spending (MAE RM168.51, MAPE 20.8%, one-off savings transfer excluded) and a 15-month rolling-origin backtest against naive and moving-average baselines, which supersede the informal 35.5% figure (based on recalled, partly mis-summed actuals). Section 5.1 lists the May–Jul 2026 data (180 rows; 988 in total); Sections 5.3/7.2 note the optional ledger mode; the recurring-savings category is spelled `Saving` to match the stored data; Known Limitations gain the partially logged April 2026, the fragility of a short history, and the early-disbursement income handling. Documentation only — no code, models, or Section 8.3 Kaggle results changed. |
| 16.0 | September 2026 | **Engine 2 model re-evaluation; deployed model switched to Random Forest + Platt calibration.** The Section 8.3 winner (LightGBM) came from one ~300-row test split where the three candidates differ by ~0.003 F1 (about one row). Re-compared with 5×5 repeated stratified cross-validation, corrected resampled t-tests, calibration metrics and an oracle ceiling: XGBoost and LightGBM tie; Random Forest is significantly better on ROC-AUC and Brier score. Nested CV then chose sigmoid (Platt) calibration over isotonic and none. Deployed model changed to Random Forest + Platt calibrator (`models v4/`); SHAP wiring re-verified against the new model (additivity, shape, feature order, calibration monotonicity); SHAP/comparison plots regenerated; UI/docs naming updated. Records that all candidates used hand-set, untuned hyperparameters, and that `forecasted_cash_flow` is a weak feature (near-constant at serving). Monotonic constraints and decision-threshold tuning recorded as future work. |
| 17.0 | September 2026 | **Provider-aware instalment schedules.** Research on how Malaysian BNPL providers actually bill (`docs/BNPL Billing Rules SPayLater, TikTok PayLater, Atome (Malaysia).md`) showed the Risk Checker started every schedule on the purchase date, which is right only for Atome. Provider list is now SPayLater, TikTok PayLater, Atome and Other (GrabPayLater and PayLater by Boost dropped). SPayLater and TikTok PayLater start the first payment one month after the purchase, same day, for both (a single flagged assumption; SPayLater's billing-cycle days and TikTok's first due date are unconfirmed, one informal user report supports next-month billing for TikTok); Atome starts on the purchase date with the first payment charged at checkout and stored as already paid. The fee stays a manual, user-entered field. Effects on Engine 2: `missed_payments` no longer risks a phantom miss from a wrong first due date, `bnpl_outstanding` excludes the prepaid part, and `forecasted_cash_flow` and the balance projection follow the provider's timing. No retraining needed (features are aggregates). |
| 18.0 | September 2026 | **Monthly fee rate and provider configuration.** The BNPL fee field is now the provider's monthly rate (as shown at checkout) with total = price x (1 + rate x instalments), computed in integer sen with instalments rounded down and the leftover sen in the last instalment. Provider rules are data (one config entry per provider): SPayLater and TikTok PayLater start one month after the purchase, same day (an editable estimate; SPayLater's real billing cycles are unconfirmed and not modelled); Atome charges the first payment at checkout. No stored data needed migration; older risk checks convert their whole-plan fee on confirm. |
| 19.0 | September 2026 | **Engine 2 serving/training consistency fix.** Testing showed the app served `bnpl_income_ratio` as monthly instalment burden / income while the model was trained on total BNPL debt / income, understating risk. The app now serves the training definition (message: "Your total BNPL debt is X% of your monthly income"); a monthly-burden definition with a regenerated dataset and retrain is recorded as future work. The synthetic `missed_payments` assumption (average about 3) versus careful real users, and the risk of unmarked-but-paid instalments inflating it, are recorded as known limitations. Near-zero SHAP factors are no longer shown as reasons. |

---

## 1. Research Question

> How can an AI-driven predictive system, combining time-series cash flow forecasting and BNPL risk classification, be developed to support informed BNPL purchasing decisions among Malaysian university students?

---

## 2. Research Objectives

1. To evaluate 3 candidate time-series forecasting models (ARIMA, Prophet, LSTM) and 3 candidate BNPL risk classification models (Random Forest, XGBoost, LightGBM), selecting the best-performing model for each based on empirical evaluation metrics.

2. To develop a **Financial Health Forecasting Engine** that projects a user's rolling bank balance, and a **BNPL Risk Classification Engine** that assesses the risk of a proposed purchase before commitment.

3. To design and deploy an **interactive PaySense web dashboard** with explainable AI (XAI) insights, and evaluate its usability among Malaysian university students via User Acceptance Testing (UAT).

---

## 3. Problem Statement

Traditional personal finance apps are reactive digital ledgers — they log historical spending but don't forecast future cash flows. This is a critical gap for Malaysian university students who heavily rely on BNPL services.

**Key statistics:**
- Malaysian BNPL market has reached **RM9.3 billion** in spending
- Gen-Z students are among the heaviest adopters due to limited income and no access to traditional credit
- Despite high self-reported financial literacy (M = 4.07/5), the correlation with actual debt management behaviour is very weak (r = 0.060) — the **Knowledge-Action Gap**
- Dominant predictor of BNPL usage: **Perceived Behavioural Control** (Beta = 0.694) — students overestimate their repayment ability

### Core Problems

| # | Problem |
|---|---------|
| 1 | Existing finance apps are reactive ledgers, not predictive tools |
| 2 | BNPL instalment stacking creates invisible future cash flow crises |
| 3 | Students cannot assess the impact of new purchases against future projected balances before committing |
| 4 | No AI-driven system combines time-series forecasting AND BNPL risk classification for Malaysian students |

### Gap in Existing Solutions

| Tool | Historical Tracking | Cash Flow Forecasting | Internal Credit Check | Multi-App View | Explainable AI (XAI) |
|------|:-------------------:|:---------------------:|:---------------------:|:--------------:|:--------------------:|
| ANIKA by IBPO | ✓ | ✗ | ✗ | ✗ | ✗ |
| UOB Mighty Insights | ✓ | ✗ | ✗ | ✗ | ✗ |
| Atome | ✗ | ✗ | ✓ | ✗ | ✗ |
| SPayLater | ✗ | ✗ | ✓ | ✗ | ✗ |
| GrabPayLater | ✗ | ✗ | ✓ | ✗ | ✗ |
| **PaySense (This Project)** | **✓** | **✓** | **✓** | **✓** | **✓** |

---

## 4. Machine Learning Model Evaluation Plan

Both AI engines follow a **compare-3-pick-1** approach. All candidate models are trained, tested, and compared on the same dataset. The best-performing model per engine is selected and integrated into the final system.

### 4.1 Engine 1 — Cash Flow Forecasting (Time-Series)

Models are trained on historical transaction data to project the user's bank balance month-by-month for the next 3 months.

| Model | Type | Strengths | Weaknesses | Reference |
|-------|------|-----------|------------|-----------|
| **ARIMA** | Statistical Time-Series | Computationally efficient, interpretable, well-established for short-horizon forecasting | Assumes linearity; struggles with irregular spending patterns and missing dates | Box & Jenkins (1970); Weytjens et al. (2021) |
| **Prophet** | Additive Time-Series (Facebook) | Handles seasonality natively (monthly allowance cycles); robust to missing dates; minimal tuning | Higher error on short-term daily fluctuations | Taylor & Letham (2018); Yadav (2022) |
| **LSTM** | Deep Learning (Recurrent NN) | Highest accuracy for complex, long-term patterns; captures non-linear spending behaviour | Requires more data and compute; less interpretable | Weytjens et al. (2021); Yadav (2022) |

**Evaluation Metrics:**

| Metric | Description |
|--------|-------------|
| MAE (Mean Absolute Error) | Average absolute difference between predicted and actual balance — lower is better |
| RMSE (Root Mean Square Error) | Penalises large prediction errors more heavily — lower is better |
| MAPE (Mean Absolute Percentage Error) | Percentage-based error, useful for comparing across scales |

> **Selection criterion:** Lowest RMSE on the test set. If RMSE values are close, MAE and MAPE are used as tiebreakers.

---

### 4.2 Engine 2 — BNPL Risk Classification

Ensemble classification models trained on synthetic BNPL scenario data to predict **binary BNPL risk** (`bnpl_risk`: 0 = Low Risk, 1 = High Risk) given the user's profile and forecasted future balance. The predicted risk probability is then mapped to a 3-tier, user-facing label — **Safe**, **Caution**, or **At Risk** — via rule-based probability thresholds (Section 8.2). The 3-tier label is a post-hoc bucketing layer, not a native 3-class model output.

| Model | Type | Strengths | Weaknesses | Reference |
|-------|------|-----------|------------|-----------|
| **Random Forest** | Ensemble (Bagging) | Robust to overfitting; handles imbalanced data; high recall for risky cases | Lower overall accuracy vs. boosting models | Mittal et al. (2018); XAI paper (2025) |
| **XGBoost** | Ensemble (Gradient Boosting) | Highest accuracy and AUC-ROC in credit risk literature; handles imbalanced datasets with SMOTE; industry standard for fintech | More hyperparameters to tune | Multiple credit risk studies (2022–2024) |
| **LightGBM** | Ensemble (Gradient Boosting) | Fastest training speed; best precision; efficient on large datasets; native SHAP support | Can overfit on small datasets | XAI credit risk paper (2025); Default prediction studies |

**Evaluation Metrics:**

| Metric | Description | Why It Matters |
|--------|-------------|----------------|
| Accuracy | Overall % of correct predictions | Baseline performance measure |
| Precision | Of all predicted 'Risky', how many were actually risky | Avoids false alarms — important for user trust |
| Recall | Of all actual 'Risky' cases, how many were caught | **Critical** — missing a risky case is more harmful than a false alarm |
| F1-Score | Harmonic mean of Precision and Recall | Balanced measure for imbalanced datasets |
| ROC-AUC | Area under the Receiver Operating Characteristic curve | Overall discriminatory power of the classifier |

> **Selection criterion:** Highest average of F1-Score and ROC-AUC (a combined `F1_AUC_avg` metric). **Recall is prioritised over Precision** as a secondary tiebreaker — missing a high-risk case is more harmful than a false alarm. SMOTE applied to address class imbalance before training (train set only).

---

### 4.3 XAI Layer — Explainability

Both engines use **SHAP (SHapley Additive exPlanations)** for explainability. All three Engine 2 candidate models have native SHAP support via the `shap` Python library.

SHAP values are translated into plain-language explanations, e.g.:
> *"Your risk is HIGH because your projected balance drops below RM0 on 15 July due to 3 overlapping BNPL payments."*

---

## 5. Data Strategy

### 5.1 Dataset Sources

| Source | Purpose | Description |
|--------|---------|-------------|
| Kaggle — Personal Finance Data (ramyapintchy) | Engine 1 Training (Forecasting) | Synthetic personal finance transaction records (Jan 2020–Dec 2024) with columns: Date, Transaction Description, Category, Amount, Type (Income/Expense). Download: [kaggle.com/datasets/ramyapintchy/personal-finance-data](https://www.kaggle.com/datasets/ramyapintchy/personal-finance-data) |
| Personal Real Transaction Data (farah_spending_history.xlsx) | Engine 1 Demo Data | 808 transactions across 12 monthly sheets (May 2025–Apr 2026) covering income, categorised expenses, and BNPL instalments — Farah's actual bank records |
| Personal Real Transaction Data (Transaction History (May-July 2026).xlsx) | Engine 1 live data | 180 transactions across 3 monthly sheets (May–Jul 2026), imported after the original file. Income is dated to the month it covers, categories are normalised to the existing scheme (Academic is a new category), and a one-off savings set-aside is stored as a Savings-type transaction. Together with the original file the live series holds 988 transactions over 15 months (May 2025–Jul 2026) |
| Kaggle dataset subset (Jan 2021–Dec 2023) | Engine 1 Generalisation Test | Same file as the primary Kaggle training data, different date window selected for its naturally positive/growing balance trend — used to test whether the trained ARIMA model generalises beyond the negative-trending personal demo case, rather than defaulting to a fixed pessimistic output |
| Synthetic BNPL Scenarios (Generated) | Engine 2 Training (Classification) | 2,000 algorithmically generated, Malaysian-literature-grounded BNPL profiles labelled with a binary risk outcome (`bnpl_risk`: 0 = Low Risk, 1 = High Risk), bucketed into Safe / Caution / At Risk for display |
| User-Inputted Data (Live) | Production Runtime | Transactions entered manually or imported via CSV / PDF bank statement upload |

### 5.2 Dataset Requirements

| Requirement | Why It Matters |
|-------------|----------------|
| Time-series structure with date column | Required for ARIMA, Prophet, and LSTM to learn temporal patterns |
| Minimum 6 months of transaction history | Sufficient data for train/test split and for LSTM to learn long-term dependencies |
| Seasonality present (monthly income cycles) | Validates Prophet's seasonal decomposition capability |
| Handles missing dates / irregular transactions | Real student spending is irregular; Prophet and LSTM handle this better than ARIMA |
| Class imbalance in BNPL risk labels | Actual synthetic dataset is imbalanced toward High Risk: ~74.1% `bnpl_risk = 1` (High Risk) vs. ~25.9% `bnpl_risk = 0` (Low Risk); SMOTE applied to the training set only before classification training |
| Malaysian Ringgit (RM) denomination or convertible | Directly relevant to target user demographic |

### 5.3 Transaction Data Fields

| Field | Type | Description |
|-------|------|-------------|
| Date | Date | Date of transaction (YYYY-MM-DD) |
| Amount (RM) | Float | Transaction value in Malaysian Ringgit |
| Type | Categorical | Income, Expense, or Savings — Savings covers one-off/goal money set aside (e.g. a trip fund); excluded from spending-category breakdowns and Engine 1's forecast input, but still reduces available balance (at the next re-sync by default, or immediately when ledger mode is on; Section 7.2) |
| Category | Categorical | Food, Transport, Shopping, Bills, Saving, BNPL Instalment, etc. |
| Description | Text | Optional free-text note |
| Bank / Account | Text | Which bank account or e-wallet |
| BNPL Flag | Boolean | Indicates if this transaction is a BNPL instalment payment |
| BNPL Plan ID | String | Links the transaction to a specific BNPL plan if flagged |

> **Recurring vs. one-off savings:** a recurring set-aside (e.g. a fixed RM200/month transfer with no end date) is logged as `Type: Expense` + `Category: Saving`, so Engine 1 learns it as a normal predictable outflow. A one-off/goal set-aside with a defined target or end date (e.g. RM1,000 for a trip, even if spread across several months) uses the separate `Type: Savings` instead — this is a deliberate choice at the point of entry, not something the system infers from repetition, since a finite goal spread over a few months can look identical to a recurring pattern by count alone.

### 5.4 BNPL Plan Data Fields

| Field | Type | Description |
|-------|------|-------------|
| Item Name | Text | Name of purchased item |
| BNPL Provider | Categorical | e.g. Atome, Shopee PayLater, GrabPayLater |
| Total Price (RM) | Float | Full purchase value |
| Interest Rate (%) | Float | 0% if none, or applicable rate |
| Total Payable (RM) | Float (Calculated) | Total price + interest |
| Number of Instalments | Integer | e.g. 3, 6, 12 |
| Instalment Amount (RM) | Float (Calculated) | Total payable ÷ number of instalments |
| First Payment Date | Date | Start date of repayment schedule |
| Instalment Due Dates | Date Array | Auto-calculated schedule of all payment dates |
| Status | Categorical | Active / Completed / Overdue |
| Risk Score at Creation | Integer (0–100) | Score generated when the plan was created via Risk Checker |

---

## 6. System Architecture

### 6.1 Sequential AI Architecture

The two AI engines work **sequentially** — this is the core technical novelty of PaySense. The Forecasting Engine's output becomes the evaluation context for the Risk Classifier.

| Step | Action | Engine |
|------|--------|--------|
| 1 | Forecasting Engine runs first. Takes user's historical transaction data (income, spending patterns, existing active BNPL instalments) and generates a projected future balance curve for the next 3 months. | Engine 1 |
| 2 | User proposes a new BNPL purchase: item name, total price, BNPL provider, number of instalments, first payment date, interest rate. | User Input |
| 3 | Risk Classifier uses the forecasted balance curve as its evaluation context. Instead of asking "can you afford this today?", it overlays the new instalment schedule onto the projected balance curve: "will your future balance absorb each payment at every instalment date?" | Engine 2 |
| 4 | System outputs: risk score (0–100), health label (Safe / Caution / At Risk), visual impact overlay on the balance chart, and SHAP-based XAI explanation. | Output |

### 6.2 Technology Stack

| Layer | Technology | Justification |
|-------|-----------|---------------|
| Frontend Framework | **Next.js** (React-based) | Optimal for Vercel deployment; server-side rendering; best ecosystem for dynamic dashboards |
| Styling | **Tailwind CSS** | Utility-first; rapid development; responsive design out of the box |
| Backend / API | **Python with FastAPI** | Modern, async-capable; industry standard for ML model serving; auto-generates API docs |
| Forecasting Model | **ARIMA / Prophet / LSTM** (best selected) | Python-native via statsmodels, prophet, and tensorflow/keras |
| Risk Classifier | **Random Forest / XGBoost / LightGBM** (best selected) | scikit-learn / xgboost / lightgbm Python libraries |
| XAI Library | **SHAP** | Native support for all three candidate classifiers |
| Database | **Supabase (PostgreSQL)** | Open-source; relational structure suits transactions + BNPL plan linkage; free tier available |
| Data Visualisation | **Chart.js or Recharts** (via Next.js) | Lightweight, responsive charts embedded in the web app |
| File Parsing — CSV | **pandas** (Python) | Industry-standard data manipulation library |
| File Parsing — PDF | **pdfplumber** (Python) | Handles Malaysian bank statement PDF formats (Maybank, CIMB, RHB, etc.) |
| Deployment — Frontend | **Vercel** | Native Next.js deployment platform; zero-config; free tier |
| Deployment — Backend | **Render or Railway** | Free-tier Python/FastAPI hosting; supports background workers for model inference |
| Development Tools | VS Code, Jupyter Notebook, Git/GitHub | Model prototyping in Jupyter; version control on GitHub |
| Model Training Environment | **Google Colab (Pro)** | GPU-accelerated LSTM training |

### 6.3 Three-Tier Architecture

```
[Frontend — Next.js on Vercel]
  ↕ REST API calls
[Backend — FastAPI on Render/Railway]
  - Hosts trained ML models (.pkl / .h5)
  - Endpoints: balance forecasting, BNPL risk scoring, SHAP explanations, transaction CRUD, PDF/CSV parsing
  ↕ Supabase Python client
[Database — Supabase (PostgreSQL)]
  - User transaction records
  - BNPL plan records
  - Risk score history
```

### 6.4 Open-Source References

| Repository | URL | Relevance |
|------------|-----|-----------|
| DominicRoyStang / finance-predictor | github.com/DominicRoyStang/finance-predictor | Personal finance ML prediction using transaction CSV — model selection approach reference |
| sergepaulc / Machine-Learning-for-Finance | github.com/sergepaulc/Machine-Learning-for-Finance | scikit-learn and PyTorch ML models for financial applications |
| naveenventuri / Cash-Flow-prediction-master | github.com/naveenventuri/Cash-Flow-prediction-master | SVR, Random Forest, DNN, ensemble models for cash flow |
| Facebook Prophet (official) | github.com/facebook/prophet | Official Prophet library |
| SHAP (official) | github.com/slundberg/shap | Official SHAP library — integrates with all three classifier candidates |
| Supabase Python client | github.com/supabase/supabase-py | Official Supabase Python client for FastAPI backend |
| XGBoost (official) | github.com/dmlc/xgboost | Official XGBoost library |
| LightGBM (official) | github.com/microsoft/LightGBM | Official Microsoft LightGBM library |

---

## 7. Application Features & Screens

PaySense is a fully deployed responsive web application accessible on desktop and mobile browsers via Vercel.

### 7.1 Screen Summary

| Screen | Key Features |
|--------|-------------|
| **Main Dashboard** | Current balance, Financial Health Speedometer (0–100), 6-month bar chart (3 historical + 3 projected), active BNPL list, upcoming payment alerts, Check New BNPL button |
| **Transactions Screen** | Full transaction history, manual entry form, CSV import, PDF bank statement import, category breakdown, balance sync |
| **BNPL Plans Manager** | List of all active/completed BNPL plans, manual plan creation, plan detail view with instalment timeline |
| **BNPL Risk Checker** | Purchase input form, risk score output (0–100), balance impact overlay chart, SHAP explanation panel, top risk factors, recommendation, confirm & save to plans |

---

### 7.2 Main Dashboard

| Feature | Description |
|---------|-------------|
| Current Balance Display | Prominently displays the user's current bank balance. By default this is a manually-synced snapshot, not derived from the transaction log — logging a transaction (Income, Expense, or Savings) does not change it; the user must re-sync via Balance Sync to reflect it. An optional ledger mode (Section 9) makes every logged transaction move the balance automatically, with Balance Sync retained as a correction tool. |
| Income & Expense Summary | Mini cards showing total income and total expenses for the current month. |
| Financial Health Speedometer | Speedometer-style gauge, score 0–100. Labels: **Safe** (green, 70–100), **Caution** (yellow, 40–69), **At Risk** (red, 0–39). Computed by ML risk classifier combined with rule-based thresholds. |
| 6-Month Bar Chart | 3 months of historical spending (actual) + 3 months of projected spending (AI Engine 1). Income and expense bars shown side by side per month. |
| Active BNPL Instalments List | All ongoing BNPL commitments: provider name, item, remaining instalments, amount per instalment, next due date. |
| Upcoming Payment Alerts | Proactive alerts highlighting BNPL payments due within 7 days, flagging if projected balance may be insufficient. |
| Check New BNPL Button | CTA button navigating to the BNPL Risk Checker screen. |

---

### 7.3 Transaction Management

| Feature | Description |
|---------|-------------|
| Manual Transaction Entry | Fields: Amount, Type (Income/Expense/Savings), Category (includes "Saving" for recurring set-asides logged under Expense), Description, Date, Bank/Account Name, BNPL flag toggle. |
| CSV Bank Statement Import | Upload CSV; system parses and maps transactions automatically with a preview screen for user confirmation. |
| PDF Bank Statement Import | Upload PDF from Malaysian banks (Maybank, CIMB, RHB, etc.). Parsed via pdfplumber. Best-effort parsing — user confirmation required. |
| Balance Sync | User can manually override and correct current balance at any time. |
| Transaction History | Full searchable and filterable list of all transactions by month, category, or type, with All / Income / Expense / Savings tabs. |
| Category Breakdown | Visual breakdown of spending by category with percentage bars — reflects Expense-type totals only; one-off Savings-type transactions are excluded, while recurring Savings-category entries (logged under Expense) are included like any other category. |

---

### 7.4 BNPL Plans Manager

| Feature | Description |
|---------|-------------|
| Manual BNPL Plan Creation | User inputs: Item Name, BNPL Provider, Total Price, Interest Rate (%), Number of Instalments, First Payment Date. System auto-calculates each instalment amount and due date schedule. |
| Auto-Creation from Risk Checker | If user confirms a purchase after risk checking, system automatically creates a new BNPL plan record. |
| Plan Detail View | Full instalment timeline, payment schedule, current status (Active / Completed / Overdue), and the risk score generated at creation. |
| Plan Status Tracking | Plans are marked Overdue if a payment date passes without the user logging the payment. |

---

### 7.5 BNPL Risk Checker

The **core feature** of PaySense. The two AI engines work sequentially here.

| Feature | Description |
|---------|-------------|
| Purchase Input Form | User enters: Item Name, Total Price (RM), BNPL Provider, Number of Instalments, First Payment Date, Interest Rate (%). |
| Risk Score Output | Prominent score 0–100 with colour-coded label: **Safe** (green), **Caution** (yellow), **At Risk** (red). |
| Balance Impact Overlay | 6-month balance chart re-renders with proposed BNPL instalments overlaid as a new line, visually showing where the balance would drop. |
| SHAP XAI Explanation Panel | Plain-language explanation of the top 3 factors driving the risk score. Example: *"Your risk is HIGH because: (1) You already have 2 active BNPL plans. (2) Your projected balance drops below RM50 on 10 August. (3) Your instalment-to-income ratio exceeds 30%."* |
| Recommendation | System-generated recommendation: e.g. "Safe to proceed", "Consider delaying by 3 weeks", or "Avoid this purchase — high deficit risk in Month 2". |
| Confirm & Save to Plans | If user proceeds, a single tap saves the purchase as a new active BNPL plan in the BNPL Plans Manager. |

---

### 7.6 Forecasting Engine (Backend)

Powers the 6-month bar chart and the risk evaluation context. Not a standalone screen.

| Feature | Description |
|---------|-------------|
| Time-Series Forecasting | Aggregates the user's logged transactions into a monthly net cash flow series (income minus expenses) and fits ARIMA to it (`auto_arima`, non-seasonal, refit on every request because the personal series is under 12 months) to forecast the next 3 months of **net** cash flow; with fewer than 3 usable months it falls back to a trailing 3-month mean. The income and expense bars on the 6-month chart are not forecast independently: they are derived from the trailing 3-month averages, adjusted so that they differ by exactly the forecast net (see Section 9, fixed/variable decomposition). The historical series aggregates Income and Expense transaction types only — one-off Savings-type transactions are excluded (a lump-sum deposit would otherwise look like a spending spike and distort the trend), while recurring savings logged as Expense + Category: Saving are included like any other predictable outflow. |
| Future Balance Curve | Computes a week-by-week projected balance for the next 13 weeks, starting from the current balance, adding each week a pro-rata share of the forecast monthly net cash flow and subtracting every unpaid BNPL instalment falling due in that week. Known recurring bills are not modelled separately (see the fixed/variable decomposition item in Section 9). |
| Purchase Impact Simulation | When a new BNPL purchase is proposed, the engine simulates the updated balance curve with new instalments included, identifying any dates where balance drops below a safe threshold (RM0 or a configurable buffer). |

> **Current non-goal:** a future-dated one-off Savings goal does not automatically appear as a dip in the Future Balance Curve today, since it is excluded from the monthly net figure that curve relies on. Giving it the same explicit treatment as BNPL instalments (subtracted directly on its target date) would be needed if this becomes a requirement — not attempted in this version.

---

## 8. AI Model Design (Detailed)

### 8.1 Engine 1 — Financial Health Forecasting

| Attribute | Detail |
|-----------|--------|
| Candidate Models | ARIMA, Prophet, LSTM (all three trained and evaluated — best selected) |
| Input Features | Univariate: the monthly net cash flow series (income minus expenses) built from the user's logged transactions — Income and Expense types only; one-off Savings-type transactions are excluded, recurring savings logged as Expense + Category: Saving are included. No category, calendar or exogenous features are used by the forecasting model. BNPL instalment schedules and the current balance are applied afterwards, when the weekly balance curve is built, not fed into ARIMA. |
| Output | 3-month forecast of net cash flow from ARIMA (the chart's income and expense bars are derived from it — see Section 7.6); week-by-week balance curve for purchase impact simulation. **ARIMA selected as the winning model, based on lowest RMSE (7,300.30) on the 2024 hold-out test set** (see Section 8.3). |
| Training Data | Model selection: Kaggle personal finance dataset (2020–2024). Live serving: no pre-trained artefact — `auto_arima` is refit on each request to the user's own logged monthly net series (currently May 2025–Jul 2026, 15 months; April 2026 is partially logged). |
| Train/Test Split | 80% training, 20% testing (model-selection stage; time-series aware split — no random shuffling) |
| Evaluation Metrics | MAE, RMSE, MAPE |
| Selection Criterion | Lowest RMSE on test set |
| Training Tool | Google Colab Pro (Python / Jupyter Notebook) |
| Serialisation | The selection-stage ARIMA is saved as `engine1_winner.pkl` for provenance only; it is not loaded at serve time because the model is refit live on the user's data (Prophet and LSTM were evaluated only and are not served). |

### 8.2 Engine 2 — BNPL Risk Classifier

| Attribute | Detail |
|-----------|--------|
| Candidate Models | Random Forest, XGBoost, LightGBM (all three trained and evaluated — best selected) |
| Input Features | 11 features: `age`, `employment_status`, `monthly_income`, `monthly_expenses`, `num_bnpl_plans`, `bnpl_outstanding`, `missed_payments`, `forecasted_cash_flow` (Engine 1 linkage), `income_expense_ratio`, `bnpl_income_ratio`, `savings_rate` |
| Target / Output | Binary target `bnpl_risk` (0 = Low Risk, 1 = High Risk). The model outputs a risk probability, which is converted to a risk score (0–100) and bucketed into a rule-based 3-tier label (Safe / Caution / At Risk) for display — the model itself is a binary classifier, not a native 3-class classifier |
| XAI Layer | SHAP — feature importance values mapped to plain-language explanations for end-user display |
| Training Data | 2,000 synthetic BNPL scenarios (Malaysian-literature-grounded, Section 8.3), labelled with binary `bnpl_risk` |
| Class Imbalance Handling | Dataset is imbalanced toward High Risk (~74.1% risk=1 vs. ~25.9% risk=0); SMOTE applied on the training set only |
| Train/Test Split | 70% training, 15% validation, 15% test (stratified) |
| Evaluation Metrics | Accuracy, Precision, Recall, F1-Score, ROC-AUC |
| Selection Criterion | Highest average of F1-Score and ROC-AUC (`F1_AUC_avg` composite metric); Recall used as tiebreaker |
| Hyperparameter Tuning | Grid Search or Optuna for XGBoost and LightGBM (planned; **not performed** — all three candidates used hand-set, untuned hyperparameters, see Section 8.3) |
| Serialisation | Saved as `.pkl` and loaded by FastAPI at inference time |

> **Note:** `savings_rate` is computed from Income/Expense transaction totals only and is unaffected by the Savings transaction type introduced in Sections 5.3/7.3.

### 8.3 ML Model Evaluation Results

Both engines have been trained and evaluated on Google Colab (GPU T4). Results below reflect empirical performance on held-out test sets using the Kaggle Personal Finance Dataset (Engine 1) and 2,000 synthetic BNPL profiles (Engine 2).

#### Engine 1 — Cash Flow Forecasting Results

**Dataset:** Kaggle Personal Finance Data (Jan 2020 – Dec 2024) | **Split:** 80% train / 20% test (time-series aware, no shuffling)

| Rank | Model | MAE | RMSE | MAPE | Selected |
|------|-------|----:|-----:|-----:|:--------:|
| 1 | **ARIMA** | 5,350.51 | **7,300.30** | 257.89% | ✓ WINNER |
| 2 | Prophet | 6,518.97 | 7,607.86 | 274.01% | |
| 3 | LSTM | 7,911.61 | 9,923.00 | 516.27% | |

> **Winner: ARIMA** — selected by lowest RMSE (7,300.30). ARIMA outperformed Prophet by 4.0% on RMSE and LSTM by 26.4% on RMSE.
>
> **Note on MAPE:** All three models show high MAPE (>100%) because the target variable — monthly net cashflow — includes months near zero or negative, causing percentage-based errors to be mathematically inflated. RMSE was used as the primary selection metric as planned, since it is robust to this issue.

#### Engine 2 — BNPL Risk Classification Results

**Dataset:** 2,000 synthetic BNPL profiles (Gen-Z Malaysian students, literature-grounded v2 distributions; **v3 continuous-scaling label**, September 2026) | **Split:** 70% train / 15% val / 15% test (stratified) | **SMOTE applied on train set only**

**Dataset grounding:** Age distribution derived from Tan et al. (2026) Table 1 (N=150, active BNPL users at Malaysian public universities); employment status and monthly income brackets derived from Osman et al. (2024) Table 1 (N=440, Gen Z BNPL-aware sample). Key parameters: 61.4% students, 65.9% earning below RM1,000/month, age range 18–26. Features without empirical basis (monthly expenses, BNPL plan counts, missed payments) retained as domain-informed assumptions — see notebook cell 2 for full feature-by-feature grounding status. Demographic distributions (age/employment/income) are unchanged from v2; only the `bnpl_risk` **label-generation formula** changed (see below).

**Label-design fix (v3, September 2026):** Live end-to-end testing of the Risk Checker surfaced a labelling flaw traced to SHAP analysis of a real scenario: a purchase committing 115% of monthly income scored "safe" (P(risk)=0.08), because the v1/v2 label used hard binary thresholds — `missed_payments` only earned credit at ≥2 occurrences (1 missed payment counted the same as 0), and `bnpl_income_ratio` earned a flat +2 whether it was 51% or 500% of income. Both terms were replaced with continuous, linearly-scaled equivalents (same overall calibration point), and the dataset was regenerated and all three candidates retrained. Full trace, before/after numbers, and rationale for not attempting a full fuzzy-logic redesign under deadline pressure are in `docs/KNOWN_LIMITATIONS.md`.

**Class balance:** The relabelled `bnpl_risk` target is now less imbalanced than v1/v2 — **60.9% risk=1 (High Risk) vs. 39.1% risk=0 (Low Risk)**, pre-SMOTE (previously 74.1%/25.9%). This is a direct effect of continuous scaling: profiles just past a single risk factor no longer round up to "High Risk" the way a binary threshold did. SMOTE was still applied to the training split only.

| Rank | Model | Accuracy | Precision | Recall | F1 | ROC-AUC | F1+AUC Avg | Selected |
|------|-------|:--------:|:---------:|:------:|:--:|:-------:|:----------:|:--------:|
| 1 | **LightGBM** | 0.8333 | **0.9080** | 0.8087 | 0.8555 | **0.8987** | **0.8771** | ✓ WINNER |
| 2 | XGBoost | 0.8300 | 0.8976 | **0.8142** | 0.8539 | 0.8924 | 0.8732 | |
| 3 | Random Forest | 0.8267 | 0.8970 | 0.8087 | 0.8506 | 0.8985 | 0.8745 | |

> **Single-split notebook selection (superseded by the re-evaluation below): LightGBM** — selected by highest average of F1 (0.8555) and ROC-AUC (0.8987), giving a combined score of 0.8771, narrowly ahead of Random Forest (0.8745) and XGBoost (0.8732). This replaces XGBoost as the Engine 2 winner (XGBoost won on the v1/v2 binary-threshold-labelled dataset).
>
> **Note on Recall:** All three models land within 0.006 of each other on Recall (0.8087–0.8142) on the relabelled dataset — much closer than the v1/v2 spread (0.8182–0.8455) — so the F1+ROC-AUC combined score was the deciding factor rather than a clear Recall leader.
>
> **Consistency note:** Accuracy/Precision/ROC-AUC all held steady or improved slightly versus the v1/v2 dataset (e.g. Accuracy 0.82→0.83, ROC-AUC 0.876→0.899 for the respective winners), indicating the continuous-scaling label fix did not come at the cost of overall discriminative performance — see `docs/KNOWN_LIMITATIONS.md` for the case-level before/after that motivated the change.

#### Engine 2 — Re-evaluation with Repeated Cross-Validation and Calibration (September 2026)

The single-split result above cannot separate the candidates: the test split holds ~300 rows, so one row is ~0.33% accuracy and the three models differ by ~0.003 F1. The comparison was therefore repeated with **5×5 repeated stratified cross-validation** on the 1,700-row development set (SMOTE fitted on training folds only; the 15% test split untouched until one final check), with Nadeau–Bengio corrected resampled t-tests and an **oracle** row scored with the true generating probability (the labels are Bernoulli draws from a known probability, so the oracle is the ceiling any model can reach). All three candidates used hand-set, untuned hyperparameters (no grid search or Optuna was run), so the comparison is a like-for-like comparison of defaults, not of tuned optima. LightGBM ran without early stopping in this comparison (no fixed validation set per fold), so its figures differ slightly from the notebook's.

| Model | F1 | ROC-AUC | Recall | Brier (↓) | ECE (↓) |
|-------|:--:|:-------:|:------:|:---------:|:-------:|
| Oracle (true probability) | 0.836 | 0.882 | 0.838 | 0.135 | 0.044 |
| **Random Forest** | **0.826** | **0.868** | 0.813 | **0.146** | **0.057** |
| LightGBM | 0.819 | 0.857 | 0.811 | 0.159 | 0.099 |
| XGBoost | 0.816 | 0.857 | 0.809 | 0.159 | 0.095 |

> **Findings.** XGBoost vs LightGBM is a genuine tie (F1 p=0.50, ROC-AUC p=1.00, Brier p=0.97). Random Forest is significantly better than both on ROC-AUC (p≈0.002 / 0.008) and Brier score (p≈0.0003); its F1 advantage is not significant (p=0.11 / 0.24). The boosters are over-confident (ECE ≈0.10); because the 0–100 score is derived directly from P(risk), calibration matters more than the tiny F1 gaps. All three models sit within ~0.02 of the oracle ceiling, so the ~0.86 F1 on the single held-out split reflects label noise plus an easy split, not model quality.

**Calibration.** Because the forest trains on SMOTE-balanced data while real profiles are 60.9% high-risk, its raw probabilities are biased. Three options were compared by *nested* CV (calibrators fitted on inner out-of-fold predictions at the natural class balance): none, sigmoid (Platt scaling on log-odds) and isotonic.

| Calibration | Brier (↓) | Log loss (↓) | ECE (↓) | ROC-AUC | Recall |
|---|:-:|:-:|:-:|:-:|:-:|
| None | 0.1463 | 0.4492 | 0.0559 | 0.8661 | 0.811 |
| **Sigmoid (Platt)** | **0.1449** | **0.4447** | **0.0466** | 0.8661 | 0.844 |
| Isotonic | 0.1466 | 0.4685 | 0.0493 | 0.8639 | 0.861 |

Sigmoid significantly improves Brier (p=0.038) and log loss (p=0.012) over no calibration and beats isotonic on log loss (p=0.049); isotonic shows no significant gain over none, introduces probability ties (slightly lowering ROC-AUC) and can create flat regions in the score — the failure mode of the original label bug. **Sigmoid was selected.** The effect is modest (Random Forest was already reasonably calibrated); the fitted map is close to identity with a small upward shift (coefficient 0.941, intercept 0.234).

**Deployed model:** Random Forest (200 trees, depth 10) + Platt calibrator, fitted on the 1,700-row development set. One-shot held-out test check (informational, not used for any choice): raw F1 0.8555 / ROC-AUC 0.8944 / Recall 0.8251 / Brier 0.1290 / ECE 0.0685 → calibrated F1 0.8595 / ROC-AUC 0.8944 / Recall 0.8525 / Brier 0.1271 / ECE 0.0477. SHAP explains the raw forest output (additive to 1e-14); calibration is strictly increasing, so factor ranking is unaffected. The reference scenario (iPhone 16e, RM5,000, 6 instalments) now scores raw 0.572 → calibrated 0.624, score 38, "At Risk" (LightGBM: 0.409, score 59, "Caution"). Artefacts and regenerated plots: `models v4/`; scripts: `backend/scripts/engine2_model_comparison.py`, `backend/scripts/train_engine2_random_forest.py`; details in `docs/KNOWN_LIMITATIONS.md`.

#### Summary of Selected Models

| Engine | Task | Winner | Primary Metric | Value |
|--------|------|--------|---------------|-------|
| Engine 1 | Cash Flow Forecasting | **ARIMA** | RMSE (lowest) | 7,300.30 |
| Engine 2 | BNPL Risk Classification | **Random Forest + Platt calibration** | 5×5 repeated-CV ROC-AUC and Brier (single-split notebook pick was LightGBM, F1+AUC avg 0.8771 — superseded) | ROC-AUC 0.868, Brier 0.146 |

Both winner models are serialised locally (development moved from Colab/Drive to a local-first workflow — see `PaySense_Development_Plan.md`):
- `engine1_winner.pkl` — ARIMA forecasting model (pmdarima); provenance only, never loaded at serve time (serving refits live)
- `models v2/engine2_winner.pkl` — the XGBoost classifier described in v7.0 above; **frozen, unmodified provenance** for the already-graded Interim Report/Proposal Defence
- `models v3/engine2_winner.pkl` — the LightGBM classifier from the single-split notebook selection; **frozen provenance**, superseded for serving
- `models v4/` — the **current** Engine 2: `engine2_winner.pkl` (Random Forest) + `engine2_calibrator.pkl` (Platt), with regenerated comparison and SHAP plots; copied to `backend/models/` for serving

#### Engine 1 — Live Check on Personal Transaction Data (September 2026)

The Kaggle comparison above selects the model family. This section checks how the deployed pipeline behaves on the user's own logged data. **Setup:** the pipeline's forecast made with data through April 2026 (April partially logged, to 19 April) is compared with the real May–July 2026 expenses; a one-off savings transfer in May is excluded (it is stored as a Savings-type transaction). The live series has 15 monthly observations.

| Month | Actual expenses (RM) | Forecast (RM) | Error (RM) | Abs. % error |
|-------|---------------------:|--------------:|-----------:|-------------:|
| May 2026 | *redacted* | *redacted* | *redacted* | 11.4% |
| Jun 2026 | *redacted* | *redacted* | *redacted* | 34.2% |
| Jul 2026 | *redacted* | *redacted* | *redacted* | 16.8% |
| **Mean** | | | **MAE 168.51** | **MAPE 20.8%** |

The pipeline's headline output is net cash flow (MAE RM181.5 on the net figure). If the one-off savings transfer were counted as spending, the expense MAPE would be 35.1%. *(Monthly actual amounts are the author's personal data and are omitted from this public copy.)*

**Comparison with simple baselines** (same expenses target, forecasts made with data through April 2026, and a rolling-origin backtest over 7 forecast origins × 3 months on the 15-month series):

| Method | Live check MAE (RM) | Live check MAPE | Backtest MAE (RM) | Backtest MAPE |
|--------|-------------------:|----------------:|------------------:|--------------:|
| Naive (last month) | 134.2 | 14.0% | 440.5 | 44.3% |
| Trailing 2-month mean | 140.3 | 14.5% | 357.2 | 39.0% |
| Trailing 3-month mean | 155.5 | 19.4% | 384.6 | 42.3% |
| **Pipeline (ARIMA on net, split into income/expenses)** | **168.5** | **20.8%** | **450.5** | **49.5%** |
| ARIMA fitted directly on expenses | 505.0 | 62.1% | 482.9 | 54.9% |
| Expanding mean | 505.0 | 62.1% | 484.2 | 54.8% |

**Findings.**
- On this dataset the ARIMA-on-net pipeline does **not** outperform trivial baselines: it is beaten by the naive and moving-average forecasts in both the live check and the backtest. The result is indicative rather than conclusive — 15 monthly points, 3 live test months and overlapping backtest windows — and it does not overturn model selection, since ARIMA was chosen over Prophet and LSTM on the larger Kaggle dataset, which did not include naive baselines (adding them would be a sensible extension).
- Part of the live-check error is traceable to the data: the trailing 3-month base was inflated by an unusually high February 2026 that included a one-off payment, while March and April were lower. The user attributes May's higher spending to using later months' income early; this is a self-reported hypothesis that cannot be tested from the log, where income is recorded by the month it covers.
- **Small-sample fragility.** When May 2026 was added with the one-off savings transfer still logged as an ordinary expense, `auto_arima` selected ARIMA(0,0,0) with no intercept and the August–October net forecast collapsed to RM0 / RM0 / RM0. After the transfer was reclassified to the Savings type and excluded, it selected ARIMA(1,0,0) (φ ≈ 0.39) and forecast net RM64.14 / RM24.88 / RM9.65. A single large non-recurring entry can therefore change the selected model on a series this short. Spreading the amount across months was rejected because it would fabricate transactions that did not occur.
- The estimated noise is large (95% prediction interval on the April-cutoff net forecast of roughly ±RM1,100–1,300), so forecasts should be read as indicative.
- An earlier informal figure of 35.5% MAPE for this comparison used recalled, partly mis-summed actuals and is superseded by the table above.

---

## 9. Project Scope

### In Scope

- Fully deployed responsive web application (Next.js on Vercel)
- Two AI engines: time-series forecasting (best of ARIMA / Prophet / LSTM) and BNPL risk classification (best of Random Forest / XGBoost / LightGBM)
- Empirical model comparison and selection based on evaluation metrics
- XAI explanations for risk classifier output using SHAP
- Manual transaction entry and bank statement import (CSV and PDF — Malaysian bank formats)
- BNPL Plans Manager with manual and auto-creation flows
- Financial Health Speedometer (0–100 score with Safe / Caution / At Risk labels)
- Supabase (PostgreSQL) database for persistent data storage
- FastAPI Python backend for ML model serving and data operations
- Full literature review matrix comparing at least 20 papers on BNPL risk, credit scoring, and cash flow forecasting

### Out of Scope (Future Work)

- Direct bank API integration (Maybank, CIMB, RHB) for automated transaction sync
- CCRIS/CTOS credit bureau integration
- Native mobile applications (iOS/Android)
- User authentication and multi-user account management
- Push notification/SMS alerts
- Peer comparison or social features
- Investment and stock portfolio tracking

### Known Limitations

- **Self-reported data completeness** — logged transaction amounts may not perfectly match real-world spending (e.g. untracked cash purchases, forgotten entries); a standard constraint of manually-entered personal finance data, not a model defect.
- **Calendar-month vs. pay-cycle timing noise** — income and expenses are attributed to the calendar month they are logged in, not necessarily the pay cycle they conceptually belong to (e.g. income received early in one month and spent before the next month begins). Example: a multi-month income disbursement that arrives early is logged as equal amounts dated the 1st of each month it covers, so the monthly series reflects the month each amount is for rather than when the cash arrived (the synced balance reflects real timing).
- **April 2026 is partially logged** — the personal log ends on 19 April 2026; the remaining April entries were lost to a technical error and cannot be recovered. The forecasting series treats April as a complete month, so its expenses are understated and its net overstated.
- **Short personal history makes the live forecast fragile** — the live series has 15 monthly observations. ARIMA is non-seasonal, its forecasts decay toward zero within a few months, and a single large non-recurring entry can change the selected model (Section 8.3, live check). One-off savings transfers are protected by the Savings type; other large one-offs are not.
- **Current Balance is manually-synced by default, not ledger-derived** — accuracy of balance-dependent features (Financial Health Speedometer, projected balance curve, Risk Checker) depends on how recently and accurately the user has synced their real balance via Balance Sync. A ledger-derived mode now exists in the codebase (`app_state.ledger_mode`, see below) but is off by default and not yet activated for this evaluation.

### Future Improvements

- **Ledger-derived running balance — built, not yet activated (2026-09-23).** Current Balance now supports two modes, switched by an `app_state.ledger_mode` flag: manually-synced (original design, still the default) or a running ledger where every income/expense/savings transaction's create, edit or delete moves Current Balance the instant it happens (income adds; expense and savings both subtract), with Balance Sync kept as a manual correction tool for drift (bank fees, missed entries, rounding) rather than the only update path. Full details in `docs/ARCHITECTURE.md` §4.1. Rollout is staged, not immediate: historical transactions are still being backfilled with `ledger_mode` off so backfill itself never touches the balance; once backfill is complete, one manual sync sets an accurate baseline, and `ledger_mode` is switched on from that point forward. Not yet done as of this version — the balance shown today is still the pre-ledger manual figure.
- **Multi-account balance** — allow the user to enter a balance per bank/e-wallet account; the system sums these into the single Current Balance used as Engine 1's forecasting starting point, removing the need for users to manually total multiple accounts themselves.
- **Fixed/variable decomposition of Engine 1's forecast** — Engine 1 currently forecasts total monthly net cash flow as a single combined series. Part of that total is already known with certainty (rent, Wi-Fi and BNPL instalments have exact amounts and due dates), so ARIMA is effectively re-guessing quantities the system already holds, which adds avoidable noise to an already difficult forecasting problem. The proposed change needs no new algorithm or library, only three steps:
  1. Sum the known fixed outflows for the forecast period (rent, bills, BNPL instalments) from the existing schedules — pure arithmetic.
  2. Run ARIMA only on the remaining discretionary spending (total minus fixed outflows), instead of on the combined total.
  3. Add the two components back together for the final projected balance.

  *Expected benefit and caveats:* this is a sound, low-risk idea, but the improvement is likely to be modest. If most of the current forecast error comes from genuinely unpredictable discretionary spending (a large one-off trip, an impulse purchase) rather than fixed-cost noise, removing the fixed portion will help less than hoped. MAPE will also likely remain poor regardless, because of the near-zero-denominator distortion already described in Section 8.3, which this change does not address.

  *Concrete example — income (observed 2026-09-24):* the same principle applies to income, which is also largely known in advance (the user's monthly allowance is a fixed amount) yet is not forecast independently. Engine 1 forecasts only the net figure with ARIMA; the income and expense bars on the 6-month chart are then back-derived by splitting the trailing 3-month averages so that they differ by exactly that net. With real May–Jul 2026 data, income was the same fixed amount every month, but the August forecast income bar showed a different figure — not a prediction that income would fall, but the arithmetic of closing a RM65.82 gap between the trailing averages and ARIMA's net by moving both bars RM32.91. A simulation on an in-memory copy of the data (nothing written) also showed that if a different income is logged, ARIMA reacts in the next month but then decays back toward zero net over the following months, because with roughly 15 monthly observations the model cannot distinguish a permanent income change from a one-off. Forecasting income and expenses as separate series (income as a known or recently observed amount; expenses by a method suited to a volatile series) would make the income bar a genuine forecast and let an income change carry through. Its caveats: it changes the net forecast and therefore every downstream figure (balance curve, Engine 2's forecasted-cash-flow feature, Risk Checker, and the evaluation results reported in this document); an ARIMA fitted directly to expenses did not outperform simple trailing averages in a rolling backtest on this dataset (roughly 63% vs 42–48% MAPE), so the gain is mainly interpretability rather than accuracy; and because ARIMA was selected on net cash flow (Section 8.3), splitting or replacing it for one series would weaken that selection evidence and should be reviewed with the supervisor.

  *Why deferred:* this is a quality/rigour enhancement on an inherently hard forecasting problem, not a correctness fix, and higher-priority items take precedence within the FYP2 timeline. Documented as future work only; not implemented in this version. The chart is deliberately left unchanged while Engine 1/2 testing is in progress; the net figure it derives from is correct and all downstream numbers are unaffected.
- **Fuzzy-rule-based / Fuzzy C-Means-derived label logic for Engine 2** — Engine 2's synthetic training labels originally used hard binary thresholds (e.g. `bnpl_income_ratio > 0.5`, `missed_payments >= 2`), which flattened risk severity and caused a real misclassification: a purchase committing 115% of monthly income with 1 missed payment scored "Safe" (P(risk) = 0.08). This was traced via SHAP and fixed in v8.0 with continuous linear scaling (Section 8.3), which resolved the correctness issue; LightGBM is now the winner (F1 0.8555, ROC-AUC 0.8987, Recall 0.8087). The remaining limitation is that the scaling boundaries are still chosen manually (e.g. `bnpl_income_ratio` clipped at 3× monthly income, `missed_payments` at 6), not derived from the data itself.

  *Proposed refinement:* replace the fixed clip points with fuzzy membership functions (e.g. Gaussian or trapezoidal) for each risk factor, combined through a fuzzy rule base, with the membership-function parameters derived from the data via Fuzzy C-Means clustering. This would give the label logic a more theoretically grounded, citable basis than hand-picked boundaries.

  *Status and caveat:* this direction is being explored in consultation with UTP faculty with relevant expertise in neuro-fuzzy classification and fuzzy membership function design. It is not required for correctness, since the label-design defect is already fixed and regression-guarded (`backend/tests/test_engine2_calibration.py`); it is being pursued as a potential refinement, pending their input and remaining project time. Because the training labels are synthetic, data-derived boundaries would reflect the distributions of the generated dataset rather than ground-truth default behaviour, so any FCM-derived result would need to be presented with that limitation. Documented as future work only; not implemented in this version.
- **Anchor Engine 1's forecast to the current date (stale-data handling)** — Engine 1 currently starts its 3-month forecast from the month after the *last logged transaction*, whereas the weekly balance curve starts from *today*. While the transaction log is kept up to date the two windows coincide. If the log lags behind the system date, they stop overlapping: the balance curve receives no forecast net cash flow for the uncovered weeks, and the instalments of a proposed BNPL purchase that fall outside the forecast months are not deducted from the forecasted-cash-flow feature passed from Engine 1 to Engine 2. This was observed during evaluation, when the log ended in April 2026 and the system date was September 2026 (the curve was flat). A related edge case is that a partially logged final month is treated as a complete month by the forecasting series.

  *Proposed change:* derive the forecast months from the current calendar month rather than the last logged month; treat any gap between the last logged month and today as missing data (warn the user or fill it from the forecast); and exclude the current, incomplete month from the training series.

  *Why deferred:* this affects the balance curve and purchase-impact simulation only when the log is stale — it does not change model selection, the forecasting method, or any reported evaluation metric. For the FYP evaluation the log is loaded up to July 2026, so the limitation is known and bounded. Documented as future work only; not implemented in this version.

---

## 10. Academic & Research Alignment

### 10.1 Literature Review Summary

A total of **30 papers (2021–2026)** have been reviewed and categorised across 7 domains. Sources: Google Scholar, IEEE Xplore, ScienceDirect, Springer, Taylor & Francis.

**Distribution:** 21 Journal Papers | 3 Conference Papers | 3 Working Papers/Preprints | 3 Review Papers

| Domain | Count |
|--------|-------|
| BNPL Consumer Behavior | 8 |
| BNPL Regulation & Market | 3 |
| Financial Literacy | 4 |
| Time-Series Forecasting | 5 |
| Credit Risk Classification | 5 |
| Explainable AI (XAI) | 3 |
| Personal Finance Apps | 2 |
| **Total** | **30** |

---

### 10.2 Literature Review Matrix

#### A — BNPL Consumer Behavior (8 papers)

| # | Author(s) & Year | Key Findings | Research Gap | PaySense Relevance |
|---|-----------------|-------------|-------------|-------------------|
| 1 | Osman et al. (2024) | Attitude and Perceived Behavioral Control (PBC) significantly drive BNPL adoption among Malaysian Gen Z; social influence promotes impulsive spending | Cross-sectional; no predictive modelling of financial outcomes | Validates target demographic; confirms knowledge-action gap |
| 2 | Tan et al. (2026) | High self-reported financial literacy (M = 4.07/5) but very weak correlation with debt management (r = 0.060); PBC (Beta = 0.694) is dominant predictor of BNPL usage | No longitudinal tracking; no AI intervention proposed | **Core reference** — provides key statistics for the problem statement |
| 3 | Raj et al. (2024) | BNPL intensifies materialism; reduces 'pain of payment'; promotes overconsumption and debt traps | No quantification of future cash flow impact of BNPL stacking | Supports Engine 2's role in simulating cumulative financial impact before commitment |
| 4 | Aisjah, S. (2024) | Financial self-efficacy and parenting influence BNPL adoption; low self-efficacy = higher BNPL vulnerability | Indonesian context; no predictive modelling | Confirms university students are a high-risk group for BNPL-related debt |
| 5 | Kumar et al. (2024) | BNPL drives 10% increase in basket sizes; reduces price sensitivity; effects strongest for consumers who made smaller purchases | No tracking of individual debt accumulation over time | Empirical evidence that BNPL increases spending — justifies forecasting need |
| 6 | Blue et al. (2023) | Many users experience debt cycling — using one BNPL to pay another; BNPL normalises debt and reduces awareness of cumulative obligations | Qualitative; no quantitative financial impact measurement | Confirms 'instalment stacking' problem central to Engine 1's forecasting approach |
| 7 | Relja et al. (2023) | Users underestimate BNPL risk due to 'interest-free' framing; trust and perceived usefulness drive adoption | UK-centric; no forecasting component | Supports need for AI risk classifier that objectively evaluates purchase risk |
| 8 | Cook et al. (2023) | BNPL providers frame debt as a neutral 'payment method', reducing risk perception among youth | No technological interventions proposed | Explains why explicit dashboard visualisation of future financial impact is essential |

#### B — BNPL Regulation & Market (3 papers)

| # | Author(s) & Year | Key Findings | Research Gap | PaySense Relevance |
|---|-----------------|-------------|-------------|-------------------|
| 9 | Irawati et al. (2024) | Malaysia emphasises financial inclusion; BNPL poses over-indebtedness, credit risk, and data protection challenges across ASEAN | No consumer-facing tools proposed | Highlights regulatory gap justifying consumer protection tools like PaySense |
| 10 | Filotto et al. (2024) | BNPL displacing credit cards among younger demographics globally; significant scale reached with limited regulatory oversight | Macro-level analysis; no individual-level consumer tools | Confirms urgency and scale of BNPL growth |
| 11 | Cornelli et al. (2023) | BNPL growth correlated with higher e-commerce and lower credit card access; disproportionately affects younger, lower-income consumers | Aggregate country-level data; no individual debt trajectory analysis | Confirms target demographic selection for PaySense |

#### C — Financial Literacy (4 papers)

| # | Author(s) & Year | Key Findings | Research Gap | PaySense Relevance |
|---|-----------------|-------------|-------------|-------------------|
| 12 | Cappelli et al. (2024) | Financial literacy alone insufficient to change behaviour; digital tools and behavioural interventions more effective than knowledge-only approaches | No specific technological solutions tested | Directly supports AI-driven copilot rationale over education-only interventions |
| 13 | Surwanti et al. (2024) | Gen Z shows lower financial discipline despite digital fluency; fintech adoption outpaces financial literacy development | Self-reported data; no predictive modelling | Validates need for predictive copilot bridging digital convenience and financial responsibility |
| 14 | Di Maggio et al. (2022) | BNPL users stack multiple commitments; financially fragile consumers most affected; stacking increases overall spending significantly | US-focused; no consumer forecasting tools | Foundational evidence for instalment stacking — directly motivates Engine 1 |
| 15 | Gerrans et al. (2022) | BNPL users with lower financial literacy significantly more likely to experience financial stress; minimal affordability checks in BNPL | Australian context; no AI or predictive modelling component | Directly justifies Engine 2's affordability assessment before purchase commitment |

#### D — Time-Series Forecasting (5 papers)

| # | Author(s) & Year | Key Findings | Research Gap | PaySense Relevance |
|---|-----------------|-------------|-------------|-------------------|
| 16 | Ning et al. (2022) | Prophet robust for automatic seasonality detection; LSTM outperforms for complex non-linear patterns; ARIMA competitive for stationary series; MAE & RMSE as primary metrics | Oil production context; performance may differ for personal finance with irregular patterns | **Primary reference** for Engine 1 model selection and evaluation metric choice |
| 17 | Arslan, S. (2022) | Hybrid Prophet-LSTM significantly outperforms standalone models; Prophet decomposes seasonality, LSTM handles non-linear residuals | Energy consumption context; computational complexity concern for real-time apps | Validates hybrid decomposition approach as potential Engine 1 enhancement |
| 18 | Khan & Ali (2023) | Prophet provides best balance of accuracy and simplicity for short-horizon financial forecasts; ARIMA effective for stationary data; deep learning offers marginal gain with short horizons | Macroeconomic indicators, not personal finance | Validates Prophet and ARIMA as candidate models; confirms 3-month horizon is best suited to Prophet |
| 19 | Wang & Li (2023) | Combined Prophet-LSTM achieves superior accuracy; Prophet's trend/seasonality decomposition provides interpretability; computationally efficient for real-time applications | Not validated on personal finance or spending data | Provides implementable architecture combining Prophet interpretability with LSTM accuracy |
| 20 | Ibrahim & Al-Shammari (2025) | ARIMA-Prophet hybrid achieves lowest error rates across multiple financial datasets; framework adaptable to different forecasting horizons | Not tested on personal finance data; tuning overhead increases with longer horizons | State-of-the-art hybrid framework applicable to Engine 1 as a potential enhancement |

#### E — Credit Risk Classification (5 papers)

| # | Author(s) & Year | Key Findings | Research Gap | PaySense Relevance |
|---|-----------------|-------------|-------------|-------------------|
| 21 | Zhu et al. (2023) | XGBoost achieves AUC > 0.85 for loan default prediction; SHAP reveals income-to-debt ratio and number of active accounts as key features; explainability does not reduce accuracy | Traditional loan default context; not BNPL-specific; no future balance forecasting as input | **Primary reference** for Engine 2 — validates XGBoost + SHAP integration |
| 22 | Chang et al. (2024) | Gradient Boosting achieves best F1-score for P2P lending; ratio-based feature engineering significantly improves credit risk classification performance | P2P lending context; no BNPL-specific features; no forecasting integration | Validates Gradient Boosting (XGBoost/LightGBM) for credit risk; ratio features transferable to Engine 2 |
| 23 | Naik, K. S. (2021) | Random Forest and XGBoost consistently outperform traditional classifiers for unsecured credit risk; repayment history and debt-to-income ratio are strongest predictors | No BNPL-specific features; no forecasting integration; no XAI layer | Benchmark for ML classifier comparison in consumer credit — directly applicable to Engine 2 selection |
| 24 | Sousa et al. (2022) | Random Forest achieves best accuracy; consumer spending patterns are stronger predictors than static demographic features | Brazilian banking context; no time-series forecasting input | Validates Random Forest as candidate; spending patterns as predictors align with Engine 2 features |
| 25 | Rahmani et al. (2025) | Gradient Boosting: accuracy = 0.89, F1 = 0.81; SMOTE significantly improves minority class (defaulter) recall; structured ML pipeline with feature engineering and tuning is essential | General lending data; not BNPL-specific; no consumer-facing risk scores | Complete reproducible ML pipeline design adaptable for Engine 2; validates SMOTE approach for class imbalance |

#### F — Explainable AI (XAI) (3 papers)

| # | Author(s) & Year | Key Findings | Research Gap | PaySense Relevance |
|---|-----------------|-------------|-------------|-------------------|
| 26 | Osei-Bonsu & Mensah (2024) | SHAP provides consistent global feature importance; LIME offers intuitive local explanations; combining both produces complementary global and local insights | Lender-focused; not consumer-facing | Directly informs XAI layer design for Engine 2's Risk Checker screen |
| 27 | Mujo et al. (2025) | SHAP values mapped to plain-language explanations improve user trust and reduce bias in automated credit decisions | Not applied to consumer-facing personal finance tools | Validates feasibility of mapping SHAP values to plain-language alerts for students |
| 28 | Azzutti et al. (2025) | SHAP and LIME most widely adopted model-agnostic XAI methods in finance; consumer-facing XAI in personal finance **explicitly identified as a research gap** | Review paper; does not implement new XAI approaches | **Positions PaySense as a novel contribution** — fills the identified consumer-facing XAI gap |

#### G — Personal Finance Apps (2 papers)

| # | Author(s) & Year | Key Findings | Research Gap | PaySense Relevance |
|---|-----------------|-------------|-------------|-------------------|
| 29 | Kamarudeen & Vijayalakshmi (2023) | ML-based expense categorisation reduces manual effort ~70%; students using the app showed improved budgeting; real-time feedback critical for engagement | Historical tracking only; no predictive or forecasting capability; no BNPL-specific risk handling | Validates ML-powered financial apps for students; PaySense extends this with prediction + BNPL risk classification |
| 30 | Georgieva et al. (2024) | Mobile-first design increases adoption; CSV/PDF import best balance of accuracy and usability; visual financial status reports improve financial awareness | Purely reactive — historical tracking only; no AI or predictive features; no BNPL or risk assessment | Represents current state-of-the-art; the limitations identified are precisely the gaps PaySense addresses |

---

### 10.3 Research Gaps Identified

Five critical research gaps have been identified through systematic review of the 30 papers:

| Gap | Description | How PaySense Addresses It |
|-----|-------------|--------------------------|
| **Gap 1 — No Predictive Consumer-Facing BNPL Tools** | All existing BNPL research documents behaviour and risk but no study proposes a consumer-facing predictive tool that simulates the financial impact of new BNPL commitments *before* purchase | Engine 1 + Engine 2 sequential architecture provides pre-purchase simulation and impact assessment |
| **Gap 2 — Forecasting Not Applied to Personal Finance** | Prophet and ARIMA have been applied to macroeconomic indicators, stock prices, and enterprise cash flows — not to individual student personal finance forecasting | Engine 1 targets individual student spending patterns with explicit BNPL instalment awareness in the balance projection |
| **Gap 3 — Credit Risk Models Not Adapted for BNPL** | Existing ML classifiers use institutional lending features; no classifier uses forecasted future balance as input or models BNPL-specific factors (instalment stacking, overlapping due dates, remaining buffer) | Engine 2 uses Engine 1's forecasted balance curve as a key feature; input features are explicitly designed around BNPL-specific risk signals |
| **Gap 4 — XAI Not Applied to Consumer-Facing Financial Tools** | SHAP/LIME extensively used in institutional credit scoring; consumer-facing XAI in personal finance explicitly identified as underexplored by Azzutti et al. (2025) | SHAP explanations translated to student-friendly plain-language alerts surfaced in the Risk Checker screen |
| **Gap 5 — No Integration of Forecasting + Classification** | No existing system feeds forecasted future balances into a BNPL risk classifier for real-time, context-aware purchase risk assessment | **Core novelty of PaySense** — sequential Engine 1 → Engine 2 architecture where the forecasted balance curve is the evaluation context for every risk decision |

> **Search terms:** `BNPL credit risk machine learning`, `credit scoring classification algorithms`, `consumer default prediction XGBoost`, `cash flow forecasting LSTM Prophet`, `peer-to-peer lending default prediction`, `personal finance time series ARIMA`, `explainable AI credit risk SHAP`, `BNPL Malaysia university students`, `financial literacy Gen Z`  
> **Sources:** Google Scholar, IEEE Xplore, ScienceDirect, Springer, Taylor & Francis

---

## 11. Project Timeline

### FYP 1 — Current Semester

| Week | Task / Milestone | Deliverable |
|------|-----------------|-------------|
| 1–2 | Topic confirmation, supervisor meeting, concept document v1 | Concept Document v1 |
| 3–4 | Literature review — 20 papers, build comparison matrix | Literature Matrix (draft) |
| 5–6 | Identify and confirm 3 candidate models per engine; identify Kaggle datasets | Model shortlist, Dataset sourced |
| 7 | Concept document v2 — finalised ML plan, tech stack, architecture | Concept Document v2 |
| 8 | Proposal Defence preparation — slides, script, architecture diagrams | Proposal Defence Slides |
| 9 | **Proposal Defence** | ✅ Proposal Defence — SUBMITTED |
| 10–11 | Interim Report writing — Introduction, Literature Review, Methodology chapters | Interim Report (draft) |
| 12 | Finalize and submit Interim Report | ✅ Interim Report — SUBMITTED |
| 13–14 | Begin data preparation — clean Kaggle dataset, generate synthetic BNPL scenarios | Prepared datasets |
| 14–15 | Ahead of the original schedule: train and evaluate all 6 candidate models — Engine 1 (ARIMA, Prophet, LSTM) and Engine 2 (Random Forest, XGBoost, LightGBM) — on Google Colab; full empirical comparison completed | ✅ Model evaluation complete — **ARIMA** (Engine 1) and **XGBoost** (Engine 2) selected (Section 8.3) |

> **Note:** Model training for both engines (originally scheduled for FYP2 Weeks 1–6) was completed during FYP1, once the Kaggle dataset and literature-grounded synthetic BNPL data were ready. The FYP2 timeline below has been restructured accordingly to start directly with XAI integration and full-stack development.

### FYP 2 — Next Semester

| Week | Task / Milestone | Deliverable |
|------|-----------------|-------------|
| 1–2 | Integrate SHAP explainability for the selected Engine 2 model (Random Forest, after the September 2026 re-evaluation); build FastAPI backend with all ML endpoints (forecasting, risk scoring, SHAP, transaction CRUD, parsing) | FastAPI backend (complete) |
| 3–6 | Build Next.js frontend — Dashboard, Transactions, BNPL Manager, Risk Checker; connect to Supabase | Frontend (complete) |
| 6–8 | Full system integration — frontend + backend + database; CSV/PDF parsing | Integrated system |
| 8–9 | System testing, bug fixing, performance tuning; deploy to Vercel + Render | Deployed live application |
| 9–10 | User Acceptance Testing (UAT) with Malaysian university students (Objective 3) | UAT results |
| 10–11 | Write Dissertation + Technical Paper (6 pages, IEEE format) | Dissertation draft, Technical Paper draft |
| 12 | Project Presentation preparation; final application demo | Presentation slides, Demo ready |
| 13 | **Project Presentation & Demo** | ✅ Project Presentation — SUBMITTED |
| 14 | Submit hard-bound dissertation copies and final revised technical paper | ✅ Hard-bound Dissertation — SUBMITTED |

---

## 12. References

### BNPL Consumer Behavior

1. I. Osman, N. A. M. Ariffin, M. F. N. B. Mohd Yuraimie, M. F. B. Ali, and M. A. F. B. Noor Akbar, "How Buy Now, Pay Later (BNPL) is Shaping Gen Z's Spending Spree in Malaysia," *Information Management and Business Review*, vol. 16, no. 3S(I)a, pp. 757–770, 2024.
2. W. S. Tan et al., "Buy Now Pay Later (BNPL) Usage and Its Impact on Debt Management Among Malaysian University Students," *International Journal of Accounting and Finance in Asia Pacific*, vol. 9, no. 1, pp. 90–103, 2026.
3. V. A. Raj, S. S. Jasrotia, and S. S. Rai, "Intensifying Materialism Through Buy-Now Pay-Later (BNPL): Examining the Dark Sides," *International Journal of Bank Marketing*, vol. 42, no. 1, pp. 94–112, 2024.
4. S. Aisjah, "Intention to Use Buy-Now-Pay-Later Payment System Among University Students: A Combination of Financial Parenting, Financial Self-Efficacy, and Social Media Intensity," *Cogent Social Sciences*, vol. 10, no. 1, 2306705, 2024.
5. A. Kumar, J. Salo, and R. Bezawada, "The Effects of Buy Now, Pay Later (BNPL) on Customers' Online Purchase Behavior," *Journal of Retailing*, Advance Online Publication, 2024.
6. L. Blue, L. Coglan, T. Pham, I. Lammer, R. Menner, and C. Lee, "Spend and Repeat! Young Adult's Experiences with Buy Now Pay Later Services," *Financial Planning Research Journal*, vol. 9, no. 1, pp. 1–19, 2023.
7. R. Relja, P. Ward, and A. Zhao, "Understanding the Psychological Determinants of Buy-Now-Pay-Later (BNPL) in the UK: A User Perspective," *International Journal of Bank Marketing*, vol. 42, no. 1, pp. 7–37, 2023.
8. J. Cook, K. Davies, D. Farrugia, S. Threadgold, J. Coffey, K. Senior, A. Haro, and B. Shannon, "Buy Now Pay Later Services as a Way to Pay: Credit Consumption and the Depoliticization of Debt," *Consumption Markets & Culture*, vol. 26, no. 4, pp. 245–257, 2023.

### BNPL Regulation & Market

9. L. Irawati, M. Z. Hamzah, and E. Sofilda, "Regulating Buy Now Pay Later (BNPL) in ASEAN: A Comparative Analysis on Regulatory Challenges and Opportunities," *International Journal of Economics, Management and Accounting*, vol. 1, no. 4, pp. 60–81, 2024.
10. U. Filotto, D. Salerno, G. Sampagnaro, and G. P. Stella, "Riding the Wave of Change: Buy Now, Pay Later as a Disruptive Threat to Payment Cards in the Global Market," *Research in International Business and Finance*, vol. 72, 102499, 2024.
11. G. Cornelli, L. Gambacorta, and L. Pancotto, "Buy Now, Pay Later: A Cross-Country Analysis," *BIS Quarterly Review*, Bank for International Settlements, 2023.

### Financial Literacy

12. T. Cappelli, A. P. Banks, and B. Gardner, "Understanding Money-Management Behaviour and Its Potential Determinants Among Undergraduate Students: A Scoping Review," *PLOS ONE*, vol. 19, no. 8, e0307137, 2024.
13. A. Surwanti, M. Maulidah, Wihandaru, R. Kusumawati, and F. Santi, "Financial Management Behaviour Z Generation," *E3S Web of Conferences*, vol. 571, 03003, 2024.
14. M. Di Maggio, E. Williams, and J. Katz, "Buy Now, Pay Later Credit: User Characteristics and Effects on Spending Patterns," NBER Working Paper No. 30508, National Bureau of Economic Research, 2022.
15. P. Gerrans, D. G. Baur, and S. Lavagna-Slater, "Fintech and Responsibility: Buy-Now-Pay-Later Arrangements," *Australian Journal of Management*, vol. 48, no. 4, pp. 772–793, 2022.

### Time-Series Forecasting

16. Y. Ning, H. Kazemi, and P. Tahmasebi, "A Comparative Machine Learning Study for Time Series Oil Production Forecasting: ARIMA, LSTM, and Prophet," *Computers & Geosciences*, vol. 164, 105126, 2022.
17. S. Arslan, "A Hybrid Forecasting Model Using LSTM and Prophet for Energy Consumption with Decomposition of Time Series Data," *PeerJ Computer Science*, vol. 8, e1001, 2022.
18. S. N. Khan and A. Ali, "Comparative Analysis of Advanced Time Series Forecasting Techniques: Evaluating the Accuracy of ARIMA, Prophet, and Deep Learning Models for Predicting Financial Indicators," *Advances in Deep Learning Techniques*, vol. 3, no. 1, pp. 52–98, 2023.
19. Z. Wang and H. Li, "Time-Series Prediction Research Based on Combined Prophet-LSTM Model," in *Proc. IEEE 2nd International Conference on Electrical Engineering, Big Data and Algorithms (EEBDA)*, 2023, pp. 1395–1399.
20. M. Z. Ibrahim and E. T. Al-Shammari, "A Hybrid Approach to Time Series Forecasting: Integrating ARIMA and Prophet for Improved Accuracy," *Ain Shams Engineering Journal*, Article in Press, 2025.

### Credit Risk Classification

21. X. Zhu, Q. Chu, X. Song, P. Hu, and I. L. Peng, "Explainable Prediction of Loan Default Based on Machine Learning Models," *Data Science and Management*, vol. 6, pp. 123–133, 2023.
22. A. H. Chang et al., "Performance Evaluation of Hybrid Machine Learning Algorithms for Online Lending Credit Risk Prediction," *Applied Artificial Intelligence*, vol. 38, no. 1, 2358661, 2024.
23. K. S. Naik, "Predicting Credit Risk for Unsecured Lending: A Machine Learning Approach," arXiv preprint, arXiv:2110.02206, 2021.
24. M. R. Sousa, J. Gama, and E. Brandão, "Machine Learning Predictivity Applied to Consumer Creditworthiness," *Computational Economics*, vol. 59, pp. 1523–1557, 2022.
25. R. Rahmani, M. Parola, and M. G. C. A. Cimino, "Data-Driven Loan Default Prediction: A Machine Learning Approach for Enhancing Business Process Management," *Systems (MDPI)*, vol. 13, no. 7, 581, 2025.

### Explainable AI (XAI)

26. A. Osei-Bonsu and F. Mensah, "Explainable AI for Credit Risk Assessment: A Data-Driven Approach to Transparent Lending Decisions," *Journal of Economics, Finance and Accounting Studies*, vol. 6, no. 5, pp. 01–12, 2024.
27. A. Mujo, S. Nikolla, E. Hoxha, and E. Pelivani, "Explainable AI in Credit Scoring: Improving Transparency in Loan Decisions," *Journal of Information Systems Engineering and Management*, vol. 10, no. 3, 4437, 2025.
28. A. Azzutti et al., "Model-Agnostic Explainable Artificial Intelligence Methods in Finance: A Systematic Review, Recent Developments, Limitations, Challenges and Future Directions," *Artificial Intelligence Review*, vol. 58, 270, 2025.

### Personal Finance Apps

29. M. Kamarudeen and K. Vijayalakshmi, "Machine Learning Based Financial Management Mobile Application to Enhance College Students' Financial Literacy," in *Proc. ICRES 2023 — International Conference on Research in Education and Science*, 2023, pp. 1237–1253.
30. D. Georgieva, G. Tsochev, and G. Angelov, "Personal Finance Management Application," *TEM Journal*, vol. 13, no. 3, pp. 2066–2075, 2024.

---

*PaySense: AI-Driven System for Financial Health Forecasting and BNPL Risk Classification • Nur Farah Binti Ahmad Nazri • 22007916 • Universiti Teknologi PETRONAS*
