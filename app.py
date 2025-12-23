import streamlit as st
import sqlite3
import pandas as pd
import urllib.parse

# --- DATABASE SETUP ---
# We cache this so we don't reconnect on every single click
@st.cache_resource
def init_db():
    conn = sqlite3.connect("freezer_inventory.db", check_same_thread=False)
    c = conn.cursor()
    # Added UNIQUE to item_name so the UPSERT logic actually works
    c.execute('''CREATE TABLE IF NOT EXISTS inventory 
                 (item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  item_name TEXT UNIQUE, 
                  quantity INTEGER)'''
              )
    conn.commit()
    return conn

conn = init_db()

# --- UI SETTINGS ---
st.set_page_config(page_title="Freezer Manager", page_icon="❄️")
st.title("❄️ Freezer Inventory")

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
with st.sidebar:
    st.header("Add New Items")
    new_item = st.text_input("Item Name (e.g., Pizza)").strip().title()
    add_qty = st.number_input("Quantity to Add", min_value=1, value=1)

    if st.button("Add to Freezer"):
        if new_item:
            c = conn.cursor()
            # This works now because of the UNIQUE constraint above
            c.execute('''INSERT INTO inventory (item_name, quantity) 
                         VALUES(?, ?) 
                         ON CONFLICT(item_name) 
                         DO UPDATE SET quantity = inventory.quantity + excluded.quantity''',
                      (new_item, add_qty))
            conn.commit()
            st.success(f"Added {add_qty} {new_item}(s)!")
            st.rerun()
        else:
            st.error("Please enter a name.")

# --- MAIN PAGE: INVENTORY LIST ---
st.subheader("Current Contents")
# df = pd.read_sql_query("SELECT * FROM inventory WHERE quantity > 0", conn)
df = pd.read_sql_query("SELECT * FROM inventory", conn)

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
        remove_amt = cols[2].number_input(f"Qty", min_value=1, max_value=max(row['quantity'], 1), key=f"num_{row['item_name']}")

        # Button to confirm removal
        if cols[3].button("Eat It", key=f"btn_{row['item_name']}"):
            c = conn.cursor()
            new_qty = row['quantity'] - remove_amt

            if new_qty <= 0:
                # Option A: Delete the item
                # c.execute("DELETE FROM inventory WHERE item_name = ?", (row['item_name'],))
                c.execute("UPDATE inventory SET quantity = 0 WHERE item_name = ?", (row['item_name'],))
                # Set a "sticky note" for the message
                # st.session_state.special_msg = f"✨ You finished the last of the {row['item_name']}!"

                # 1. Create the Amazon Search Link
                query = urllib.parse.quote(row['item_name'])
                # Store links in session state
                st.session_state.amazon_url = f"https://www.amazon.com/s?k={query}"
                st.session_state.walmart_url = f"https://www.walmart.com/search?q={query}"

                # 2. Store the message and the link in session state
                st.session_state.special_msg = f"The {row['item_name']} is gone! Where would you like to restock?"
                # st.session_state.replacement_link = amazon_url
                st.session_state.sad_burst = True
                st.session_state.special_msg = f"The {row['item_name']} is officially gone. 😢"
            else:
                # Option B: Just update the number
                c.execute("UPDATE inventory SET quantity = ? WHERE item_name = ?", (new_qty, row['item_name']))

            conn.commit()
            st.rerun()

        if cols[4].button("Delete It!", key=f"btn_{row['item_id']}"):
            c = conn.cursor()
            if row['quantity'] < 1:
                c.execute("DELETE FROM inventory WHERE item_name = ?", (row['item_name'],))

                conn.commit()
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
st.caption("Shared Freezer App - Accessible by anyone with the link.")
st.caption("Crabb-Freezer V-1.02")
