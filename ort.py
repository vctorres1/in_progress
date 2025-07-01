import streamlit as st
import pandas as pd
from ortools.sat.python import cp_model
import itertools

st.set_page_config(page_title="Constrained Forecast Planner", layout="wide")
st.title("Constrained Revenue Forecast Planner")

# -------------------------
# USER INPUTS
# -------------------------
st.sidebar.header("Simulation Settings")

months = st.sidebar.slider("Number of Months (Forecast Period)", 1, 12, 6)
net_target = st.sidebar.number_input("Net Profit Target", value=1_000_000)
coaching_price = st.sidebar.number_input("Coaching Price per Engagement", value=8750)

min_coaching = st.sidebar.number_input("Min Coaching Clients per Month", value=0)
max_coaching = st.sidebar.number_input("Max Coaching Clients per Month", value=3)

min_deals = st.sidebar.number_input("Min Total Deals per Month", value=0)
max_deals = st.sidebar.number_input("Max Total Deals per Month", value=3)

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
# RUN OPTIMIZATION
# -------------------------
if st.button("Run Forecast Plan"):
    all_deal_types = list(itertools.product(deal_values, commission_rates))
    model = cp_model.CpModel()

    coaching_vars = []
    deal_vars = []  # deal_vars[month][deal_type] = IntVar

    for m in range(months):
        coaching = model.NewIntVar(min_coaching, max_coaching, f"coaching_{m}")
        coaching_vars.append(coaching)

        month_deals = []
        for d, (value, rate) in enumerate(all_deal_types):
            var = model.NewIntVar(0, max_deals, f"deal_m{m}_d{d}")
            month_deals.append(var)
        deal_vars.append(month_deals)

    # Constraint: total monthly deals should not exceed max_deals
    for m in range(months):
        model.Add(sum(deal_vars[m]) <= max_deals)

    # Revenue computation
    monthly_revenues = []
    for m in range(months):
        coaching_rev = coaching_vars[m] * int(coaching_price)
        deal_rev = []
        for d, (value, rate) in enumerate(all_deal_types):
            recognized = int(value * rate / 12) * max(0, months - m - 2)
            deal_rev.append(deal_vars[m][d] * recognized)
        total = coaching_rev + sum(deal_rev)
        monthly_revenues.append(total)

    total_revenue = sum(monthly_revenues)
    total_expense = int(total_expense_per_month * months)
    net_profit = total_revenue - total_expense

    model.Add(net_profit >= int(net_target))

    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        results = []
        for m in range(months):
            month_data = {
                "Month": m+1,
                "Coaching Clients": solver.Value(coaching_vars[m])
            }
            for d, (value, rate) in enumerate(all_deal_types):
                count = solver.Value(deal_vars[m][d])
                if count > 0:
                    label = f"{count} x ${value:,} @ {int(rate*100)}%"
                    month_data[f"Deal {d+1}"] = label
            results.append(month_data)
        df = pd.DataFrame(results)
        st.success("✅ Found a viable forecast plan.")
        st.dataframe(df)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download Plan as CSV", csv, "forecast_plan.csv", "text/csv")
    else:
        st.error("❌ No feasible plan found. Try loosening constraints.")
