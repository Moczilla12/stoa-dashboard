"""Parallel eth_getLogs scan via daybreak RPC (max 2000 blocks/query).
Main RPC is policy-blocked for this task; dRPC/blockvectra cap at 100 blocks.
Daybreak caps at 2000 blocks -> ~2,600 chunks, parallelised.
"""
import json, time, requests
from concurrent.futures import ThreadPoolExecutor, as_completed

RPC = "https://robinhood.daybreak-rpc.network"
ROUTER = "0x2F2804fad735a38015650f32f95Ad5E08D6B3eE5"
TOPIC0 = "0x2bbce25631e8fa58085b7ea5929726c3acdf2df8d6b1f099eb32fb7425a4f6da"
DEPLOY_BLOCK = 114244443
CHUNK = 2000
WORKERS = 15

def rpc(method, params, timeout=45):
    last = None
    for attempt in range(3):
        try:
            r = requests.post(RPC, json={"jsonrpc":"2.0","id":1,"method":method,"params":params}, timeout=timeout)
            d = r.json()
            if "error" in d:
                raise Exception(d["error"])
            return d["result"]
        except Exception as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise last

def fetch_chunk(pair):
    start, end = pair
    logs = rpc("eth_getLogs", [{"fromBlock": hex(start), "toBlock": hex(end), "address": ROUTER, "topics": [TOPIC0]}])
    return (start, end, logs)

latest = int(rpc("eth_blockNumber", []), 16)
print("latest block:", latest, flush=True)
chunks = []
s = DEPLOY_BLOCK
while s <= latest:
    chunks.append((s, min(s + CHUNK - 1, latest)))
    s += CHUNK
print("chunks:", len(chunks), flush=True)

all_logs = []
failed = []
done = 0
t0 = time.time()
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    futs = {ex.submit(fetch_chunk, c): c for c in chunks}
    for fut in as_completed(futs):
        c = futs[fut]
        done += 1
        try:
            _, _, logs = fut.result()
            all_logs.extend(logs)
            if logs:
                print(f"[{done}/{len(chunks)}] {c[0]}-{c[1]}: {len(logs)} logs", flush=True)
        except Exception as e:
            failed.append(c)
            print(f"[{done}/{len(chunks)}] {c[0]}-{c[1]}: FAILED {e}", flush=True)
        if done % 500 == 0:
            print(f"... {done}/{len(chunks)} chunks, {len(all_logs)} logs so far, {time.time()-t0:.0f}s", flush=True)

print(f"pass 1 done: {len(all_logs)} logs, {len(failed)} failed chunks, {time.time()-t0:.0f}s", flush=True)
# retry failed chunks serially, one more time
still_failed = []
for c in failed:
    try:
        _, _, logs = fetch_chunk(c)
        all_logs.extend(logs)
        print(f"retry {c[0]}-{c[1]}: {len(logs)} logs", flush=True)
    except Exception as e:
        still_failed.append(c)
        print(f"retry {c[0]}-{c[1]}: STILL FAILED {e}", flush=True)

print("failed chunks remaining:", still_failed, flush=True)

def addr(topic):
    return "0x" + topic[-40:]

def u256(word):
    return int(word, 16)

swaps = []
for log in all_logs:
    t = log["topics"]
    data = log["data"][2:]
    words = [data[i:i+64] for i in range(0, len(data), 64)]
    swaps.append({
        "blockNumber": int(log["blockNumber"], 16),
        "txHash": log["transactionHash"],
        "logIndex": int(log["logIndex"], 16),
        "sender": addr(t[1]),
        "to": addr(t[2]),
        "referrer": addr(t[3]),
        "tokenIn": "0x" + words[0][-40:],
        "tokenOut": "0x" + words[1][-40:],
        "amountIn": str(u256(words[2])),
        "amountOut": str(u256(words[3])),
        "mid": "0x" + words[4][-40:],
        "venue1": "0x" + words[5][-40:],
        "venue2": "0x" + words[6][-40:],
    })
blocks = sorted(set(s["blockNumber"] for s in swaps))
ts = {}
for b in blocks:
    blk = rpc("eth_getBlockByNumber", [hex(b), False])
    ts[b] = int(blk["timestamp"], 16)
for s in swaps:
    s["timestamp"] = ts[s["blockNumber"]]
swaps.sort(key=lambda s: (s["blockNumber"], s["logIndex"]))
json.dump({"latestBlock": latest, "count": len(swaps), "swaps": swaps,
           "failedChunks": [[a, b] for a, b in still_failed]},
          open("/home/hatch/workspace/stoa-dashboard/swaps.json", "w"), indent=1)
print("TOTAL swaps:", len(swaps))
print("senders:", len(set(s["sender"] for s in swaps)))
if swaps:
    print("first:", swaps[0]["blockNumber"], swaps[0]["timestamp"], swaps[0]["txHash"][:18])
    print("last:", swaps[-1]["blockNumber"], swaps[-1]["timestamp"], swaps[-1]["txHash"][:18])
