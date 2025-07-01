import streamlit as st
import pandas as pd
import random
import itertools

st.set_page_config(page_title="Diverse Revenue Forecast Simulator", layout="wide")
st.title("EPP Revenue Forecast (Diverse Mix Model)")

# ----------------------------
# Sidebar - Inputs
# ----------------------------
st.sidebar.header("Simulation Settings")

months = st.sidebar.slider("Forecast Months", 1, 12, 6)
net_target = st.sidebar.number_input("Net Profit Target", value=1_000_000)
near_target_threshold = st.sidebar.number_input("Show Near-Target Scenarios (≥)", value=800_000)
coaching_price = st.sidebar.number_input("Coaching Price per Engagement", value=8750)
coaching_clients = st.sidebar.number_input("Total Coaching Engagements", min_value=0, value=5)

# Deal Inputs
deal_values = st.sidebar.multiselect("Deal Values", [500_000, 1_000_000, 1_500_000, 2_000_000, 2_500_000], default=[500_000, 1_500_000, 2_500_000])
deal_rate_map = {
    500_000: [0.05, 0.07],
    1_000_000: [0.07, 0.11],
    1_500_000: [0.11, 0.13],
    2_000_000: [0.11, 0.13, 0.17],
    2_500_000: [0.13, 0.17]
}
commission_rates = sorted(set(r for val in deal_values for r in deal_rate_map[val]))

min_deals = st.sidebar.number_input("Min Deals per Month", value=0)
max_deals = st.sidebar.number_input("Max Deals per Month", value=3)
batch_size = st.sidebar.number_input("Batch Size", value=5000, step=1000)
total_batches = st.sidebar.number_input("Number of Batches", value=5)

# ----------------------------
# Monthly Expenses
# ----------------------------
st.subheader("Monthly Expenses")
if "expenses" not in st.session_state:
    st.session_state.expenses = [
        {"label": "Travel & Expenses", "amount": 6000.0},
        {"label": "Marketing Costs", "amount": 600.0},
        {"label": "Marketing Agency", "amount": 3000.0},
        {"label": "Full-Time VA Salary", "amount": 1200.0},
        {"label": "Part-Time VA Salary", "amount": 400.0},
        {"label": "Finance VA Salary", "amount": 400.0},
        {"label": "AI/Automations", "amount": 250.0},
        {"label": "Software & SaaS Tools", "amount": 600.0},
        {"label": "Legal & Compliance Fees", "amount": 300.0},
        {"label": "Insurance (Liability, E&O, Cyber)", "amount": 300.0},
    ]

for i, exp in enumerate(st.session_state.expenses):
    col1, col2, col3 = st.columns([4, 3, 1])
    exp["label"] = col1.text_input(f"Label {i+1}", value=exp["label"], key=f"label_{i}")
    exp["amount"] = col2.number_input(f"Amount {i+1}", value=float(exp["amount"]), min_value=0.0, key=f"amount_{i}")
    if col3.button("❌", key=f"remove_{i}"):
        st.session_state.expenses.pop(i)
        st.rerun()

if st.button("Add Another Expense"):
    st.session_state.expenses.append({"label": f"Expense {len(st.session_state.expenses)+1}", "amount": 0.0})
    st.rerun()

total_expense_per_month = sum(exp["amount"] for exp in st.session_state.expenses)
st.markdown(f"**Total Monthly Expense:** ${total_expense_per_month:,.2f}")

# ----------------------------
# Run Simulation
# ----------------------------
if st.button("Run Simulation"):
    coaching_revenue = coaching_clients * coaching_price
    results = []
    total_expenses = total_expense_per_month * months

    all_deal_options = [(val, rate) for val in deal_values for rate in deal_rate_map[val]]

    progress = st.progress(0)
    total_iterations = total_batches

    for b in range(total_batches):
        batch_results = []
        for _ in range(batch_size):
            plan = []  # a plan = list of monthly deal mixes
            for _ in range(months):
                deal_count = random.randint(min_deals, max_deals)
                month_deals = random.choices(all_deal_options, k=deal_count)
                plan.append(month_deals)

            monthly_commission = [0] * months
            for i, month in enumerate(plan):
                for val, rate in month:
                    commission = val * rate
                    monthly_pmt = commission / 12
                    for j in range(i + 2, i + 14):
                        if j < months:
                            monthly_commission[j] += monthly_pmt

            commission_revenue = sum(monthly_commission)
            total_revenue = coaching_revenue + commission_revenue
            net_profit = total_revenue - total_expenses

            if net_profit >= near_target_threshold:
                batch_results.append({
                    "Deal Plan": plan,
                    "Total Coaching Revenue": coaching_revenue,
                    "Total Deal Revenue (Recognized 2025)": commission_revenue,
                    "Total Revenue": total_revenue,
                    "Net Profit": net_profit,
                    "Total Coaching": coaching_clients,
                    "Total Deals": sum(len(m) for m in plan),
                    "Workload Score": coaching_clients + sum(len(m) for m in plan),
                })

        results.extend(batch_results)
        progress.progress((b + 1) / total_batches)

    # ----------------------------
    # Results
    # ----------------------------
    if results:
        df = pd.DataFrame(results)
        df = df[df["Net Profit"] >= near_target_threshold]
        df = df.sort_values(by=["Net Profit"], ascending=False).reset_index(drop=True)
        df["Net Profit"] = df["Net Profit"].round(2)
        df["Total Revenue"] = df["Total Revenue"].round(2)

        st.success(f"Found {len(df)} scenario(s) with Net Profit ≥ ${near_target_threshold:,.0f}")
        st.dataframe(df.head(100))

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download Results as CSV", data=csv, file_name="diverse_forecast_results.csv", mime="text/csv")
    else:
        st.warning("No profitable scenarios found. Try increasing coaching, deal mix, or deal count.")
