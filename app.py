import streamlit as st
from experta import *
from typing import List
import hashlib
import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",          # replace if different
        password="",  # change to your actual MySQL root password
        database="budget_app"
    )
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def check_credentials(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, password FROM users WHERE username = %s", (username,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    if result:
        user_id, stored_hash = result
        if stored_hash == hash_password(password):
            return user_id
    return None

def create_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", 
                       (username, hash_password(password)))
        conn.commit()
        return True
    except mysql.connector.errors.IntegrityError:
        return False  # Username already exists
    finally:
        cursor.close()
        conn.close()


def insert_advice_to_db(user_id, data_dict, advice_text):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        INSERT INTO advice_log (
            user_id, savings_percent, debt_percent, subscription_percent, expenses_tracking,
            emergency_fund, wants_percent, goal_exists, savings, goal_amount, advice_text
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    values = (
        user_id,
        data_dict['savings_percent'],
        data_dict['debt_percent'],
        data_dict['subscription_percent'],
        data_dict['expenses_tracking'],
        data_dict['emergency_fund'],
        data_dict['wants_percent'],
        data_dict['goal_exists'],
        data_dict['savings'],
        data_dict['goal_amount'],
        advice_text
    )

    cursor.execute(query, values)
    conn.commit()
    cursor.close()
    conn.close()

def get_user_advice_history(user_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT created_at, savings_percent, debt_percent, wants_percent, advice_text
        FROM advice_log
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 10
    """, (user_id,))

    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results



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

    @Rule(UserData(goal_exists=True, savings=MATCH.s, goal_amount=MATCH.g))
    def low_savings_for_goal(self, s, g):
        if s < g:
            self._add_advice("📌 Create a monthly savings plan to reach your goal.")

    @Rule(UserData(wants_percent=P(lambda x: x > 30)))
    def high_wants_spending(self):
        self._add_advice("⚠️ Too much spending on non-essentials.")

    


if 'user_id' not in st.session_state:
    st.header("🔐 Login")
    login_username = st.text_input("Username")
    login_password = st.text_input("Password", type="password")
    login_button = st.button("Login")

    if login_button:
        user_id = check_credentials(login_username, login_password)
        if user_id:
            st.session_state.user_id = user_id
            st.success("✅ Logged in successfully!")
            st.rerun()
        else:
            st.error("❌ Invalid username or password.")

    st.markdown("---")

    with st.expander("🆕 Don't have an account? **Sign up here**"):
        signup_username = st.text_input("New Username")
        signup_password = st.text_input("New Password", type="password")
        signup_button = st.button("Create Account")

        if signup_button:
            if signup_username and signup_password:
                success = create_user(signup_username, signup_password)
                if success:
                    st.success("🎉 Account created! You can now log in.")
                else:
                    st.error("🚫 Username already exists. Try another.")
            else:
                st.warning("Please enter both username and password.")

    st.stop()



# Streamlit Interface
st.title("💰 Student Budget Advisor")
st.sidebar.button("🚪 Logout", on_click=lambda: st.session_state.clear())


with st.form("budget_form"):
    st.markdown("### 📊 Financial Ratios")
    savings_percent = st.slider("Savings (% of income)", 0, 100, 10,
                                help="How much of your monthly income do you save?")
    debt_percent = st.slider("Debt Repayment (% of income)", 0, 100, 10,
                              help="How much of your income goes to repaying loans or debt?")
    subscription_percent = st.slider("Subscription (% of income)", 0, 100, 5,
                                     help="Monthly subscription fees like Spotify, Netflix, etc.")
    wants_percent = st.slider("Spending on Wants ((% of income)", 0, 100, 30,
                              help="E.g. food delivery, gadgets, fashion (non-essentials)")

    st.markdown("### 🧾 Financial Habits & Reserves")
    expenses_tracking = st.checkbox("Do you track your daily expenses?",
                                    help="Do you use apps or notebooks to record daily spending?")
    emergency_fund = st.number_input("Emergency Fund (RM)", 0,
                                     help="Cash you can use in case of unexpected situations.")

    st.markdown("### 🎯 Financial Goal")
    goal_exists = st.checkbox("Do you have a financial goal? (e.g. buy a laptop)", value=False)
    savings = st.number_input("Current Savings for Goal (RM)", 0,
                              help="How much you've saved towards your goal so far.")
    goal_amount = st.number_input("Goal Target Amount (RM)", 0,
                                  help="Total amount you need for the goal.")

    # Optional warning if goal is unchecked but inputs are filled
    if not goal_exists and (savings > 0 or goal_amount > 0):
        st.warning("You've entered goal details, but did not check the financial goal box.")

    submitted = st.form_submit_button("Get Advice")


if submitted:
    engine = BudgetAdvisor()
    engine.reset()
    
    # Declare user input facts
    user_facts = {
        'savings_percent': savings_percent,
        'debt_percent': debt_percent,
        'subscription_percent': subscription_percent,
        'expenses_tracking': expenses_tracking,
        'emergency_fund': emergency_fund,
        'wants_percent': wants_percent,
        'goal_exists': goal_exists,
        'savings': savings,
        'goal_amount': goal_amount
    }

    engine.declare(UserData(**user_facts))
    engine.run()

    # Display advice
    st.subheader("📋 Budgeting Advice")
    if engine.advice_list:
        for advice in engine.advice_list:
            st.write(advice)
        # Save to DB
        insert_advice_to_db(
            user_id=st.session_state.user_id,
            data_dict=user_facts,
            advice_text="\n".join(engine.advice_list)
        )
    else:
        st.write("✅ Your budgeting looks healthy. Keep it up!")

st.markdown("---")
with st.expander("📜 View Past Advice"):
        past_advice = get_user_advice_history(st.session_state.user_id)
        
        if not past_advice:
            st.info("No past advice found.")
        else:
            for entry in past_advice:
                st.markdown(f"**Date:** {entry['created_at']}")
                st.text(f"Savings: {entry['savings_percent']}%, Debt: {entry['debt_percent']}%, Wants: {entry['wants_percent']}%")
                st.write(entry['advice_text'])
                st.markdown("---")






