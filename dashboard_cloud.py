import MetaTrader5 as mt5
import time
from datetime import datetime, timedelta
from supabase import create_client, Client

# ----- CONFIG -----
SUPABASE_URL = "https://your-project-id.supabase.co"
SUPABASE_KEY = "your-anon-key"
SYNC_INTERVAL = 30  # seconds

# Connect to Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Connect to MT5
if not mt5.initialize():
    raise RuntimeError("MT5 failed to initialize. Make sure terminal is running and logged in.")

def sync():
    # --- Account Info ---
    info = mt5.account_info()
    if info:
        account_data = {
            "balance": info.balance,
            "equity": info.equity,
            "margin": info.margin,
            "free_margin": info.margin_free,
            "timestamp": datetime.now().isoformat()
        }
        supabase.table("account").insert(account_data).execute()

    # --- Open Positions (replace all) ---
    positions = mt5.positions_get()
    if positions:
        # Clear existing and re-insert
        supabase.table("positions").delete().neq("ticket", 0).execute()  # delete all
        for pos in positions:
            pos_dict = {
                "ticket": pos.ticket,
                "symbol": pos.symbol,
                "type": "Buy" if pos.type == 0 else "Sell",
                "volume": pos.volume,
                "price_open": pos.price_open,
                "sl": pos.sl,
                "tp": pos.tp,
                "profit": pos.profit,
                "comment": pos.comment,
                "timestamp": datetime.now().isoformat()
            }
            supabase.table("positions").insert(pos_dict).execute()

    # --- Closed Trades (only new ones, by ticket) ---
    # Fetch last 7 days to catch any missed ones
    from_date = datetime.now() - timedelta(days=7)
    deals = mt5.history_deals_get(from_date, datetime.now())
    if deals:
        for deal in deals:
            if deal.entry == 1:  # exit deal
                # Check if already inserted (optional but good)
                existing = supabase.table("closed_trades").select("ticket").eq("ticket", deal.ticket).execute()
                if not existing.data:
                    trade = {
                        "ticket": deal.ticket,
                        "symbol": deal.symbol,
                        "type": "Buy" if deal.type == 0 else "Sell",
                        "profit": deal.profit,
                        "close_time": datetime.fromtimestamp(deal.time).isoformat(),
                        "timestamp": datetime.now().isoformat()
                    }
                    supabase.table("closed_trades").insert(trade).execute()

# Run continuously
if __name__ == "__main__":
    print("Sync started. Press Ctrl+C to stop (but you can close this window if run with pythonw).")
    while True:
        try:
            sync()
            print(f"Synced at {datetime.now()}")
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(SYNC_INTERVAL)