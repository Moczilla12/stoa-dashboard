"""Fetch name/symbol/decimals for every unique token in swaps.json via eth_call.
Uses daybreak RPC (main RPC is policy-blocked; dRPC caps log ranges, but eth_call is fine there too).
Selectors: name() 0x06fdde03, symbol() 0x95d89b41, decimals() 0x313ce567.
"""
import json, time, requests

RPC = "https://robinhood.daybreak-rpc.network"

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

def call(to, data):
    return rpc("eth_call", [{"to": to, "data": data}, "latest"])

def decode_string(hexdata):
    # ABI string: 32B offset, 32B length, data
    b = bytes.fromhex(hexdata[2:])
    if len(b) < 64:
        return None
    ln = int.from_bytes(b[32:64], "big")
    raw = b[64:64+ln]
    try:
        return raw.decode("utf-8")
    except Exception:
        return None

def decode_uint(hexdata):
    b = bytes.fromhex(hexdata[2:])
    if len(b) < 32:
        return None
    return int.from_bytes(b[-32:], "big")

swaps = json.load(open("/home/hatch/workspace/stoa-dashboard/swaps.json"))["swaps"]
addrs = set()
for s in swaps:
    addrs.add(s["tokenIn"].lower())
    addrs.add(s["tokenOut"].lower())
# native ETH is address(0) in the event
addrs.discard("0x0000000000000000000000000000000000000000")
print("unique token addresses (excl. native):", len(addrs), flush=True)

tokens = {}
for a in sorted(addrs):
    entry = {"name": None, "symbol": None, "decimals": None}
    try:
        entry["name"] = decode_string(call(a, "0x06fdde03"))
    except Exception as e:
        print(a, "name() failed:", e, flush=True)
    try:
        entry["symbol"] = decode_string(call(a, "0x95d89b41"))
    except Exception as e:
        print(a, "symbol() failed:", e, flush=True)
    try:
        entry["decimals"] = decode_uint(call(a, "0x313ce567"))
    except Exception as e:
        print(a, "decimals() failed:", e, flush=True)
    tokens[a] = entry
    print(a, entry, flush=True)
    time.sleep(0.3)

json.dump(tokens, open("/home/hatch/workspace/stoa-dashboard/tokens.json", "w"), indent=1)
print("saved tokens.json:", len(tokens), "tokens")
