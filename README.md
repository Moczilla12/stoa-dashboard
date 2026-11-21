# Stoa Swaps — Public Dashboard (Robinhood Chain)

Public dashboard of **Stoa swaps on Robinhood Chain** (chain ID 4663): volume, traders, and routes per venue — built from on-chain data.

- **Live dashboard:** https://moczilla12.github.io/stoa-dashboard/
- **Bounty:** Stoa build bounty #3 — “Public dashboard” ($50 USDG, first working entry wins), https://stoadex.com/build#bounties
- **Referrer / payout address:** `0xc8511eD5B820E99889B168A4167FccDF73a9a2A2` (triv). Every “Swap on Stoa” link on the dashboard carries `?ref=0xc8511eD5B820E99889B168A4167FccDF73a9a2A2`, so swaps made through it earn the referrer share (10% of Stoa’s 2 bps protocol fee).

## What it shows

- Total swaps (33), unique traders (19), USDG volume (518.13 USDG, both legs), ETH volume (0.1596 ETH, both legs)
- Swaps per day (UTC), 14–20 Nov 2026
- Routes per venue, first leg: Uniswap V4 (old) 19, Uniswap V3 9, Uniswap V4 2, Aero 1, Pons 1, Ramses 1; second legs (8 two-venue swaps, all via WETH): Uniswap V4 (old) 5, Uniswap V3 2, Pons 1
- Top pairs (ETH→USDG 11, USDG→ETH 5, …) and top traders
- Full table of all 33 swaps with links to each transaction on the Robinhood Chain Blockscout explorer

All figures on the page are computed in the browser from the raw data (`data/swaps.json` + embedded copy). The static numbers in the HTML are the same values, shown when JavaScript is off.

## Data source & query

Source: `eth_getLogs` on the public Robinhood Chain RPC (`https://rpc.mainnet.chain.robinhood.com`), filtering the StoaRouter contract `0x2F2804fad735a38015650f32f95Ad5E08D6B3eE5` for the `Routed` event:

```
event Routed(
    address indexed sender, address indexed to, address indexed referrer,
    address tokenIn, address tokenOut, uint256 amountIn, uint256 amountOut,
    address mid, address venue1, address venue2
)
topic0: 0x2bbce25631e8fa58085b7ea5929726c3acdf2df8d6b1f099eb32fb7425a4f6da
```

Range: deployment block 114,244,443 → block 119,487,667 (snapshot 2026-11-21 ~01:01 UTC). The same query as Dune SQL:

```sql
SELECT block_time, tx_hash, tx_from
FROM robinhood.logs
WHERE contract_address = 0x2F2804fad735a38015650f32f95Ad5E08D6B3eE5
  AND topic0 = 0x2bbce25631e8fa58085b7ea5929726c3acdf2df8d6b1f099eb32fb7425a4f6da
ORDER BY block_time DESC
```

Raw data: [`data/swaps.json`](data/swaps.json) (33 decoded `Routed` logs), [`data/tokens.json`](data/tokens.json) (token name/symbol/decimals, resolved on-chain).

## Update the data

```bash
python3 scripts/fetch_swaps_parallel.py   # re-fetches Routed logs, writes data/swaps.json
python3 scripts/fetch_tokens.py           # re-resolves token metadata, writes data/tokens.json
python3 ../build_index.py                 # regenerates index.html (kept outside the repo)
```

(Or edit `data/swaps.json` directly — the page recomputes everything from it at load.)

## Notes

- Two different tokens share the symbol **STOA**: `0x13e6993417616De724F2b337D65063f229e96718` (the $STOA token, name “STOA”) and `0x1dd577f4c1b9a201cb099af9af74dcac012395c9` (name “Stoa Exchange”). The dashboard distinguishes them by address, shown as `STOA (13e6)` and `STOA (1dd5)`.
- `0x0000…` is native ETH. USDG has 6 decimals; all other tokens here have 18.
- “USDG volume” sums the USDG leg of every swap (amountIn when USDG is bought in, amountOut when USDG is received). It is not a USD price — USDG is a dollar-pegged stablecoin, so the figure approximates dollars.
- Volume is small (33 swaps in the router’s first week). That is the honest on-chain state, not a data gap: the router only went live mid-November 2026.

## License

MIT — see [LICENSE](LICENSE). Independent project, not affiliated with Stoa.
