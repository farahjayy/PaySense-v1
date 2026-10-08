# BNPL Billing Rules: SPayLater, TikTok PayLater, Atome (Malaysia)

Sep 25, 2026 · @Farah

## Key takeaway

Only Atome charges anything at checkout. SPayLater and TikTok PayLater charge nothing at checkout and send the first bill in a later period, so an instalment schedule that starts on the purchase date is correct for Atome only.

The 3-month plan is 0% at SPayLater (Shopee marketplace checkouts only) and at Atome. TikTok PayLater's checkout shows 0% per month for the 1-month and 6-month plans and about 1.5% per month for the 12-month plan; the 6-month 0% carries a 0% fees badge, so it may be promotional. Longer plans at SPayLater and Atome also cost about 1.5% per month.

## Billing timing

SPayLater and TikTok PayLater are pay-later products: the purchase is added to a bill. Atome is a split-payment product: a card is charged at checkout.

Atome bills the same way online and in-store: the first payment is charged at the point of purchase.

SPayLater's RM0 at checkout applies to Shopee-platform checkouts. In-store partner pages say to scan the QR and pay the first instalment at checkout using the app, so in-store purchases may require an upfront payment. This is unverified.

| Provider | Paid at checkout | First payment | Later payments |
| --- | --- | --- | --- |
| SPayLater | RM0 (Shopee checkout) | Next billing cycle, due on a fixed day (see below) | Monthly, on the same fixed due day |
| TikTok PayLater | RM0 (likely) | Not confirmed. The 1-month plan allows payment up to the 41st day after ordering | Monthly |
| Atome (3-month plan) | One-third of the bill, charged to a credit or debit card | Purchase date | Two more payments, one per month, auto-charged to the linked card |

SPayLater has two billing options. Option 1: billed on the 1st, due on the 10th. Option 2: billed on the 21st, due on the 1st. The exact cut-off that decides which bill a purchase lands on was not found, so treat billing day and due day as settings, not constants.

The Atome Card is a different product from standard Atome. It is a prepaid Visa with 0% if the bill is paid in full within up to 40 days of each billing cycle, or 3, 6, 9 or 12-month instalments. It behaves like a pay-later product, not like the 3-payment split.

## Plans and fees

Fees are 1.5% per month of the order amount on the plans that charge one: total payable = price × (1 + 1.5% × months), so 6 months is +9%. SPayLater and TikTok PayLater call it a profit rate or processing fee because both are Shariah-compliant; Atome calls it a service fee.

| Provider | 0% plans | Fee-bearing plans |
| --- | --- | --- |
| SPayLater | 1-month. 3-month on Shopee marketplace checkouts only (not ShopeeFood, insurance, prepaid, bills and tickets) | 12, 18 and 24-month at about 1.5% per month, eligible users only. The 6-month plan is disputed: some sources say 0%, others about 1.5% per month |
| TikTok PayLater | 1-month and 6-month, shown as 0% per month at checkout. The 6-month plan carries a 0% fees badge, so it may be promotional | 12-month at about 1.5% per month (RM0.21 per month on a RM13.99 order). Other tenures not seen |
| Atome | 3-month (3 payments) | 6 and 12-month at 1.5% per month. Minimum spend RM10 for the 6-month plan |

Atome's minimum bill for the 3-month plan is about RM25 on one merchant page, and merchants may set their own higher minimums.

## Limits and eligibility

All three set the limit per user and change it based on repayment behaviour, so a limit is never a constant.

| Provider | Limit | How it is set |
| --- | --- | --- |
| SPayLater | RM2,500 to RM10,000 | Payment history and spending. Users cannot apply for an increase. A temporary limit is used before the permanent one |
| TikTok PayLater | Up to RM10,000 | Occupation and income given at application. Starts smaller and may rise with on-time repayment. Verified users only |
| Atome | Varies by user | Account history and repayment behaviour. New users get lower limits. Needs a credit or debit card, age 18+, a Malaysian resident |

## Late payment

SPayLater's penalty is a flat RM10 and Atome's stacks with a reactivation fee. TikTok PayLater's was not found.

| Provider | Penalty |
| --- | --- |
| SPayLater | RM10, or the outstanding principal if that is lower. The SPayLater or Shopee account is suspended until the bill is paid |
| TikTok PayLater | Not found. TikTok staff contact users who do not repay after the due date |
| Atome | Administration fee and account frozen. RM50 reactivation fee, plus RM25 if not paid within 7 days. Administration fee capped at RM150 per transaction. One review states up to RM23 per overdue instalment, so sources differ |

## Rules for generating an instalment schedule

1. Pick the start by provider. SPayLater and TikTok PayLater: first due date in a later billing cycle, never the purchase date. Atome: first payment on the purchase date.
2. Pick the due day by provider. SPayLater: a fixed day set by the user's billing option (the 1st or the 10th). Atome: the purchase day of each month.
3. Pick the number of payments. Atome's 3-month plan is 3 payments across 2 months (purchase date, +1 month, +2 months). SPayLater and TikTok PayLater: an N-month plan is N monthly bills.
4. Split the amount equally in sen and put any leftover sen in the last payment.
5. Apply the fee only where the plan has one. 0% plans: total equals the price. Fee plans: total = price × (1 + 1.5% × months).
6. Model cash flow accordingly. Atome takes one-third of the total in the purchase month. SPayLater and TikTok PayLater take nothing in the purchase month.
7. Check the order against the user's limit and the provider's plan availability before generating a schedule.

## Unverified items and sources

Five points are not confirmed by any source found:

- TikTok PayLater's first due date and late charge, and whether the 6-month 0% is a promotion or standard.
- Whether SPayLater's 6-month plan is 0% or fee-bearing.
- Which SPayLater bill a purchase lands on, given the billing cut-off.
- Whether an order above the available limit can be part-paid at checkout.
- Whether SPayLater in-store (partner outlet) purchases require the first instalment at checkout.

Boost PayFlex (formerly Boost PayLater) was researched but left out for lack of a real checkout example. Its terms are: nothing at checkout, first payment about 1 month later, a wakalah fee of RM5 (under RM100) or RM10 (over RM100) per transaction, and a profit rate of 2.5% per month. Add it only after confirming the formula against a real schedule.

Figures come from search results and provider pages; the pages were not opened individually.

- [Shopee Help Center: SPayLater terms](https://help.shopee.com.my/4/article/78468-%5BSPayLater%5D-What-are-the-terms-for-payment-by-SPayLater)
- [Switch: SPayLater FAQ](https://shop.switch.com.my/pages/spaylater)
- [ShopeePay: SPayLater](https://shopeepay.com.my/en/spaylater/)
- [Atome (Switch)](https://shop.switch.com.my/pages/atome)
- [Atome instalment plan (Lamarsa)](https://www.lamarsacoffee.com/atome-instalment-payment-plan)
- [Atome instalment (Zalora Malaysia)](https://support-my.zalora-ops.com/support/solutions/articles/76000040654-atome-instalment)
- [Atome late fees (Speedo Malaysia)](https://speedomalaysia.com/pages/pay-later-with-atome)
- [Atome Card (RinggitPlus)](https://ringgitplus.com/en/debit-card/Atome-Card.html)
- [Atome review (Malaysia4U)](https://malaysia4u.com/review/atome)
- [TikTok PayLater (Lowyat.NET)](https://www.lowyat.net/2024/338035/tiktok-paylater-bnpl/)
- [TikTok PayLater (TikTok Shop Seller University)](https://seller-my.tiktok.com/university/essay?knowledge_id=1243424507447056&lang=en)
