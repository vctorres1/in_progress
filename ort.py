import streamlit as st
import pandas as pd
from ortools.sat.python import cp_model
import itertools

st.set_page_config(page_title="Constraint-Based Forecast Simulator", layout="wide")
st.title("Constraint-Based Forecast Simulator")

# -------------------------
# USER INPUTS
# -------------------------
st.sidebar.header("Forecast Parameters")
months = st.sidebar.slider("Forecast Period (months)", 1, 12, 6)
net_target = st.sidebar.number_input("Net Profit Target ($)", value=1_000_000)
coaching_price = st.sidebar.number_input("Coaching Price per Engagement ($)", value=8750)

st.sidebar.subheader("Deal Settings")
deal_values = st.sidebar.multiselect("Deal Values ($)", [500_000, 1_000_000, 1_500_000, 2_000_000, 2_500_000], default=[500_000, 1_500_000, 2_500_000])
commission_map = {
    500_000: [0.17, 0.13],
    1_000_000: [0.11, 0.07],
    1_500_000: [0.11],
    2_000_000: [0.07],
    2_500_000: [0.05]
}

# -------------------------
# EXPENSE SETTINGS
# -------------------------
st.sidebar.subheader("Monthly Expenses")
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
        {"label": "Insurance", "amount": 300.0},
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
monthly_target = (net_target / months) + total_expense_per_month

# -------------------------
# CONSTRAINTS FROM USER
# -------------------------
st.sidebar.subheader("Workload Constraints")
max_deals_per_month = st.sidebar.slider("Max Deals per Month", 0, 5, 3)
max_coaching_per_month = st.sidebar.slider("Max Coaching Clients per Month", 0, 5, 3)

# -------------------------
# RUN SIMULATION
# -------------------------
if st.button("Run Constraint-Based Forecast"):
    model = cp_model.CpModel()

    # Define variables for each month
    coaching_vars = []
    deal_vars = []
    revenue_exprs = []
    commission_exprs = []
    expense_exprs = []

    for m in range(months):
        coaching = model.NewIntVar(0, max_coaching_per_month, f"coaching_{m}")
        coaching_vars.append(coaching)

        # Deal configuration space
        deal_combos = [(v, r) for v in deal_values for r in commission_map[v]]
        deal_set = []
        for idx, (val, rate) in enumerate(deal_combos):
            d = model.NewIntVar(0, max_deals_per_month, f"deal_{m}_{idx}")
            deal_set.append((d, val, rate))
        deal_vars.append(deal_set)

        # Compute revenue for this month
        coaching_rev = coaching * int(coaching_price)
        commission_rev = sum([int(v * r / 12 * max(0, (months - m - 2))) * d for d, v, r in deal_set])
        revenue_exprs.append(coaching_rev + commission_rev)
        commission_exprs.append(commission_rev)
        expense_exprs.append(int(total_expense_per_month))

    # Total net profit
    net_profit = sum(revenue_exprs) - months * int(total_expense_per_month)
    model.Add(net_profit >= int(net_target))

    # Objective: minimize workload
    workload = sum(coaching_vars) + sum([d for month_deals in deal_vars for d, _, _ in month_deals])
    model.Minimize(workload)

    # Solve
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        rows = []
        for m in range(months):
            row = {"Month": m+1, "Coaching Clients": solver.Value(coaching_vars[m])}
            for i, (d, v, r) in enumerate(deal_vars[m]):
                count = solver.Value(d)
                if count > 0:
                    row[f"Deal {i+1}"] = f"{count} x ${v} @ {int(r*100)}%"
            rows.append(row)

        df = pd.DataFrame(rows)
        st.success("✅ Forecast plan found.")
        st.dataframe(df)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download Plan as CSV", csv, file_name="forecast_plan.csv", mime="text/csv")
    else:
        st.warning("⚠️ No viable plan found. Try relaxing constraints or increasing months.")
