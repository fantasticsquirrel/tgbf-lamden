CREATE TABLE trade_history (
    contract_name TEXT NOT NULL,
    token_symbol TEXT NOT NULL,
    price REAL NOT NULL,
    time INTEGER NOT NULL,
    amount REAL NOT NULL,
    type TEXT NOT NULL
)