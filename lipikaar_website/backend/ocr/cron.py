def mark_old_unprocessed_uploads_as_errored():
    # print("Marking...")
    f = open("demofile2.txt", "w+")
    f.write("Now the file has more content!")
    f.close()