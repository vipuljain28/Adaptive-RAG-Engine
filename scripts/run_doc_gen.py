import sys, os, traceback

out_file = open(os.path.join(os.path.dirname(__file__), "..", "gen_result.txt"), "w", encoding="utf-8")

try:
    sys.stdout = out_file
    sys.stderr = out_file
    exec(open(os.path.join(os.path.dirname(__file__), "generate_submission_doc.py"), encoding="utf-8").read())
except Exception as e:
    out_file.write(f"\nERROR: {e}\n")
    out_file.write(traceback.format_exc())
finally:
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    out_file.close()

print("done — check gen_result.txt")
