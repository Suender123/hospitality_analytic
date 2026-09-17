# Hospitality Revenue Intelligence: EDA Summary

## Scope

The analysis combines the supplied booking, stay, hotel, guest, review, staff, and marketing files. The commercial grain is one stay transaction linked to a booking. The source data contains no currency code, so all monetary values are labelled as **currency units**.

## Headline results

| Metric | Result |
| --- | ---: |
| Total sales | 11,080,491,493 |
| Estimated profit | 4,913,835,625 |
| Estimated profit margin | 44.3% |
| Unique booking orders | 64,944 |
| Average order value | 170,616 |

## Findings

- **Executive** is the highest-sales room category, with 2,235,546,697 in sales.
- **Bengaluru** has the highest sales among hotel cities, at 1,424,827,373.
- The strongest observed year-on-year sales growth is **2024: 1.2%**.
- The correlation between discount percentage and estimated profit margin is **-0.37**. This measures association only and does not establish causality.

## Business definitions

- **Sales:** Room_Revenue + Food_Revenue + Spa_Revenue + Other_Revenue.
- **Order:** unique Booking_ID associated with a stay transaction.
- **Category:** Room_Type.
- **Region:** hotel City.
- **Customer segment:** Loyalty_Tier.
- **Product:** Hotel_Name and Room_Type.
- **Quantity:** Nights × Rooms_Booked.
- **Profit:** estimated contribution profit. The source data has no cost or profit field, so the model applies documented room-type contribution margins and ancillary cost rates. This must be replaced with actual finance costs before any financial decision is made.
- **Payment mode:** not present in the source data. Booking channel is analysed as an acquisition channel, not a payment method.

## Delivered files

- `outputs/cleaned_hospitality_transactions.csv` contains the cleaned and transformed analytical table.
- `outputs/business_question_answers.csv` contains answers to all 25 requested questions.
- `reports/figures/` contains standalone interactive Plotly charts.
