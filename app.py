import streamlit as st
from experta import *
from typing import List

# Define Fact and Engine
class UserData(Fact):
    pass

class BudgetAdvisor(KnowledgeEngine):
    def __init__(self):
        super().__init__()
        self.advice_list = []

    def _add_advice(self, msg):
        self.advice_list.append(msg)

    @Rule(UserData(savings_percent=P(lambda x: x < 10)))
    def low_savings(self):
        self._add_advice("⚠️ Your savings are below 10% of your income.")

    @Rule(UserData(debt_percent=P(lambda x: x > 20)))
    def pay_debt(self):
        self._add_advice("⚠️ More than 20% of your income goes to debt repayment.")

    @Rule(UserData(savings_percent=P(lambda x: x > 20)))
    def encourage_investment(self):
        self._add_advice("✅ Consider investment as part of your savings.")

    @Rule(UserData(expenses_tracking=False))
    def recommend_track_expenses(self):
        self._add_advice("📌 Track daily expenses to manage your budget better.")

    @Rule(UserData(subscription_percent=P(lambda x: x > 10)))
    def recommend_reduce_subscriptions(self):
        self._add_advice("📌 Reduce unnecessary subscriptions.")

    @Rule(UserData(emergency_fund=P(lambda x: x < 500)))
    def low_emergency_fund(self):
        self._add_advice("📌 Build an emergency fund for unexpected expenses.")

    @Rule(UserData(goal_exists=True, savings=P(lambda x: x < 500), goal_amount=1000))
    def low_savings_for_goal(self):
        self._add_advice("📌 Create a monthly savings plan to reach your goal.")

    @Rule(UserData(wants_percent=P(lambda x: x > 30)))
    def high_wants_spending(self):
        self._add_advice("⚠️ Too much spending on non-essentials.")

# Streamlit Interface
st.title("💰 Student Budget Advisor")

with st.form("budget_form"):
    savings_percent = st.slider("Savings (% of income)", 0, 100, 10)
    debt_percent = st.slider("Debt Repayment (% of income)", 0, 100, 10)
    subscription_percent = st.slider("Subscription (% of income)", 0, 100, 5)
    expenses_tracking = st.checkbox("Are you currently tracking your daily expenses?")
    emergency_fund = st.number_input("Emergency Fund (RM)", 0)
    wants_percent = st.slider("Spending on Wants (%)", 0, 100, 30)
    goal_exists = st.checkbox("Do you have a financial goal (e.g. buy laptop)?")
    savings = st.number_input("Current Savings (RM)", 0)
    goal_amount = st.number_input("Goal Amount (RM)", 0)

    submitted = st.form_submit_button("Get Advice")

if submitted:
    engine = BudgetAdvisor()
    engine.reset()
    engine.declare(UserData(
        savings_percent=savings_percent,
        debt_percent=debt_percent,
        subscription_percent=subscription_percent,
        expenses_tracking=expenses_tracking,
        emergency_fund=emergency_fund,
        wants_percent=wants_percent,
        goal_exists=goal_exists,
        savings=savings,
        goal_amount=goal_amount
    ))
    engine.run()

    st.subheader("📋 Budgeting Advice")
    if engine.advice_list:
        for advice in engine.advice_list:
            st.write(advice)
    else:
        st.write("✅ Your budgeting looks healthy. Keep it up!")

