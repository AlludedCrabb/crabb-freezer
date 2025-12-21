import streamlit as st
import sqlite3
import q as pd


# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("freezer_inventory.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS inventory 
                 (item_name TEXT PRIMARY KEY,
                  quantity INTEGER)'''
              )
    conn.commit()
    return conn


conn = init_db()

# --- UI SETTINGS ---
st.set_page_config(page_title="Freezer Manager", page_icon="❄️")
st.title("❄️ Freezer Inventory")

# --- SIDEBAR: ADD ITEMS ---
with st.sidebar:
    st.header("Add New Stock")
    new_item = st.text_input("Item Name (e.g., Pizza)").strip().title()
    add_qty = st.number_input("Quantity to Add", min_value=1, value=1)

    if st.button("Add to Freezer"):
        if new_item:
            c = conn.cursor()
            # "UPSERT" logic: Add if new, update quantity if exists
            c.execute('''INSERT INTO inventory (item_name, quantity) 
                         VALUES(?, ?) 
                         ON CONFLICT(item_name) 
                         DO UPDATE SET quantity = quantity + excluded.quantity''',
                      (new_item, add_qty))
            conn.commit()
            st.success(f"Added {add_qty} {new_item}(s)!")
            st.rerun()
        else:
            st.error("Please enter a name.")

# --- MAIN PAGE: INVENTORY LIST ---
st.subheader("Current Contents")
df = pd.read_sql_query("SELECT * FROM inventory WHERE quantity > 0", conn)

if df.empty:
    st.info("The freezer is empty. Add something from the sidebar!")
else:
    # Create a nice layout for the items
    for index, row in df.iterrows():
        cols = st.columns([3, 2, 2, 2])

        cols[0].write(f"**{row['item_name']}**")
        cols[1].write(f"{row['quantity']} in stock")

        # User input for how many to remove
        remove_amt = cols[2].number_input(f"Qty", min_value=1, max_value=row['quantity'], key=f"num_{row['item_name']}")

        # Button to confirm removal
        if cols[3].button("Eat It", key=f"btn_{row['item_name']}"):
            c = conn.cursor()
            new_qty = row['quantity'] - remove_amt

            if new_qty <= 0:
                c.execute("DELETE FROM inventory WHERE item_name = ?", (row['item_name'],))
            else:
                c.execute("UPDATE inventory SET quantity = ? WHERE item_name = ?", (new_qty, row['item_name']))

            conn.commit()
            st.rerun()

st.divider()
st.caption("Shared Freezer App - Accessible by anyone with the link.")