import asyncio
from app.state import dynamic_admin_ids
from app.logger import get_d_admin_logger


async def run_debug_cli():
    # Wait for bot to initialize and dynamic admins to load
    await asyncio.sleep(8)

    print("\n" + "=" * 40)
    print("Debug CLI Mode Activated")
    print("=" * 40)

    current_admin_id = None

    while True:
        try:
            if current_admin_id is None:
                print("\nAvailable Dynamic Admins:")
                admins = list(dynamic_admin_ids)
                if not admins:
                    print("No dynamic admins found. Actions will be logged as System.")
                    current_admin_id = "System"
                else:
                    for i, aid in enumerate(admins, 1):
                        print(f"[{i}] Admin ID: {aid}")
                    print("[0] Run as System (No dynamic admin logging)")

                    print("Select Admin by number:")
                    choice = await asyncio.to_thread(input, ">>> ")
                    try:
                        choice_idx = int(choice.strip())
                        if choice_idx == 0:
                            current_admin_id = "System"
                        elif 1 <= choice_idx <= len(admins):
                            current_admin_id = admins[choice_idx - 1]
                        else:
                            print("Invalid choice.")
                            continue
                    except ValueError:
                        print("Invalid input.")
                        continue

            print(f"\n--- Debug Menu (Acting as: {current_admin_id}) ---")
            print("[1] Force fetch fiat (USD)")
            print("[2] Clear fiat debug collection")
            print("[3] Switch Admin")
            print("[0] Exit Debug CLI")

            action = await asyncio.to_thread(input, ">>> ")
            action = action.strip()

            logger = get_d_admin_logger()

            if action == "1":
                if current_admin_id != "System":
                    logger.info(f"Dynamic Admin {current_admin_id} executed CLI action: Force fetch fiat (USD)")
                print("Fetching USD rates into debug cluster...")
                from app.services.parser_service import ensure_currency

                success = await ensure_currency("USD", force=True)
                print(f"Fetch {'Success ✅' if success else 'Failed ❌'}")

            elif action == "2":
                if current_admin_id != "System":
                    logger.info(f"Dynamic Admin {current_admin_id} executed CLI action: Clear fiat debug collection")
                from app.db import get_db, get_fiat_collection_name

                db = get_db()
                result = await db[get_fiat_collection_name()].delete_many({})
                print(f"Cleared fiat debug collection. Deleted {result.deleted_count} documents.")

            elif action == "3":
                current_admin_id = None

            elif action == "0":
                print("Exiting debug CLI.")
                break
            else:
                print("Unknown command.")

        except asyncio.CancelledError:
            break
        except EOFError:
            break
        except Exception as e:
            print(f"CLI Error: {e}")
            await asyncio.sleep(1)
