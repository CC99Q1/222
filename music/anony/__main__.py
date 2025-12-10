import asyncio
import importlib
import os
import shutil
import sys  

def clear_temp_files(context="Startup"):

    try:
        print(f"[Anony {context}]: Cleaning up temporary cache files...")
        

        pycache_count = 0

        project_dir = os.path.dirname(os.path.abspath(__file__))
        
        for root, dirs, files in os.walk(project_dir):
            if "__pycache__" in dirs:
                pycache_path = os.path.join(root, "__pycache__")
                try:
                    shutil.rmtree(pycache_path)
                    pycache_count += 1
                except OSError as e:
                    print(f"[Cleanup Error]: Failed to remove {pycache_path}: {e}")
        
        if pycache_count > 0:
            print(f"[Anony {context}]: Removed {pycache_count} __pycache__ directories.")
        else:
            print("[Anony {context}]: No __pycache__ directories found to clean.")

        session_count = 0

        for file in os.listdir(project_dir):
            if file.endswith(".session") or file.endswith(".session-journal"):
                try:
                    os.remove(os.path.join(project_dir, file))
                    session_count += 1
                except OSError as e:
                    print(f"[Cleanup Error]: Failed to remove {file}: {e}")
        
        if session_count > 0:
            print(f"[Anony {context}]: Cleaned {session_count} old session files.")
        else:
            print("[Anony {context}]: No old session files found to clean.")
            
    except Exception as e:
        print(f"[Cleanup Error]: Error during temp file cleanup: {e}")


async def keep_alive(logger, userbot):

    await asyncio.sleep(15)
    logger.info("Keep-Alive task started.")
    
    while True:
        try:
            await asyncio.sleep(3600) 
            
            if not userbot.clients:
                continue

            ping_count = 0
            for client in userbot.clients:
                try:
                    await client.get_me() 
                    ping_count += 1
                except Exception as e:
                    logger.error(f"Keep-Alive: Failed to ping {client.name}. Error: {e}")
            
            if ping_count > 0:
                logger.info(f"Keep-Alive: Successfully pinged {ping_count} assistant(s).")

        except asyncio.CancelledError:
            logger.info("Keep-Alive task cancelled.")
            break
        except Exception as e:
            logger.error(f"Keep-Alive task encountered an error: {e}")
            await asyncio.sleep(300)



async def main(logger, db, app, userbot, anon, tasks, all_modules):
    

    await db.connect()
    await app.boot()
    await userbot.boot()
    await anon.boot()

    logger.info("Starting Keep-Alive task...")
    
    ka_task = asyncio.create_task(keep_alive(logger, userbot))
    tasks.append(ka_task)

    for module in all_modules:
        importlib.import_module(f"anony.plugins.{module}")
    logger.info(f"Loaded {len(all_modules)} modules.")

    sudoers = await db.get_sudoers()
    app.sudoers.update(sudoers)
    app.bl_users.update(await db.get_blacklisted())
    logger.info(f"Loaded {len(app.sudoers)} sudo users.")
    
    
    from pyrogram import idle
    await idle()
    
    logger.info("Stopping...")
    
    for task in tasks:
        task.cancel()
        try:
            await task
        except:
            pass
    
    
    await asyncio.gather(
        app.exit(),
        userbot.exit(),
        db.close()
    )
    
    
    clear_temp_files("Shutdown")

    logger.info("Stopped.")


if __name__ == "__main__":
    
    try:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        print("[Anony Startup]: UVLoop policy set. [Fast Startup Enabled]")
    except ImportError:
        print("[Anony Startup]: UVLoop not found, using standard asyncio loop. [Standard Startup]")

    
    clear_temp_files("Startup")

    
    from anony import anon, app, db, logger, tasks, userbot
    from anony.plugins import all_modules
    
    try:
        asyncio.get_event_loop().run_until_complete(
            main(logger, db, app, userbot, anon, tasks, all_modules)
        )
    except KeyboardInterrupt:
        pass
    except Exception as e:
        
        print(f"[FATAL ERROR]: {e}")
        logger.error(f"Bot crashed with fatal error: {e}")