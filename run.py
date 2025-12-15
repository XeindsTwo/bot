from watchgod import run_process

def start_bot():
    import asyncio
    from app.main import main
    asyncio.run(main())

if __name__ == "__main__":
    run_process("app", start_bot)