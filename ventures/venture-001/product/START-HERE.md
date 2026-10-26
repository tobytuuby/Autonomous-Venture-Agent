# Studio Restock Kit v1.0 — customer guide

A self-contained, offline weekly restock worksheet for independent pottery studios. It does not send information to a server or place supplier orders. Open `restock.html` in a modern browser; no installation or account is necessary.

## First use
Extract the ZIP using your computer's built-in **Extract All** or **Extract** command first. Read this guide, then double-click `restock.html` in the extracted folder. Keep both files together. No internet connection is needed.

1. Select **Load fictional example** to explore, or **Start blank** to enter your own studio supplies.
2. Enter one inventory item per row, including consistent unit (kg, litre or piece), on-hand usable amount, confirmed inbound, reorder point, desired target, supplier pack size and pack price in your preferred currency.
3. The tool flags a reorder whenever **on hand + inbound <= reorder point**. It rounds the shortfall to the nearest full supplier pack to reach or exceed the target.
4. Review all suggested quantities against space, shelf life, purchasing budget, supplier lead time, taxes and shipping before ordering.
5. Download **inputs CSV** to preserve your edits. Import that file at the next session. Download **results CSV** or print a weekly checklist to share with your team.

## Example
Stoneware clay: on hand 12 kg; inbound 0; reorder point 15; target 40; pack size 12.5 kg; price 22 per pack. Position is 12; purchase 3 packs / 37.5 kg; estimate 66 (currency units). These are fabricated numbers, not recommended thresholds.

## Important limits
- No automatic ordering, email, payment, cloud sync, reminders, purchase approval or accounting integration.
- Calculations include only pack prices; shipping, taxes, discounts, and purchase minimums are excluded.
- Different units cannot be added. If buying boxes of 12, use 'piece' consistently and set pack size 12.
- This is a planning aid, not stock forecasting. Verify physical counts and actual supplier packaging/pricing.
- Input stays in the browser tab, unless you download a CSV. Clearing the page or closing the tab loses unsaved inputs.
- Up to 200 rows per import. Never put passwords, customer information or confidential supplier agreements in examples.
- Print uses a landscape checklist with wrapped text. Review the browser print preview and choose landscape if your printer overrides the page setting.
- CSV spreadsheet output guards against leading formula characters, but inspect files before opening in other software.

## Typical weekly rhythm (10–20 minutes)
Monday: physical count; record new inbound deliveries; review flagged items; download results and confirm actual orders through your usual purchasing process. Friday: verify received goods and adjust counts.
