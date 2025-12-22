import streamlit as st
import sqlite3
import pandas as pd

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

# --- display icons ---
if "sad_burst" in st.session_state:
    # This creates a "waterfall" of sad toasts in the corner
    for _ in range(6):
        st.toast("Everything is gone...", icon="😢")
    st.error(st.session_state.special_msg)

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
        cols = st.columns([1, 3, 2, 3, 2])

        cols[0].write(f"**{row['item_id']}**")
        cols[1].write(f"**{row['item_name']}**")
        cols[2].write(f"{row['quantity']} in stock")

        # User input for how many to remove
        remove_amt = cols[3].number_input(f"Qty", min_value=1, max_value=max(row['quantity'], 1), key=f"num_{row['item_name']}")

        # Button to confirm removal
        if cols[4].button("Eat It", key=f"btn_{row['item_name']}"):
            c = conn.cursor()
            new_qty = row['quantity'] - remove_amt

            if new_qty <= 0:
                # Option A: Delete the item
                # c.execute("DELETE FROM inventory WHERE item_name = ?", (row['item_name'],))
                c.execute("UPDATE inventory SET quantity = 0 WHERE item_name = ?", (row['item_name'],))
                # Set a "sticky note" for the message
                # st.session_state.special_msg = f"✨ You finished the last of the {row['item_name']}!"
                st.session_state.sad_burst = True
                st.session_state.special_msg = f"The {row['item_name']} is officially gone. 😢"
            else:
                # Option B: Just update the number
                c.execute("UPDATE inventory SET quantity = ? WHERE item_name = ?", (new_qty, row['item_name']))

            conn.commit()
            st.rerun()

    # --- DISPLAY MESSAGES AFTER RERUN ---
    if "special_msg" in st.session_state:
        st.balloons()  # Optional fun effect!
        st.success(st.session_state.special_msg)
        # Delete it so it doesn't show up forever
        del st.session_state.special_msg

st.divider()
st.caption("Shared Freezer App - Accessible by anyone with the link.")
st.caption("Crabb-Freezer V-1.01")
