import traceback
try:
    import main
    main.init_queue_db()
    print("SUCCESS")
except BaseException as e:
    with open('real_crash.log', 'w') as f:
        traceback.print_exc(file=f)
