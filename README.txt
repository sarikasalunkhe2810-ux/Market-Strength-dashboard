MarketStrength — Free Online Streamlit Website

WHAT'S INCLUDED
- app.py: Indian sector relative-strength and rotation dashboard
- requirements.txt: packages Streamlit Cloud installs automatically

FEATURES
- Sector-only dashboard (no stock scanner or stock drill-down)
- Relative strength vs Nifty 500 over 1M, 3M, 6M and 12M
- Weighted RS score and short-term RS momentum
- Median-centred Leading / Weakening / Improving / Lagging quadrants
- CSV export and refresh button

FREE ONLINE DEPLOYMENT
1. Download and extract this ZIP on your computer.
2. Visit https://github.com and sign in/create a free account.
3. Click the + menu, then New repository.
4. Name it marketstrength-dashboard. Choose Public, then Create repository.
5. In the repository, choose Add file > Upload files.
6. Upload app.py and requirements.txt from this folder. Commit changes.
7. Visit https://share.streamlit.io and sign in.
8. Click Create app, select your GitHub repository, branch main, and file path app.py.
9. Optionally set an app URL such as marketstrength-yourchoice. Click Deploy.
10. Wait for deployment, then open the generated streamlit.app URL.

DATA NOTES
This app uses Yahoo Finance via yfinance, not an official NSE data feed. Some sector index tickers or the Nifty 500 benchmark may not be available consistently. If the app says benchmark data cannot be retrieved, verify the Yahoo Finance ticker in the sidebar or in app.py. Do not assume data is real-time.

SECURITY
Do not put passwords, brokerage credentials, API keys, or personal financial account details into app.py or a public GitHub repository.
