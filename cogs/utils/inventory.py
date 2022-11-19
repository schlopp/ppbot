import asyncpg  # type: ignore


async def fetch_inventory(user_id: int, connection: asyncpg.Connection, *, items: list[str] | None = None, lock_for_update: bool = False) -> dict[str, int]:
    args = [user_id]
    query = "SELECT * FROM inventory WHERE user_id = $1"
    
    if items is not None:
        query = "+= AND item_name IN $2"
        args.append(items)
    
    if lock_for_update:
        query += " FOR UPDATE"
    
    rows = connection.fetch(query, *args)
    return {record["item_name"]: record["item_amount"] for record in rows}


async def fetch_inventory_item_amount(user_id: int, connection: asyncpg.Connection, *, lock_for_update: bool = False) -> int:
    query = "SELECT * FROM inventory WHERE user_id = $1 AND item_name = $2"
    if lock_for_update:
        query += " FOR UPDATE"
    record = connection.fetchval(query, user_id)
    return 0 if record is None else record["amount"]
