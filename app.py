import urllib.parse
import streamlit as st
import pandas as pd
from supabase import create_client

# --- UI SETTINGS ---
st.set_page_config(page_title="Freezer Manager", page_icon="❄️")
st.title("❄️ Freezer Inventory")


URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)
TABLE = supabase.table("freezer_items")

# --- 1. INITIALIZE SESSION STATE ---
if "user" not in st.session_state:
    st.session_state.user = None

# --- 2. THE LOGIN GATE ---
if st.session_state.user is None:
    st.header("Please Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    col1, col2 = st.columns(2)
    if col1.button("Login"):
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state.user = res.user
            # 🔑 STORE THE TOKEN: Streamlit needs to remember this manually
            st.session_state.token = res.session.access_token
            st.rerun()
        except Exception as e:
            st.error(f"Login failed: {e}")

    if col2.button("Sign Up"):
        try:
            res = supabase.auth.sign_up({"email": email, "password": password})
            if res.user:
                st.success("Account created!")
                st.info("If email confirmation is on, check your inbox. Otherwise, try logging in now.")
        except Exception as e:
            st.error(f"Sign up error: {e}")

    st.stop()  # 🛑 Stops the rest of the app from running until logged in


# --- amazon search ---
if "special_msg" in st.session_state:
    st.error(st.session_state.special_msg)

    # Create two columns for the search buttons
    btn_col1, btn_col2 = st.columns(2)

    with btn_col1:
        st.link_button("📦 Amazon", st.session_state.amazon_url, use_container_width=True)

    with btn_col2:
        st.link_button("🛒 Walmart", st.session_state.walmart_url, use_container_width=True)

    if st.button("I'll buy it later"):
        # Clear everything from session state
        for key in ["special_msg", "amazon_url", "walmart_url", "sad_burst"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

# --- display icons ---
if "sad_burst" in st.session_state:
    # This creates a "waterfall" of sad toasts in the corner
    for _ in range(6):
        st.toast("Everything is gone...", icon="😢")

    del st.session_state.sad_burst
    del st.session_state.special_msg

# --- SIDEBAR: ADD ITEMS ---
with (st.sidebar):
    st.header("Add New Items")
    new_item = st.text_input("Item Name (e.g., Pizza)").strip().title()
    add_qty = st.number_input("Quantity to Add", min_value=1, value=1)

    if st.button("Add to Freezer"):
        if new_item:
            # 🔑 RE-ATTACH TOKEN: This is the "ID Card" for the Add button
            if "token" in st.session_state:
                supabase.postgrest.auth(st.session_state.token)

            current_uid = st.session_state.user.id

            # ... rest of your existing logic (existing = TABLE.select...)

            # 1. CHECK: Does this item already exist for this user?
            existing = TABLE \
                .select("id, quantity") \
                .eq("item_name", new_item) \
                .eq("user_id", current_uid) \
                .execute()

            try:
                if existing.data:
                    # 2. UPDATE: If it exists, add the new quantity to the old one
                    new_total = existing.data[0]['quantity'] + add_qty
                    TABLE \
                        .update({"quantity": new_total}) \
                        .eq("id", existing.data[0]['id'])\
                        .eq("user_id", current_uid) \
                        .execute()
                else:
                    # 3. INSERT: If it doesn't exist, create it
                    TABLE \
                        .insert({
                        "item_name": new_item,
                        "quantity": add_qty,
                        "user_id": current_uid
                    }) \
                        .execute()

                st.success(f"Updated {new_item}!")
                st.rerun()
            except Exception as e:
                st.error(f"Database error: {e}")
        else:
            st.error("Please enter a name.")

# --- MAIN PAGE: INVENTORY LIST ---
st.subheader("Current Contents")

# 🔑 RE-ATTACH TOKEN: If we have a token in session_state, tell Supabase to use it
if "token" in st.session_state:
    supabase.postgrest.auth(st.session_state.token)

# Now it is safe to fetch your data
response = TABLE.select("*").eq("user_id", st.session_state.user.id).execute()


# # --- DEBUGGING (Keep these until it works!) ---
# st.write(f"Logged in as: `{st.session_state.user.email}`")
# st.write(f"Your Secret UID: `{st.session_state.user.id}`")
# st.write(f"Raw Database Response: {response.data}")
# # ----------------------------------------------

df = pd.DataFrame(response.data)

if df.empty:
    st.info("The freezer is empty. Add something from the sidebar!")
else:
    # Create a nice layout for the items
    for index, row in df.iterrows():
        cols = st.columns([3, 3, 1, 2, 2])

        # cols[0].write(f"**{row['item_id']}**")
        cols[0].write(f"**{row['item_name']}**")
        cols[1].write(f"{row['quantity']} in stock")

        # User input for how many to remove
        remove_amt = cols[2].number_input(f"Qty", min_value=1, max_value=max(row['quantity'], 1), key=f"qty_{row['item_name']}")

        # Button to confirm removal
        if cols[3].button("Eat It", key=f"eat_btn_{row['id']}"):

            new_qty = row['quantity'] - remove_amt

            if new_qty <= 0:
                TABLE.update({"quantity" : 0})\
                             .eq("item_name", row['item_name'])\
                             .eq("user_id", st.session_state.user.id)\
                             .execute()

                # 1. Create the Amazon Search Link
                query = urllib.parse.quote(row['item_name'])
                # Store links in session state
                st.session_state.amazon_url = f"https://www.amazon.com/s?k={query}"
                st.session_state.walmart_url = f"https://www.walmart.com/search?q={query}"

                # 2. Store the message and the link in session state
                st.session_state.special_msg = f"The {row['item_name']} is gone! Where would you like to restock?"
                st.session_state.sad_burst = True
                st.session_state.special_msg = f"The {row['item_name']} is officially gone. 😢"
            else:
                TABLE.update({"quantity" : new_qty}).eq("item_name", row['item_name'])\
                    .eq("user_id", st.session_state.user.id).execute()

            st.rerun()

        if cols[4].button("Delete It!", key=f"del_btn_{row['id']}"):
            if row['quantity'] < 1:
                TABLE.delete()\
                    .eq("item_name", row['item_name'])\
                    .eq("user_id", st.session_state.user.id)\
                    .execute()

                st.rerun()
            else:
                st.session_state.special_msg = f"Can't delete {row['item_name']} until it's gone."


    # --- DISPLAY MESSAGES AFTER RERUN ---
    if "special_msg" in st.session_state:
        # st.balloons()  # Optional fun effect!
        st.snow()
        st.success(st.session_state.special_msg)
        # Delete it so it doesn't show up forever
        del st.session_state.special_msg

st.divider()
st.caption("Each login has access to it's own unique freezer contents")
st.caption("Crabb-Freezer V-1.10")
