from api.services.knowledge.retrieval import retrieve

chunks = retrieve("how much protein does a soccer player need?")

if not chunks:
    print("❌ No chunks returned — KB not connected or retrieval failed")
else:
    for c in chunks:
        print(c.title, "|", c.content[:100])
        print("---")
