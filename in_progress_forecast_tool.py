import streamlit as st
import pandas as pd
import itertools
import random

st.set_page_config(page_title="Monthly Revenue Forecast Simulator", layout="wide")
st.title("Monthly Revenue Forecast Simulator")

# -------------------------
# USER INPUTS
# -------------------------
st.sidebar.header("Simulation Settings")

months = st.sidebar.slider("Number of Months (Forecast Period)", 1, 12, 6)
net_target = st.sidebar.number_input("Net Profit Target", value=1_000_000)
coaching_price = st.sidebar.number_input("Coaching Price per Engagement", value=8750)

min_deals = st.sidebar.number_input("Min Deals per Month", value=0)
max_deals = st.sidebar.number_input("Max Deals per Month", value=3)
deal_range = range(min_deals, max_deals + 1)

min_coaching = st.sidebar.number_input("Min Coaching Clients per Month", value=0)
max_coaching = st.sidebar.number_input("Max Coaching Clients per Month", value=3)
coaching_range = range(min_coaching, max_coaching + 1)

st.sidebar.subheader("Deal Values")
deal_values = st.sidebar.multiselect(
    "Select Deal Values",
    [500_000, 1_000_000, 1_500_000, 2_000_000, 2_500_000],
    default=[500_000, 1_500_000, 2_500_000]
)

st.sidebar.subheader("Commission Rates")
commission_rates = st.sidebar.multiselect(
    "Select Commission Rates",
    [0.05, 0.07, 0.11, 0.13, 0.17],
    default=[0.05, 0.11, 0.17]
)

# -------------------------
# EXPENSES
# -------------------------
st.markdown("## Monthly Expenses")
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
        {"label": "Insurance (Liability, E&O, Cyber)", "amount": 300.0}
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

# -------------------------
# RUN SIMULATION
# -------------------------
if st.button("Run Monthly Simulation"):
    monthly_target = (net_target / months) + total_expense_per_month
    deal_options = list(itertools.product(deal_range, deal_values, commission_rates))
    coaching_options = list(coaching_range)

    all_monthly_solutions = []
    success = True

    with st.spinner("Running monthly simulations..."):
        for month in range(months):
            month_results = []
            for coaching_count in coaching_options:
                coaching_revenue = coaching_count * coaching_price
                for deal_count, deal_value, commission_rate in deal_options:
                    if deal_count == 0:
                        total_commission = 0
                        recognized_revenue = 0
                    else:
                        commission_per_deal = deal_value * commission_rate
                        total_commission = commission_per_deal * deal_count
                        recognized_revenue = total_commission / 12 * max(0, (months - month - 2))

                    total_revenue = coaching_revenue + recognized_revenue
                    net = total_revenue - total_expense_per_month

                    if net >= monthly_target:
                        month_results.append({
                            "Month": month + 1,
                            "Coaching Clients": coaching_count,
                            "Deal Count": deal_count,
                            "Deal Value": deal_value,
                            "Commission Rate": commission_rate,
                            "Coaching Revenue": coaching_revenue,
                            "Deal Revenue": recognized_revenue,
                            "Total Revenue": total_revenue,
                            "Net": net
                        })
            if not month_results:
                success = False
                break
            best = sorted(month_results, key=lambda x: x["Net"])[-1]
            all_monthly_solutions.append(best)

    if success:
        st.success("✅ Found viable combinations for all months.")
        df = pd.DataFrame(all_monthly_solutions)
        #import ace_tools as tools; tools.display_dataframe_to_user(name="Monthly Forecast Plan", dataframe=df)
    else:
        st.warning("⚠️ Simulation failed to find combinations for one or more months. Try adjusting ranges.")
